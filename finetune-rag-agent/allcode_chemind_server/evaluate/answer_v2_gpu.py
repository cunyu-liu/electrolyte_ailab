import os
import json
import torch
import re
import time
import logging
import sys
import gc
from math import isclose
from collections import Counter
from typing import List, Dict, Any
from more_itertools import collapse
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ==========================================
# 核心工具函数 (来自 Source Code A)
# ==========================================

def clean_json_text(text: str) -> str:
    """清理模型输出，提取合法的 JSON 字符串"""
    text = text.strip()
    # 去除 Markdown 标记
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)

    # 提取 JSON 主体 ({...} 或 [...])
    json_match = re.search(r'(\{.*\}|\[.*\])', text, flags=re.DOTALL)
    if not json_match:
        # 尝试非贪婪匹配或容错
        return text 
    json_text = json_match.group(0)

    # 清理 ASCII 控制字符
    json_text = re.sub(r'\\x[0-9a-fA-F]{2}', '', json_text)

    # 修复全角引号
    json_text = json_text.replace("“", r'\"').replace("”", r'\"').replace("‘", "'").replace("’", "'")

    # 处理反斜杠转义
    def escape_backslashes_in_strings(match):
        string_content = match.group(1)
        string_content = re.sub(r'(?<!\\)\\(?![\\"bfnrtu])', r'\\\\', string_content)
        return '"' + string_content + '"'
    
    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_backslashes_in_strings, json_text)

    # 修复内部非法引号
    def escape_inner_quotes(match):
        inner = match.group(1)
        fixed_inner = re.sub(r'(?<!\\)"', r'\"', inner)
        return '"' + fixed_inner + '"'
    
    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_inner_quotes, json_text)

    return json_text

class LocalEvaluator:
    def __init__(self, model_path: str, questions_file: str, output_dir: str, batch_size: int = 20):
        """
        Args:
            model_path: 本地模型路径
            questions_file: 原始题目 JSON 文件路径
            output_dir: 结果输出目录
            batch_size: 这里指 chunk size，即一次让 LLM 回答多少道题 (Source A 逻辑为 20)
        """
        self.model_path = model_path
        self.questions_file = questions_file
        self.output_dir = output_dir
        self.chunk_size = batch_size
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 加载模型
        print(f"Loading local model from {model_path}...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, 
            device_map="auto", 
            torch_dtype=torch.float16, 
            trust_remote_code=True
        ).eval()
        print("Model loaded successfully.")

    def _generate_llm_response(self, text_json: str) -> str:
        """核心生成逻辑：构造 Prompt 并调用本地模型"""
        sys_prompt = """
Task: Analyze and answer the following chemistry questions accurately. Each question contains metadata and requires different response formats.

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
filename, question_number, sub_id, answer

Example Output:
[
  {
    "filename": "doc1", "question_number": "1", "sub_id": "1", "answer": ["B"]
  },
  {
    "filename": "doc2", "question_number": "3", "sub_id": "1", "answer": -237.2
  }
]
Instructions:
Read each question stem carefully. Answer the specific question asked.
Follow the exact output format specified by answer_data_type.
Do NOT include explanations in the final JSON output.
"""
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": text_json}
        ]
        
        # 应用模板
        text = self.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=4096,  # 允许长输出以容纳20道题的JSON
                temperature=0.7,
                top_p=0.9
            )
        
        # 裁剪输入部分
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        raw_output = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return raw_output

    def retry_with_json(self, func_input_text, max_retries=2, retry_delay=1, expected_length=None):
        """带有 JSON 解析校验的重试机制"""
        for attempt in range(1, max_retries + 1):
            try:
                raw_output = self._generate_llm_response(func_input_text)
                cleaned_output = clean_json_text(raw_output)
                results = json.loads(cleaned_output)

                if expected_length is not None and len(results) != expected_length:
                    logging.warning(f"Length mismatch: expected {expected_length}, got {len(results)}. Retrying...")
                    raise ValueError("Length mismatch")
                
                return results

            except Exception as e:
                logging.error(f"Attempt {attempt}/{max_retries} failed: {e}")
                if attempt >= max_retries:
                    raise e
                time.sleep(retry_delay)
        return []

    def run_inference(self):
        """执行全量推理流程"""
        # 1. 读取数据
        with open(self.questions_file, "r", encoding="utf-8") as f:
            input_json_list = json.load(f)
        
        # 2. 分块 (Chunking)
        input_json_list_chunks = [input_json_list[i:i + self.chunk_size] for i in range(0, len(input_json_list), self.chunk_size)]
        
        print(f"Total questions: {len(input_json_list)}. Total chunks: {len(input_json_list_chunks)}.")

        # 3. 逐块处理
        # 注意：本地模型通常不支持高并发推理，因此这里使用简单的循环而不是 ThreadPool
        for i, chunk in enumerate(tqdm(input_json_list_chunks, desc="Processing chunks")):
            chunk_id = i
            output_json_file = os.path.join(self.output_dir, f"{chunk_id}_answer.json")
            
            # 断点续传检查
            if os.path.exists(output_json_file):
                try:
                    existing_data = json.load(open(output_json_file, "r", encoding="utf-8"))
                    if len(existing_data) == len(chunk):
                        continue # Skip completed
                except:
                    pass

            # 构造输入列表 (格式化字段)
            problem_list = []
            for item in chunk:
                problem_list.append({
                    "filename": item.get("filename"),
                    "question_number": item.get("question_number"),
                    "sub_id": item.get("sub_id"),
                    "question": item.get("question"),
                    "type": item.get("type"),
                    "answer_data_type": item.get("answer_data_type"),
                    "domain": item.get("domain", "general"),
                })
            
            problem_text = json.dumps(problem_list, ensure_ascii=False)

            # 调用带重试的推理
            try:
                # 第一次尝试
                answers = self.retry_with_json(problem_text, max_retries=2, expected_length=len(problem_list))
            except Exception as e:
                print(f"Failed to process chunk {chunk_id} after retries. Saving error state.")
                # 即使失败也尽量保存原始输出以便排查（此处略）
                answers = []

            # 如果长度对不上，再尝试一次无长度检查的
            if len(answers) != len(problem_list) and len(answers) > 0:
                 # 可以在这里做后处理补全，或者直接保存部分结果
                 pass

            # 保存结果
            if answers:
                with open(output_json_file, "w", encoding="utf-8") as fp:
                    json.dump(answers, fp, ensure_ascii=False, indent=4)
        
        print("Inference completed.")

    def run_evaluation(self):
        """执行评分流程 (基于 Source A 的 get_evluation_score 逻辑)"""
        print("Starting evaluation...")
        
        # 1. 构建 Ground Truth 字典
        answer_pair_dict = {}
        with open(self.questions_file, "r", encoding="utf-8") as f:
            gt_list = json.load(f)
            
        for item in gt_list:
            # 兼容处理：去除文件名空格
            filename = item["filename"].replace(" ", "")
            key = f"{filename}_{item['question_number']}_{item['sub_id']}"
            
            original_type = item.get("original_type", item["type"]).replace(" ", "")
            
            answer_pair_dict[key] = {
                "gt_answer": item["answer"],
                "type": item["type"],
                "original_type": original_type,
                "domain": item.get("domain", "general"),
            }

        # 2. 读取 LLM 输出并合并
        llm_files = [f for f in os.listdir(self.output_dir) if f.endswith("_answer.json")]
        for file in tqdm(llm_files, desc="Loading answers"):
            try:
                chunk_data = json.load(open(os.path.join(self.output_dir, file), "r", encoding="utf-8"))
                for ans in chunk_data:
                    # 同样处理 key
                    fname = ans.get("filename", "").replace(" ", "")
                    q_num = ans.get("question_number")
                    s_id = ans.get("sub_id")
                    key = f"{fname}_{q_num}_{s_id}"
                    
                    if key in answer_pair_dict:
                        answer_pair_dict[key]["llm_answer"] = ans.get("answer")
            except Exception as e:
                print(f"Error reading {file}: {e}")

        # 3. 计算分数
        total_score, total_answered = 0, 0
        non_answered = 0
        
        # 统计计数器
        stats = {
            "calculation": {"score": 0, "count": 0},
            "choice": {"score": 0, "count": 0},
            "true_false": {"score": 0, "count": 0},
            "general": {"choice_score": 0, "choice_count": 0, "calc_score": 0, "calc_count": 0},
            "electro": {"score": 0, "count": 0, "choice_score": 0, "choice_count": 0, "calc_score": 0, "calc_count": 0}
        }

        for key, data in answer_pair_dict.items():
            if "llm_answer" not in data:
                non_answered += 1
                continue
            
            q_type = data["type"]
            gt = data["gt_answer"]
            llm = data["llm_answer"]
            score = 0

            # --- 评分逻辑 ---
            if q_type == "Calculation":
                # 尝试转 float 并比较
                llm_val_list = list(collapse([llm])) # 处理可能嵌套的列表
                try:
                    val = float(llm_val_list[0])
                    # 使用 isclose
                    if isclose(float(gt), val, rel_tol=1e-2, abs_tol=1e-3):
                        score = 1
                except:
                    score = 0
                stats["calculation"]["score"] += score
                stats["calculation"]["count"] += 1

            elif q_type == "Choice":
                gt_set = set(list(collapse([gt])))
                llm_set = set(list(collapse([llm])))
                if gt_set == llm_set:
                    score = 1
                stats["choice"]["score"] += score
                stats["choice"]["count"] += 1

            elif q_type == "True/False":
                gt_val = list(collapse([gt]))[0]
                llm_val = list(collapse([llm]))[0]
                # 简单比较，Source A 逻辑中 True/False 是布尔值
                if str(gt_val).lower() == str(llm_val).lower():
                    score = 1
                stats["true_false"]["score"] += score
                stats["true_false"]["count"] += 1
            
            # --- 领域/原始类型统计 ---
            is_electro = "electrochemistry" in data["domain"]
            
            if is_electro:
                stats["electro"]["score"] += score
                stats["electro"]["count"] += 1
                if q_type == "Choice":
                    stats["electro"]["choice_score"] += score
                    stats["electro"]["choice_count"] += 1
                elif q_type == "Calculation":
                    stats["electro"]["calc_score"] += score
                    stats["electro"]["calc_count"] += 1
            else:
                if q_type == "Choice":
                    stats["general"]["choice_score"] += score
                    stats["general"]["choice_count"] += 1
                elif q_type == "Calculation":
                    stats["general"]["calc_score"] += score
                    stats["general"]["calc_count"] += 1

            total_score += score
            total_answered += 1

        # 4. 生成报告
        def safe_div(n, d): return n / d if d > 0 else 0

        summary = {
            "total_answered": total_answered,
            "total_non_answered": non_answered,
            "overall_accuracy": safe_div(total_score, total_answered),
            
            "calculation_acc": safe_div(stats["calculation"]["score"], stats["calculation"]["count"]),
            "choice_acc": safe_div(stats["choice"]["score"], stats["choice"]["count"]),
            "true_false_acc": safe_div(stats["true_false"]["score"], stats["true_false"]["count"]),
            
            "electro_acc": safe_div(stats["electro"]["score"], stats["electro"]["count"]),
            
            "weighted_score": (
                safe_div(stats["general"]["choice_score"], stats["general"]["choice_count"]) * 1 +
                safe_div(stats["general"]["calc_score"], stats["general"]["calc_count"]) * 2 +
                safe_div(stats["electro"]["choice_score"], stats["electro"]["choice_count"]) * 2 +
                safe_div(stats["electro"]["calc_score"], stats["electro"]["calc_count"]) * 3
            )
        }

        print("\nEvaluation Results:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
        # 保存详细结果
        result_file = os.path.join(self.output_dir, "evaluation_summary.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4)
        print(f"Summary saved to {result_file}")

# ==========================================
# 主程序入口
# ==========================================
if __name__ == "__main__":
    # 配置路径
    MODEL_PATH = "/home/chemind/allcode_chemind_server/mergedoutput/qwen3-8b-sft-mdQA_data-merged"
    # 如果是测试，可以使用一个较小的模型路径或 API 逻辑 (本代码专为 Local Model 设计)
    
    QUESTIONS_FILE = "/home/chemind/allcode_chemind_server/evaluate/eval_dataset/v2/习题问答对_qwen_sft_all_test.jsonl"
    
    # 自动根据模型路径生成输出目录名
    model_name = os.path.basename(os.path.normpath(MODEL_PATH))
    OUTPUT_DIR = f"/home/chemind/allcode_chemind_server/testoutput/{model_name}_eval"

    # 初始化评估器 (Batch Size = Chunk Size = 20)
    evaluator = LocalEvaluator(
        model_path=MODEL_PATH,
        questions_file=QUESTIONS_FILE,
        output_dir=OUTPUT_DIR,
        batch_size=20 
    )

    # 1. 运行推理 (生成 chunk_x_answer.json)
    evaluator.run_inference()
    
    # 2. 释放显存 (可选，如果后续不跑其他东西)
    gc.collect()
    torch.cuda.empty_cache()

    # 3. 运行评分
    evaluator.run_evaluation()