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
from typing import List, Dict, Any, Optional
# 如果没有安装 more_itertools，请先 pip install more_itertools
from more_itertools import collapse
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM
import pandas as pd  # 用于保存 CSV 结果

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ==========================================
# 核心工具函数
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
            batch_size: chunk size
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
            device_map="auto",   #兼容cpu gpu
            torch_dtype=torch.float16, 
            trust_remote_code=True
        ).eval()
        print("Model loaded successfully.")

    def _generate_llm_response(self, text_json: str) -> str:
        """核心生成逻辑"""
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
        
        text = self.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=4096,
                temperature=0.7,
                top_p=0.9
            )
        
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
                    # 如果重试失败，不抛出异常，而是返回空列表，防止整个程序中断
                    logging.error("Max retries reached. Returning empty list.")
                    return []
                time.sleep(retry_delay)
        return []

    def run_inference(self) -> List[Dict]:
        """
        执行全量推理流程
        修改：增加断点续评检测 + 保存中间结果到 json 文件
        """
        with open(self.questions_file, "r", encoding="utf-8") as f:
            input_json_list = json.load(f)
        
        input_json_list_chunks = [input_json_list[i:i + self.chunk_size] for i in range(0, len(input_json_list), self.chunk_size)]
        
        print(f"Total questions: {len(input_json_list)}. Total chunks: {len(input_json_list_chunks)}.")

        all_answers = [] # 用于在内存中保存所有结果

        for i, chunk in enumerate(tqdm(input_json_list_chunks, desc="Processing chunks")):
            chunk_id = i
            output_file = os.path.join(self.output_dir, f"{chunk_id}_answer.json")
            
            # ================= [新增 1] 断点续评逻辑 =================
            # 如果文件存在且长度正确，直接读取，跳过推理
            if os.path.exists(output_file):
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        saved_answers = json.load(f)
                    # 校验长度是否匹配（防止上次中断导致文件不完整）
                    if len(saved_answers) == len(chunk):
                        # print(f"Chunk {chunk_id} already exists. Skipping inference.")
                        all_answers.extend(saved_answers)
                        continue # 跳过本次循环，处理下一个 chunk
                except Exception as e:
                    logging.warning(f"Error reading existing file {output_file}: {e}. Re-running inference.")
            # =======================================================

            # 构造输入
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

            # 执行推理
            try:
                answers = self.retry_with_json(problem_text, max_retries=2, expected_length=len(problem_list))
            except Exception as e:
                print(f"Failed to process chunk {chunk_id} after retries.")
                answers = []

            if answers:
                # 内存聚合
                if isinstance(answers, list):
                    all_answers.extend(answers)
                elif isinstance(answers, dict):
                    # 极其罕见情况，防守式编程
                    all_answers.append(answers)
                    answers = [answers] # 统一转为 list 方便保存

                # ================= [新增 2] 保存结果逻辑 =================
                # 将当前 chunk 的结果立即写入文件
                try:
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(answers, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logging.error(f"Failed to save chunk {chunk_id} to {output_file}: {e}")
                # =======================================================
        
        print(f"Inference completed. Collected {len(all_answers)} answers.")
        return all_answers

    def run_evaluation(self, memory_answers: List[Dict]):
        """
        Args:
            memory_answers: 从 run_inference 传递过来的结果列表
        """
        print("Starting evaluation...")
        
        # 1. 构建 Ground Truth 字典
        answer_pair_dict = {}
        with open(self.questions_file, "r", encoding="utf-8") as f:
            ground_truth_answer_list = json.load(f)

        for problem_answer_data in tqdm(ground_truth_answer_list, desc="Loading ground truth answers"):
            filename = problem_answer_data["filename"].replace(" ", "") # LLM把文件名中的空格删掉了
            question_number = problem_answer_data["question_number"]
            sub_id = problem_answer_data["sub_id"]
            
            if "original_type" in problem_answer_data:
                original_type = problem_answer_data["original_type"].replace(" ", "")
            else:
                original_type = problem_answer_data["type"]
            
            answer_pair_dict["%s_%s_%s"%(filename, question_number, sub_id)] = {
                "gt_answer": problem_answer_data["answer"],
                "question": problem_answer_data["question"],
                "type": problem_answer_data["type"],
                "original_type": original_type,
                "solution": problem_answer_data.get("solution"),
                "domain": problem_answer_data.get("domain", ""),
                "correctness": problem_answer_data.get("correctness"),
                "notes": problem_answer_data.get("notes"),
            }

        # 2. 统计原始数据分布
        type_counter = Counter()
        original_type_counter = Counter()
        domain_counter = Counter()
        correctness_counter = Counter()

        for entry in answer_pair_dict.values():
            type_counter[entry["type"]] += 1
            original_type_counter[entry["original_type"]] += 1
            domain_counter[entry["domain"]] += 1
            correctness_counter[entry.get("correctness")] += 1

        print("不同 type 及数量:", dict(type_counter))
        print("不同 original_type 及数量:", dict(original_type_counter))
        print("不同 domain 及数量:", dict(domain_counter))
        print("不同 correctness 及数量:", dict(correctness_counter))

        # 3. 加载 LLM 答案并合并
        # [修改] 使用传入的 memory_answers 进行评估，不再扫描文件夹
        
        if not memory_answers:
            print("Warning: No answers provided for evaluation.")
        
        for answer_data in tqdm(memory_answers, desc="Processing LLM answers"):
            # [关键修复]：确保 answer_data 是字典，解决 TypeError: string indices must be integers
            if not isinstance(answer_data, dict):
                # 如果列表里混入了字符串，直接跳过
                continue
            
            # [关键修复]：确保 filename 字段存在
            if "filename" not in answer_data:
                continue

            try:
                tmp_filename = answer_data["filename"].replace(" ", "")
                question_number = answer_data["question_number"]
                sub_id = answer_data["sub_id"]
                
                key = "%s_%s_%s" % (tmp_filename, question_number, sub_id)
                if key not in answer_pair_dict:
                    continue
                answer_pair_dict[key]["llm_answer"] = answer_data["answer"]
            except Exception as e:
                print(f"Error processing answer item: {e}, Data: {answer_data}")
                continue

        # 保存对齐后的字典
        with open(os.path.join(self.output_dir, "answer_pair_dict.json"), "w", encoding="utf-8") as f:
            json.dump(answer_pair_dict, f, ensure_ascii=False, indent=4)

        # 4. 计算评分
        results = []
        total_score, total_answered_count, total_non_answered_count = 0, 0, 0
        total_calculation_score, total_calculation_count = 0, 0
        total_choice_score, total_choice_count = 0, 0
        total_true_false_score, total_true_false_count = 0, 0
        total_short_answer_score, total_short_answer_count = 0, 0
        total_original_choice_score, total_original_choice_count = 0, 0
        total_electrochemistry_score, total_electrochemistry_count = 0, 0
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
            
            elif type_ == "True/False":
                gt_answer = answer_pair_data["gt_answer"]
                llm_answer = list(collapse(answer_pair_data["llm_answer"]))[0]
                score = int(gt_answer == llm_answer)
                total_true_false_score += score
                total_true_false_count += 1
            else:
                print("Invalid question type:", type_)
                continue

            # 领域和子类型统计
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

        print("\nEvaluation Results:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"✅ 评测完成，总答题数 {total_answered_count}，平均得分 {summary['average_score']:.2f}，未答题数量 {total_non_answered_count}")
        
        # 保存详细结果 JSON
        result_file = os.path.join(self.output_dir, "evaluation_summary.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)
        
        return summary

# ==========================================
# 主程序入口
# ==========================================
if __name__ == "__main__":
    # 配置路径
    MODEL_PATH = "/home/chemind/allcode_chemind_server/mergedoutput/qwen3-8b-sft-md_quitQA_data-merged"
    QUESTIONS_FILE = "/home/chemind/allcode_chemind_server/evaluate/eval_dataset/v1/习题问答对_v1test.json"
    
    # 自动根据模型路径生成输出目录名
    model_name = os.path.basename(os.path.normpath(MODEL_PATH))
    OUTPUT_DIR = f"/home/chemind/allcode_chemind_server/testoutput/{model_name}_eval"

    # 初始化评估器
    evaluator = LocalEvaluator(
        model_path=MODEL_PATH,
        questions_file=QUESTIONS_FILE,
        output_dir=OUTPUT_DIR,
        batch_size=1 
    )

    # 1. 运行推理 (结果保存在内存中，不生成 chunk 文件)
    all_results = evaluator.run_inference()
    
    # 2. 释放显存
    gc.collect()
    torch.cuda.empty_cache()

    # 3. 运行评分 (直接传入内存结果)
    summary_dict = evaluator.run_evaluation(all_results)

    # 4. 保存 CSV 结果
    all_dict = {}
    key_name = model_name
    all_dict[key_name] = summary_dict

    df = pd.DataFrame.from_dict(all_dict, orient="index")
    csv_file = f"/home/chemind/allcode_chemind_server/testoutput/{model_name}_eval/model_evaluation_results.csv"
    df.to_csv(csv_file, encoding="utf-8-sig")
    print(f"Summary saved to {csv_file}")