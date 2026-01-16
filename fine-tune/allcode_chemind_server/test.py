import os
import json
import csv
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel  # 新增：用于加载 LoRA
from typing import List, Dict, Tuple
import time
import re
from tqdm import tqdm  # 建议安装：pip install tqdm

'''
代码修改详情解释
Chat Template (关键)：
在 predict 函数中，我使用了 self.tokenizer.apply_chat_template。
原因：SFT 训练时，模型学习的是 <|im_start|>system... 这种 token 结构。如果不使用 apply_chat_template，模型会把输入当成普通的续写任务，而不是对话指令，这会导致推理能力大打折扣。

LoRA 自动挂载：
在 __init__ 中增加了 PeftModel 的判断。
原因：Trainer 保存的通常是 Adapter（几百MB）。直接用 AutoModel 加载那个文件夹会报错或只加载一个空的 Config。必须先加载基座，再用 PeftModel.from_pretrained 把训练好的 Adapter 挂上去。

Prompt 调整：
将 Prompt 里的英文指令改为了中文：“请仔细阅读以下题目...”。
原因：根据您之前提供的信息，您的微调数据主要是中文医学内容。在测试时保持语言一致性（Training-Inference Consistency）能获得更好的性能。

生成参数调整：
设置 do_sample=False 和 temperature=0.01。
原因：做选择题评估时，我们希望模型输出是确定性的（Greedy Decoding），不需要它发挥“创造力”，这样可以保证结果的可复现性。
'''



class QuestionEvaluator:
    def __init__(self, model_path: str, base_model_path: str = None):
        """
        初始化评估器
        
        Args:
            model_path: 微调后的模型路径（如果是LoRA，这是adapter路径；如果是全量/合并模型，这是模型路径）
            base_model_path: 如果 model_path 是 LoRA，这里需要填基座模型路径（如 Qwen/Qwen2.5-7B-Instruct）
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"正在加载 Tokenizer: {model_path}")
        
        # 1. 加载 Tokenizer
        # 如果是 LoRA，通常 tokenizer 还在基座目录或 adapter 目录，优先尝试 adapter 目录
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        except:
            if base_model_path:
                self.tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)
            else:
                raise ValueError("无法加载 Tokenizer，请指定 base_model_path")

        # 2. 智能加载模型 (适配 LoRA 或 全量)
        print(f"正在加载模型...")
        if os.path.exists(os.path.join(model_path, "adapter_config.json")):
            print("检测到 LoRA 权重，正在加载基座模型并挂载 LoRA...")
            if not base_model_path:
                raise ValueError("检测到 LoRA 路径，必须提供 base_model_path (基座模型路径)")
            
            # 加载基座
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model_path,
                torch_dtype=torch.bfloat16, # 5090 推荐 bf16
                device_map="auto",
                trust_remote_code=True
            )
            # 挂载 LoRA
            self.model = PeftModel.from_pretrained(self.model, model_path)
        else:
            print("加载全量/合并模型...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True
            )
        
        self.model.eval() # 开启评估模式
        print(f"模型加载完成，设备: {self.device}")
        
    def create_prompt_messages(self, question_data: Dict) -> List[Dict]:
        """
        构建符合 Qwen Chat 格式的消息列表
        """
        stem = question_data.get("question_stem", "") or question_data.get("question", {}).get("question_stem", "")
        question = question_data.get("question", "") or question_data.get("question", {}).get("question", "")
        options_list = question_data.get("options", []) or question_data.get("question", {}).get("options", [])
        
        # 处理选项格式
        if isinstance(options_list, list):
            options_str = "\n".join(options_list)
        else:
            options_str = str(options_list)
            
        # 构造输入内容
        user_content = f"""请仔细阅读以下题目，并选出正确答案。

【题目背景】：
{stem}

【问题】：
{question}

【选项】：
{options_str}

请按照以下格式输出：
Answer: [这里填写 A/B/C/D]
Reasoning: [这里填写详细的推理过程]
"""
        # 使用 Chat 格式
        messages = [
            {"role": "system", "content": "你是一个专业的医学考试专家。请先进行深度思考，然后给出正确选项。"},
            {"role": "user", "content": user_content}
        ]
        
        return messages
    
    def extract_answer_and_reasoning(self, response: str) -> Tuple[str, str]:
        """
        优化后的正则提取，支持更多模型输出的边缘情况
        """
        answer = ""
        reasoning = ""
        
        # 1. 优先提取 Answer: X 格式
        answer_match = re.search(r"Answer:\s*([A-D])", response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
        else:
            # 2. 兜底：如果没按格式，尝试找 "答案是 X" 或 "选项 X"
            backup_patterns = [
                r"答案(?:是|为|选)[:\s]*([A-D])",
                r"选项[:\s]*([A-D])",
                r"^([A-D])$" # 只有单独一个字母的情况
            ]
            for p in backup_patterns:
                m = re.search(p, response)
                if m:
                    answer = m.group(1).upper()
                    break
        
        # 3. 提取推理
        reasoning_match = re.search(r"Reasoning:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
        else:
            # 如果没有 Reasoning 标签，把 Answer 标签之后的所有内容都当作推理
            if answer_match:
                reasoning = response[answer_match.end():].strip()
            else:
                reasoning = response.strip()

        return answer, reasoning
    
    def predict(self, messages: List[Dict]) -> Tuple[str, str, str]:
        # 核心修改：使用 apply_chat_template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                max_new_tokens=512, # 思考过程可能较长
                temperature=0.01,   # 测试时降低随机性，趋近贪婪采样
                top_p=0.9,
                do_sample=False,    # 确定性输出
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # 只解码新增的部分
        generated_ids = outputs[0][len(inputs.input_ids[0]):]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        answer, reasoning = self.extract_answer_and_reasoning(response)
        return answer, reasoning, response
    
    def load_test_data(self, data_path: str) -> List[Dict]:
        """
        兼容加载 json 列表、jsonl 或 单个 json 文件
        """
        all_data = []
        
        # 如果是目录，读取目录下所有 .json/.jsonl
        if os.path.isdir(data_path):
            files = [os.path.join(data_path, f) for f in os.listdir(data_path) if f.endswith(('.json', '.jsonl'))]
        else:
            files = [data_path]
            
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                if file.endswith('.jsonl'):
                    for line in f:
                        if line.strip(): all_data.append(json.loads(line))
                else:
                    try:
                        content = json.load(f)
                        if isinstance(content, list):
                            all_data.extend(content)
                        else:
                            all_data.append(content)
                    except json.JSONDecodeError:
                        print(f"Warning: {file} 解析失败")
        return all_data

    def run_evaluation(self, data_path: str, output_csv: str):
        questions = self.load_test_data(data_path)
        print(f"共加载 {len(questions)} 道题目")
        
        results = []
        correct_count = 0
        
        # 使用 tqdm 显示进度条
        for item in tqdm(questions, desc="Evaluating"):
            try:
                # 假设正确答案字段是 "answer" 或 "correct_answer"
                true_answer_raw = item.get("answer", "") or item.get("correct_answer", "")
                # 处理答案是列表的情况 ["A"] -> "A"
                true_answer = true_answer_raw[0] if isinstance(true_answer_raw, list) and len(true_answer_raw)>0 else str(true_answer_raw)
                
                messages = self.create_prompt_messages(item)
                
                start_t = time.time()
                pred_answer, reasoning, raw_resp = self.predict(messages)
                cost_time = time.time() - start_t
                
                is_correct = (pred_answer == true_answer.upper())
                if is_correct: correct_count += 1
                
                results.append({
                    "id": item.get("id", ""),
                    "question": messages[1]['content'][:50] + "...", # 截断显示
                    "true_answer": true_answer,
                    "pred_answer": pred_answer,
                    "is_correct": is_correct,
                    "reasoning": reasoning,
                    "raw_response": raw_resp,
                    "cost_time": round(cost_time, 2)
                })
                
            except Exception as e:
                print(f"Error processing item: {e}")
                continue
        
        accuracy = correct_count / len(questions) if questions else 0
        print(f"\n评估结束！准确率: {accuracy:.2%}")
        
        # 保存
        keys = results[0].keys() if results else []
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
            
        return accuracy

def main():
    # === 配置区域 ===
    
    # 情况A：如果你已经合并了模型，只填 MODEL_PATH
    # MODEL_PATH = "/path/to/merged_model"
    # BASE_MODEL = None
    
    # 情况B：如果你使用的是 LoRA (推荐)，MODEL_PATH 填 output 目录，BASE_MODEL 填原版 Qwen
    MODEL_PATH = "./output/qwen2.5-7b-lora/checkpoint-final" # 你的 LoRA output 路径
    BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct" # 你的基座模型路径
    
    TEST_DATA_PATH = "./data/test_questions.jsonl" # 支持文件或文件夹
    OUTPUT_CSV = "eval_result.csv"
    
    evaluator = QuestionEvaluator(MODEL_PATH, BASE_MODEL)
    evaluator.run_evaluation(TEST_DATA_PATH, OUTPUT_CSV)

if __name__ == "__main__":
    main()