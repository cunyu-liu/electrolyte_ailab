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
        主流程：上传 -> 轮询 -> 下载
        """
        if not file_paths:
            print("[!] 没有检测到需要处理的文件，任务终止。")
            return

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 1. 获取批量上传链接
        print(f"[-] 正在申请 {len(file_paths)} 个文件的上传链接...")
        batch_id, upload_urls = self._get_batch_upload_urls(file_paths, model_version)
        
        if not batch_id:
            print("[!] 获取上传链接失败，请检查 Token 或 网络。")
            return

        # 2. 上传文件
        print("[-] 开始上传文件...")
        for i, file_path in enumerate(file_paths):
            if i < len(upload_urls):
                self._upload_file(file_path, upload_urls[i])
            else:
                print(f"[!] 错误：文件 {file_path} 没有对应的上传链接")

        print(f"[-] 上传完成，任务 Batch ID: {batch_id}")
        print("[-] 系统已自动开始解析，正在等待结果（每5秒轮询一次）...")

        # 3. 轮询任务状态直至完成
        self._poll_and_download(batch_id, output_dir)

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
            if file.lower().endswith('.docx'):
                full_path = os.path.join(root, file)
                pdf_list.append(full_path)
    
    return pdf_list

if __name__ == "__main__":
    MY_TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI3OTIwMDU3NyIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2ODk2NzE4NiwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiNDcxZDViY2MtMTBlNy00NjQ3LTg3NzUtNjA0MDM2M2QwZmM0IiwiZW1haWwiOiIiLCJleHAiOjE3NzAxNzY3ODZ9.JpUilYN5yEFKACuna4RoUfbCmObVC3p2dQOXbGte7aJmuJoJTY0RCq1vmjthaoplzlWarecy0BO-ou2Vl4ebZg"
    
    INPUT_FOLDER = '/Users/liucunyu/Documents/课题idea 数据 结论/Thu化工院张强课题组25实习/Qwen3微调数据/rag 硬件数据'
    OUTPUT_FOLDER = "./rag_hardware_mineru_output" 

    print(f"正在扫描文件夹: {INPUT_FOLDER} ...")
    files_to_process = scan_directory(INPUT_FOLDER)
    
    if len(files_to_process) > 0:
        print(f"共发现 {len(files_to_process)} 个 PDF 文件。")
        converter = MineruConverter(MY_TOKEN)
        converter.process_files(files_to_process, output_dir=OUTPUT_FOLDER, model_version="vlm")
    else:
        print("未找到任何 PDF 文件，请检查路径。")