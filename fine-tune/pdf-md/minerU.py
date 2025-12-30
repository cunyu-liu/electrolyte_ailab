import requests
import json
import time
import os
import zipfile
import io
import hashlib 

class MineruConverter:
    def __init__(self, api_token):
        self.base_url = "https://mineru.net/api/v4"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

    def process_files(self, file_paths, output_dir="output", model_version="vlm"):
        """
        [修改] 增加分批处理逻辑，解决文件数量过多导致的 API 限制问题
        """
        if not file_paths:
            print("[!] 没有检测到需要处理的文件，任务终止。")
            return

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # --- 配置区 ---
        BATCH_SIZE = 50  # 建议设为 50，防止超过 API 单次限制
        total_files = len(file_paths)
        # -------------

        print(f"[-] 总任务数: {total_files} 个文件，将分为 {(total_files + BATCH_SIZE - 1) // BATCH_SIZE} 个批次依次执行。")

        # 按批次循环处理
        for i in range(0, total_files, BATCH_SIZE):
            # 切片获取当前批次的文件列表
            current_batch_files = file_paths[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            print(f"\n>>> 正在执行第 {batch_num} 批次 (本批 {len(current_batch_files)} 个文件，进度: {i+1}~{min(i+BATCH_SIZE, total_files)}/{total_files}) <<<")

            # 1. 获取当前批次的上传链接
            print(f"[-] [批次 {batch_num}] 正在申请上传链接...")
            batch_id, upload_urls = self._get_batch_upload_urls(current_batch_files, model_version)
            
            if not batch_id:
                print(f"[!] [批次 {batch_num}] 获取上传链接失败，跳过本批次。")
                continue

            # 2. 上传当前批次文件
            print(f"[-] [批次 {batch_num}] 开始上传文件...")
            for idx, file_path in enumerate(current_batch_files):
                if idx < len(upload_urls):
                    self._upload_file(file_path, upload_urls[idx])
                else:
                    print(f"[!] 错误：文件 {file_path} 没有对应的上传链接")

            print(f"[-] [批次 {batch_num}] 上传完成，Batch ID: {batch_id}")
            print(f"[-] [批次 {batch_num}] 等待解析结果...")

            # 3. 轮询当前批次状态直至下载完成
            # 注意：这会阻塞直到当前批次全部处理完，才进入下一批，非常安全
            self._poll_and_download(batch_id, output_dir)
            
            # 批次间稍微暂停一下，避免请求过于密集
            time.sleep(2)
        
        print("\n[=] 所有批次任务均已执行完毕。")

    def _get_batch_upload_urls(self, file_paths, model_version):
        url = f"{self.base_url}/file-urls/batch"
        
        files_info = []
        for p in file_paths:
            file_name = os.path.basename(p)
            
            # 使用 MD5 生成固定长度 ID，防止文件名过长报错
            raw_str = f"{time.time()}_{file_name}"
            data_id = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
            
            files_info.append({
                "name": file_name,
                "data_id": data_id 
            })

        data = {
            "files": files_info,
            "model_version": model_version
        }

        try:
            res = requests.post(url, headers=self.headers, json=data)
            res_data = res.json()
            
            if res.status_code == 200 and res_data.get("code") == 0:
                return res_data["data"]["batch_id"], res_data["data"]["file_urls"]
            else:
                print(f"[!] API 错误: {res_data.get('msg')}")
                return None, None
        except Exception as e:
            print(f"[!] 请求异常: {e}")
            return None, None

    def _upload_file(self, file_path, upload_url):
        try:
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            print(f"    ...正在上传: {os.path.basename(file_path)} ({file_size:.2f} MB)")
            
            with open(file_path, 'rb') as f:
                res = requests.put(upload_url, data=f)
                if res.status_code == 200:
                    print(f"    [√] 上传成功")
                else:
                    print(f"    [x] 上传失败: {res.status_code}")
        except Exception as e:
            print(f"    [!] 上传异常: {e}")

    def _poll_and_download(self, batch_id, output_dir):
        url = f"{self.base_url}/extract-results/batch/{batch_id}"
        completed_files = set()
        
        while True:
            try:
                res = requests.get(url, headers=self.headers)
                res_data = res.json()
                
                if res_data.get("code") != 0:
                    print(f"[!] 查询状态失败: {res_data.get('msg')}")
                    break

                results = res_data["data"]["extract_result"]
                all_done = True
                
                for item in results:
                    file_name = item["file_name"] # 这是原始文件名（例如 a.pdf）
                    state = item["state"]
                    
                    if file_name in completed_files:
                        continue

                    if state == "done":
                        print(f"    [√] {file_name} 解析完成！正在下载...")
                        # [修改] 传入 file_name 以便创建独立文件夹
                        self._download_and_extract(item["full_zip_url"], output_dir, file_name)
                        completed_files.add(file_name)
                    
                    elif state == "failed":
                        print(f"    [x] {file_name} 解析失败: {item.get('err_msg')}")
                        completed_files.add(file_name)
                    
                    elif state == "running":
                        all_done = False
                        progress = item.get("extract_progress", {})
                        done_pages = progress.get('extracted_pages', 0)
                        total_pages = progress.get('total_pages', '?')
                        print(f"    [>] {file_name}: {done_pages}/{total_pages} 页")
                    
                    elif state in ["pending", "waiting-file", "converting"]:
                        all_done = False
                
                if all_done and len(completed_files) == len(results):
                    print("[-] 所有任务已结束。")
                    break

                time.sleep(5)

            except Exception as e:
                print(f"[!] 轮询异常: {e}")
                time.sleep(5)

    def _download_and_extract(self, zip_url, output_dir, original_filename):
        # [修改] 新增 original_filename 参数
        try:
            r = requests.get(zip_url)
            if r.status_code == 200:
                # [关键修改] 创建该文件专属的子文件夹
                # 去掉 .pdf 后缀作为文件夹名
                folder_name = os.path.splitext(original_filename)[0]
                # 拼接完整路径: ./mineru_output/电池综述xxx/
                specific_dir = os.path.join(output_dir, folder_name)
                
                if not os.path.exists(specific_dir):
                    os.makedirs(specific_dir)
                
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    # 解压到专属文件夹
                    z.extractall(specific_dir)
                print(f"        -> 已解压至独立文件夹: {specific_dir}")
            else:
                print(f"        -> 下载 ZIP 失败: {r.status_code}")
        except Exception as e:
            print(f"        -> 解压异常: {e}")

# ==========================================
#              使用配置区
# ==========================================

def scan_directory(folder_path):
    """扫描指定文件夹下的所有PDF文件"""
    if not os.path.exists(folder_path):
        print(f"[错误] 文件夹不存在: {folder_path}")
        return []
    
    pdf_list = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(root, file)
                pdf_list.append(full_path)
    
    return pdf_list

if __name__ == "__main__":
    MY_TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI3OTIwMDU3NyIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2NTk1Njk4NSwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiM2Y3NTYyMGYtODQ0Ni00YzQ4LWE3NGEtZjc4MDljNjM2MjIwIiwiZW1haWwiOiIiLCJleHAiOjE3NjcxNjY1ODV9.dITk-cI9xQSZpf0w4TWH-FMUvp9OUTzLmqDDURWWUhLKnFPpNNXg1x-c88KlP2oiX8PaxGMg7mTaYZHSJ6sq7w"
    
    INPUT_FOLDER = '/Users/liucunyu/Documents/课题idea 数据 结论/Thu化工院张强课题组25实习/Qwen3微调数据/SUPERChem-500-benchmark/pdf'
    OUTPUT_FOLDER = "./mineru_superchem_output" 

    print(f"正在扫描文件夹: {INPUT_FOLDER} ...")
    files_to_process = scan_directory(INPUT_FOLDER)
    
    if len(files_to_process) > 0:
        print(f"共发现 {len(files_to_process)} 个 PDF 文件。")
        converter = MineruConverter(MY_TOKEN)
        converter.process_files(files_to_process, output_dir=OUTPUT_FOLDER, model_version="vlm")
    else:
        print("未找到任何 PDF 文件，请检查路径。")