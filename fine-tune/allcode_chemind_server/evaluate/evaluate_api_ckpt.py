import os
import sys
import json
import time
import re
import gc
import logging
import torch
import concurrent.futures
import pandas as pd
import numpy as np
from typing import List, Dict, Union, Any
from math import isclose
from collections import Counter
from tqdm import tqdm
from more_itertools import collapse, chunked
from transformers import AutoModelForCausalLM, AutoTokenizer
from openai import OpenAI

# =================配置区域=================   完全支持断点续评
class Config:
    # 路径配置
    INPUT_FILE = r"/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/evaluate/eval_dataset/v1/习题问答对_v1test.json"
    BASE_OUTPUT_DIR = r"/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/testoutput"
    
    # API配置 (根据实际情况修改)
    API_KEYS = {
        "deepseek": "sk-e387e1a310824ad7ac7b84f6f82cd284",
        "wwxq": "sk-2xoohlqxvrqwv6fq" # 无问芯穹
    }
    API_URLS = {
        "deepseek": "https://api.deepseek.com/v1",
        "wwxq": "https://cloud.infini-ai.com/maas/v1"
    }

    # 待测模型列表
    # 格式: (模型名称或路径, 类型 'local' 或 'api')
    MODELS_TO_EVAL = [
        ("deepseek-chat", "api"),
        ("deepseek-reasoner", "api"),
        ("qwen3-next-80b-a3b-instruct", "api"),
        ("qwen3-next-80b-a3b-thinking", "api"),
        ("qwen3-235b-a22b-instruct-2507t", "api"), 
        ("qwen3-8b", "api"),
    ]

    # 推理参数
    MAX_TOKENS = 4096
    TEMPERATURE = 0.7
    BATCH_SIZE = 20  # 每个文件块的大小
    API_WORKERS = 5  # API并发数
    LOCAL_WORKERS = 1 # 本地模型强制串行

# =================日志设置=================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# =================工具函数=================
def clean_json_text(text: str) -> str:
    """
    清理模型输出，提取合法的 JSON 字符串
    增强版：处理控制字符和转义问题
    """
    text = text.strip()
    
    # 1. 去除 Markdown 标记
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    
    # 2. 提取 JSON 主体
    # 尝试寻找最外层的 {} 或 []
    json_match = re.search(r'(\{.*\}|\[.*\])', text, flags=re.DOTALL)
    if json_match:
        json_text = json_match.group(0)
    else:
        # 容错：如果找不到明确的闭合，尝试补全或直接使用原文本
        if text.strip().startswith("{") and text.strip().endswith("}"):
             json_text = f"[{text}]"
        else:
            # 返回原始内容以便重试逻辑捕获错误或进行后续处理
            json_text = text

    # 3. 剔除真正非法的 ASCII 控制字符 (0-31)，保留 \n(10), \r(13), \t(9)
    # 这些字符通常是不可见的干扰项
    json_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', json_text)

    # 4. 处理十六进制转义 (如 \x00) - JSON 标准不支持，但在 Python 字符串中常见
    json_text = re.sub(r'\\x[0-9a-fA-F]{2}', '', json_text)

    # 5. 修复全角引号
    json_text = json_text.replace("“", r'\"').replace("”", r'\"').replace("‘", "'").replace("’", "'")

    # 6. 处理反斜杠转义 (防止 \ 后面接非法字符)
    # 逻辑：如果 \ 后面不是 JSON 合法转义符 (b,f,n,r,t,u,",\)，则将其转义为 \\
    def escape_backslashes_in_strings(match):
        string_content = match.group(1)
        # 负向先行断言：如果 \ 后面不是合法的转义字符，就变成 \\
        string_content = re.sub(r'(?<!\\)\\(?![\\"bfnrtu/])', r'\\\\', string_content)
        return '"' + string_content + '"'
    
    # 应用于所有双引号内的内容
    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_backslashes_in_strings, json_text)

    # 7. 修复双引号内部的未转义双引号 (常见错误: "key": "He said "Hello"")
    def escape_inner_quotes(match):
        inner = match.group(1)
        # 将内部的 " 替换为 \"
        fixed_inner = re.sub(r'(?<!\\)"', r'\"', inner)
        return '"' + fixed_inner + '"'
    
    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_inner_quotes, json_text)

    return json_text

def retry_with_json(func, *args, max_retries=3, retry_delay=2, length_check=None, **kwargs):
    """
    通用重试与JSON解析器
    修改：增加 strict=False 以允许控制字符
    """
    for attempt in range(1, max_retries + 1):
        try:
            raw_output = func(*args, **kwargs)
            
            # 兼容模型直接返回 List/Dict 的情况
            if isinstance(raw_output, (dict, list)):
                results = raw_output
            else:
                cleaned_output = clean_json_text(raw_output)
                # [关键修改] strict=False 允许字符串中包含换行符等控制字符
                results = json.loads(cleaned_output, strict=False)
            
            if length_check is not None and len(results) != length_check:
                raise ValueError(f"Length mismatch: expected {length_check}, got {len(results)}")
            
            return results
        except Exception as e:
            # 只有最后一次失败才打印 Error，中间的打印 Warning
            log_level = logging.ERROR if attempt >= max_retries else logging.WARNING
            logging.log(log_level, f"JSON Parse/Retry Error (Attempt {attempt}): {str(e)}")
            
            if attempt >= max_retries:
                # 打印出有问题的文本的前500个字符，方便调试
                debug_text = raw_output[:500] if 'raw_output' in locals() and isinstance(raw_output, str) else "N/A"
                logging.error(f"Failed Text Snippet: {debug_text}...")
                # 可以在这里选择返回 [] 而不是抛出异常，防止整个程序中断
                # raise e 
                return [] 
            
            time.sleep(retry_delay)
    return []

# =================模型包装类=================
class BaseModel:
    def __init__(self, model_name):
        self.model_name = model_name
        self.sys_prompt = '''Task: Analyze and answer the following chemistry questions accurately. Each question contains metadata and requires different response formats.
Input Format: A list of question objects with the following structure:
json
{
"filename": "source document name",
"question_number": "question identifier",
"sub_id": "sub-question identifier",
"question": {
"question_stem": "full question context",
"question": "specific question to answer",
"options": ["A. option1", "B. option2", ...] // for Choice questions
},
"type": "Question type (Choice/Calculation/TrueFalse)",
"answer_data_type": "Expected output format",
"domain": "general_chemistry"
}
Question Types & Response Requirements:
Choice Questions: Select correct option(s) from multiple choices
Output format: ["A"] or ["A","B"] for multiple correct answers
Calculation Questions: Provide numerical answer with proper units
Output format: float value (e.g., -237.2)
True/False Questions: Boolean response
Output format: true or false
Output Requirements: For each question, provide a JSON object containing:
filename: Original source filename
question_number: Main question identifier
sub_id: Sub-question identifier
answer: Your response in the specified data type
Example Output:
json
[
{
"filename": "(化工系学习生活部)物理化学(A2)习题解答_selected_0_cleaned",
"question_number": "1",
"sub_id": "1",
"answer": ["B"]
},
{
"filename": "(化工系学习生活部)物理化学(A2)习题解答_selected_0_cleaned",
"question_number": "3",
"sub_id": "1",
"answer": -237.2
},
{
"filename": "(化工系学习生活部)物理化学(A2)习题解答_selected_3_cleaned",
"question_number": "7",
"sub_id": "1",
"answer": false
}
]
Instructions:
Read each question stem carefully for context
Answer the specific question asked
Follow the exact output format specified by answer_data_type
Maintain scientific accuracy in calculations
Provide concise, direct answers without explanations
Include all three metadata fields in each response
Begin processing the question list now.'''

    
    def generate(self, input_json_str: str) -> str:
        raise NotImplementedError

    def cleanup(self):
        pass

class LocalModel(BaseModel):
    def __init__(self, model_path):
        super().__init__(os.path.basename(os.path.normpath(model_path)))
        logging.info(f"Loading Local Model from: {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, 
            device_map="auto", 
            torch_dtype=torch.float16, 
            trust_remote_code=True
        ).eval()

    def generate(self, input_json_str: str) -> str:
        messages = [
            {"role": "system", "content": self.sys_prompt},
            {"role": "user", "content": input_json_str}
        ]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE,
                top_p=0.9
            )
        
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        return self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    def cleanup(self):
        logging.info("Cleaning up local model memory...")
        del self.model
        del self.tokenizer
        gc.collect()
        torch.cuda.empty_cache()

class APIModel(BaseModel):
    def __init__(self, model_name):
        super().__init__(model_name)
        # 根据模型名简单判断使用哪个 Key/URL
        if "deepseek" in model_name:
            self.client = OpenAI(api_key=Config.API_KEYS["deepseek"], base_url=Config.API_URLS["deepseek"])
        else:
            self.client = OpenAI(api_key=Config.API_KEYS["wwxq"], base_url=Config.API_URLS["wwxq"])
            
    def generate(self, input_json_str: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.sys_prompt},
                {"role": "user", "content": input_json_str}
            ],
            temperature=Config.TEMPERATURE,
            stream=False
        )
        return response.choices[0].message.content

# =================核心处理逻辑=================
class Pipeline:
    def __init__(self, model_identifier, model_type):
        self.model_identifier = model_identifier
        self.model_type = model_type
        
        # 确定输出目录名
        self.model_short_name = os.path.basename(os.path.normpath(model_identifier))
        self.output_dir = os.path.join(Config.BASE_OUTPUT_DIR, self.model_short_name)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def prepare_data_chunks(self):
        """读取原始数据并切块"""
        with open(Config.INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 简化字段，只保留推理需要的
        simplified_data = []
        for item in data:
            simplified_data.append({
                "filename": item["filename"],
                "question_number": item["question_number"],
                "sub_id": item["sub_id"],
                "question": item["question"],
                "type": item["type"],
                "answer_data_type": item["answer_data_type"],
                "domain": item["domain"]
            })
        
        return list(chunked(simplified_data, Config.BATCH_SIZE))

    def process_chunk(self, model_instance, chunk_data, chunk_id):
        """处理单个数据块"""
        output_file = os.path.join(self.output_dir, f"{chunk_id}_answer.json")
        
        # 跳过已完成的
        if os.path.exists(output_file):
            try:
                exist_data = json.load(open(output_file, 'r', encoding='utf-8'))
                if len(exist_data) == len(chunk_data):
                    return f"Skipped {chunk_id}"
            except:
                pass

        input_str = json.dumps(chunk_data, ensure_ascii=False)
        
        try:
            # 这里的 retry_with_json 调用 generate
            result_json = retry_with_json(
                model_instance.generate, 
                input_str, 
                max_retries=2, 
                length_check=len(chunk_data)
            )
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result_json, f, ensure_ascii=False, indent=4)
            return f"Completed {chunk_id}"
        except Exception as e:
            return f"Failed {chunk_id}: {str(e)}"

    def run_inference(self):
        logging.info(f"Starting inference for {self.model_identifier} ({self.model_type})")
        
        # 1. 初始化模型
        if self.model_type == "local":
            model_engine = LocalModel(self.model_identifier)
            workers = Config.LOCAL_WORKERS
        else:
            model_engine = APIModel(self.model_identifier)
            workers = Config.API_WORKERS

        chunks = self.prepare_data_chunks()
        
        # 2. 执行推理
        # 如果是 Local 模式，强制单线程，避免显存爆炸
        if self.model_type == "local":
            for i, chunk in tqdm(enumerate(chunks), total=len(chunks), desc="Local Inference"):
                res = self.process_chunk(model_engine, chunk, i)
                if "Failed" in res:
                    logging.error(res)
        else:
            # API 模式多线程
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(self.process_chunk, model_engine, chunk, i): i for i, chunk in enumerate(chunks)}
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(chunks), desc="API Inference"):
                    pass # 已经在 process_chunk 里打印或记录了

        # 3. 清理资源
        model_engine.cleanup()
        logging.info(f"Inference finished for {self.model_identifier}")

    def evaluate(self):
        """
        使用指定的评测逻辑（严格对齐 Code 1）进行评估
        """
        logging.info(f"Starting evaluation for {self.model_identifier} using strict metrics...")
        
        # ==================== 1. 构建 Ground Truth 字典 ====================
        answer_pair_dict = {}
        with open(Config.INPUT_FILE, "r", encoding="utf-8") as f:
            ground_truth_answer_list = json.load(f)

        for problem_answer_data in tqdm(ground_truth_answer_list, desc="Loading ground truth answers"):
            # 注意：LLM 可能会把文件名中的空格删掉，这里统一预处理
            filename = problem_answer_data["filename"].replace(" ", "") 
            question_number = problem_answer_data["question_number"]
            sub_id = problem_answer_data["sub_id"]
            
            if "original_type" in problem_answer_data:
                original_type = problem_answer_data["original_type"].replace(" ", "")
            else:
                original_type = problem_answer_data["type"]
            
            key = "%s_%s_%s" % (filename, question_number, sub_id)
            answer_pair_dict[key] = {
                "gt_answer": problem_answer_data["answer"],
                "question": problem_answer_data["question"],
                "type": problem_answer_data["type"],
                "original_type": original_type,
                "solution": problem_answer_data.get("solution"),
                "domain": problem_answer_data.get("domain", ""),
                "correctness": problem_answer_data.get("correctness"),
                "notes": problem_answer_data.get("notes"),
            }

        # ==================== 2. 加载 LLM 答案并合并 ====================
        # 从 output_dir 读取所有 chunk json 文件
        chunk_files = [f for f in os.listdir(self.output_dir) if f.endswith(".json") and "answer_pair" not in f and "evaluation" not in f]
        
        for fname in tqdm(chunk_files, desc="Loading LLM outputs"):
            fpath = os.path.join(self.output_dir, fname)
            try:
                chunk_results = json.load(open(fpath, "r", encoding="utf-8"))
            except Exception as e:
                logging.error(f"Failed to load {fname}: {e}")
                continue
                
            for answer_data in chunk_results:
                if not isinstance(answer_data, dict):
                    continue
                if "filename" not in answer_data:
                    continue
                
                try:
                    tmp_filename = answer_data["filename"].replace(" ", "")
                    question_number = answer_data["question_number"]
                    sub_id = answer_data["sub_id"]
                    
                    key = "%s_%s_%s" % (tmp_filename, question_number, sub_id)
                    if key in answer_pair_dict:
                        answer_pair_dict[key]["llm_answer"] = answer_data["answer"]
                except Exception as e:
                    continue

        # 保存对齐后的字典
        with open(os.path.join(self.output_dir, "answer_pair_dict.json"), "w", encoding="utf-8") as f:
            json.dump(answer_pair_dict, f, ensure_ascii=False, indent=4)

        # ==================== 3. 计算评分 (严格复刻逻辑) ====================
        total_score, total_answered_count, total_non_answered_count = 0, 0, 0
        total_calculation_score, total_calculation_count = 0, 0
        total_choice_score, total_choice_count = 0, 0
        total_true_false_score, total_true_false_count = 0, 0
        total_short_answer_score, total_short_answer_count = 0, 0
        total_original_choice_score, total_original_choice_count = 0, 0
        total_electrochemistry_score, total_electrochemistry_count = 0, 0
        
        # 细分统计变量
        total_general_choice_score, total_general_choice_count = 0, 0
        total_general_calculation_score, total_general_calculation_count = 0, 0
        total_electrochemistry_choice_score, total_electrochemistry_choice_count = 0, 0
        total_electrochemistry_calculation_score, total_electrochemistry_calculation_count = 0, 0

        for question_key in answer_pair_dict:
            answer_pair_data = answer_pair_dict[question_key]
            type_ = answer_pair_data["type"]

            if "llm_answer" not in answer_pair_data:
                total_non_answered_count += 1
                continue

            score = 0
            # --- Calculation ---
            if type_ == "Calculation":
                gt_answer = answer_pair_data["gt_answer"]
                llm_answer = [answer_pair_data["llm_answer"]]
                llm_answer = list(collapse(llm_answer))
                try:
                    llm_answer_val = float(llm_answer[0])
                except:
                    llm_answer_val = 0
                
                # 使用 isclose 判定
                score = int(isclose(float(gt_answer), float(llm_answer_val), rel_tol=1e-2, abs_tol=1e-3))
                total_calculation_score += score
                total_calculation_count += 1
            
            # --- Choice ---
            elif type_ == "Choice":
                gt_answer = set(answer_pair_data["gt_answer"])
                llm_answer = set(list(collapse(answer_pair_data["llm_answer"])))
                
                score = int(gt_answer == llm_answer)
                total_choice_score += score
                total_choice_count += 1

                if answer_pair_data["original_type"] == "ShortAnswer":
                    total_short_answer_score += score
                    total_short_answer_count += 1
                elif answer_pair_data["original_type"] == "Choice":
                    total_original_choice_score += score
                    total_original_choice_count += 1
            
            # --- True/False ---
            elif type_ == "True/False":
                gt_answer = answer_pair_data["gt_answer"]
                try:
                    llm_answer = list(collapse(answer_pair_data["llm_answer"]))[0]
                except:
                    llm_answer = "None"
                # 兼容字符串 True/False 和 布尔值
                score = int(str(gt_answer).lower() == str(llm_answer).lower())
                total_true_false_score += score
                total_true_false_count += 1
            else:
                continue

            # --- 领域和子类型统计 ---
            if "electrochemistry" not in answer_pair_data["domain"]:
                if type_ == "Choice":
                    total_general_choice_score += score
                    total_general_choice_count += 1
                elif type_ == "Calculation":
                    total_general_calculation_score += score
                    total_general_calculation_count += 1
            else:
                total_electrochemistry_score += score
                total_electrochemistry_count += 1
                if type_ == "Choice":
                    total_electrochemistry_choice_count += 1
                    total_electrochemistry_choice_score += score
                elif type_ == "Calculation":
                    total_electrochemistry_calculation_count += 1
                    total_electrochemistry_calculation_score += score

            total_score += score
            total_answered_count += 1

        # 计算平均分
        average_general_choice_score = total_general_choice_score / total_general_choice_count if total_general_choice_count else 0
        average_general_calculation_score = total_general_calculation_score / total_general_calculation_count if total_general_calculation_count else 0
        average_electrochemistry_choice_score = total_electrochemistry_choice_score / total_electrochemistry_choice_count if total_electrochemistry_choice_count else 0
        average_electrochemistry_calculation_score = total_electrochemistry_calculation_score / total_electrochemistry_calculation_count if total_electrochemistry_calculation_count else 0

        summary = {
            "total_answered_questions": total_answered_count,
            "average_score": total_score / total_answered_count if total_answered_count else 0,
            "total_non_answered_count": total_non_answered_count,
            "total_calculation_questions": total_calculation_count,
            "average_calculation_score": total_calculation_score / total_calculation_count if total_calculation_count else 0,
            "total_choice_questions": total_choice_count,
            "average_choice_score": total_choice_score / total_choice_count if total_choice_count else 0,
            "total_true_false_questions": total_true_false_count,
            "average_true_false_score": total_true_false_score / total_true_false_count if total_true_false_count else 0,
            "total_short_answer_questions": total_short_answer_count,
            "average_short_answer_score": total_short_answer_score / total_short_answer_count if total_short_answer_count else 0,
            "total_original_choice_questions": total_original_choice_count,
            "average_original_choice_score": total_original_choice_score / total_original_choice_count if total_original_choice_count else 0,
            "total_electrochemistry_questions": total_electrochemistry_count,
            "average_electrochemistry_score": total_electrochemistry_score / total_electrochemistry_count if total_electrochemistry_count else 0,

            "total_general_choice_questions": total_general_choice_count,
            "average_general_choice_score": average_general_choice_score,
            "total_general_calculation_questions": total_general_calculation_count,
            "average_general_calculation_score": average_general_calculation_score,
            "total_electrochemistry_choice_questions": total_electrochemistry_choice_count,
            "average_electrochemistry_choice_score": average_electrochemistry_choice_score,
            "total_electrochemistry_calculation_questions": total_electrochemistry_calculation_count,
            "average_electrochemistry_calculation_score": average_electrochemistry_calculation_score,
            # 特定加权公式
            "weighted_score": average_general_choice_score * 1 + average_general_calculation_score * 2 +
                              average_electrochemistry_choice_score * 2 + average_electrochemistry_calculation_score * 3
        }

        # 保存详细结果 JSON
        result_file = os.path.join(self.output_dir, "evaluation_summary.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)
            
        return summary

# =================主入口=================
if __name__ == "__main__":
    final_results = {}
    
    for model_id, model_type in Config.MODELS_TO_EVAL:
        pipeline = Pipeline(model_id, model_type)
        
        # 1. 运行推理 (会跳过已完成的 chunk)
        pipeline.run_inference()
        
        # 2. 运行评估
        summary = pipeline.evaluate()
        
        final_results[pipeline.model_short_name] = summary
        print(f"\nModel: {pipeline.model_short_name}")
        print(f"Weighted Score: {summary['weighted_score']:.4f}")
        print("-" * 50)

    # 保存最终 CSV
    df = pd.DataFrame.from_dict(final_results, orient="index")
    # 按照你的需求保存为 UTF-8 BOM 格式
    
    df.to_csv("/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/testoutput/api_final_model_comparison.csv", encoding="utf-8-sig")
    print("\n✅ All tasks completed. Results saved to final_model_comparison.csv")