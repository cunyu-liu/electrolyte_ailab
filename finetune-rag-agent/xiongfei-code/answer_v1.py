import os
import json
import csv
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Dict, Tuple
import time

class QuestionEvaluator:
    def __init__(self, model_path: str, questions_dir: str):
        """
        初始化评估器
        
        Args:
            model_path: 微调模型路径
            questions_dir: 题目文件夹路径
        """
        self.model_path = model_path
        self.questions_dir = questions_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载模型和tokenizer
        print(f"正在加载模型: {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
            trust_remote_code=True
        )
        print(f"模型加载完成，设备: {self.device}")
        
    def create_prompt(self, question_data: Dict) -> str:
        """
        创建英文prompt，要求模型先给出答案再给出思考过程
        
        Args:
            question_data: 题目数据
            
        Returns:
            str: 构建的prompt
        """
        stem = question_data["question"]["question_stem"]
        question = question_data["question"]["question"]
        options = "\n".join(question_data["question"]["options"])
        
        prompt = f"""You are an expert in answering multiple choice questions. Please read the following question carefully and select the correct answer.

Question Context:
{stem}

Specific Question:
{question}

Options:
{options}

Instructions:
1. Analyze the question carefully
2. Consider all options
3. Your response MUST follow this format:
   Answer: [Single letter A, B, C, or D]
   Reasoning: [Your detailed reasoning process here]

Example format:
Answer: B
Reasoning: The question asks about... After analyzing... Therefore, option B is correct.

Your response:"""
        
        return prompt
    
    def extract_answer_and_reasoning(self, response: str) -> Tuple[str, str]:
        """
        从模型响应中提取答案和思考过程
        
        Args:
            response: 模型生成的文本
            
        Returns:
            Tuple[str, str]: (提取的答案, 提取的思考过程)
        """
        answer = ""
        reasoning = ""
        
        # 尝试提取"Answer:"和"Reasoning:"格式
        answer_match = None
        reasoning_match = None
        
        # 查找Answer:部分
        answer_patterns = [
            r"Answer:\s*([ABCD])",
            r"Answer:\s*([A-D])",
            r"^\s*([ABCD])\s*$"
        ]
        
        import re
        for pattern in answer_patterns:
            answer_match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if answer_match:
                answer = answer_match.group(1).upper()
                break
        
        # 如果没有找到匹配的答案格式，尝试提取第一个A/B/C/D字母
        if not answer:
            first_letter_match = re.search(r'[ABCD]', response.upper())
            if first_letter_match:
                answer = first_letter_match.group()
        
        # 查找Reasoning:部分
        reasoning_patterns = [
            r"Reasoning:\s*(.*?)(?=\n\s*\n|\Z)",  # 匹配Reasoning:后的内容直到空行或结尾
            r"Reasoning:\s*(.*)",  # 简单匹配
        ]
        
        for pattern in reasoning_patterns:
            reasoning_match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                break
        
        # 如果没找到Reasoning，但找到了Answer，尝试提取Answer之后的内容作为reasoning
        if not reasoning and answer_match:
            # 获取Answer之后的所有内容
            answer_end = answer_match.end()
            reasoning = response[answer_end:].strip()
            # 清理可能的前导换行和空白
            reasoning = re.sub(r'^\s*[\n\r]+', '', reasoning)
            reasoning = re.sub(r'^\s*Reasoning:\s*', '', reasoning, flags=re.IGNORECASE)
        
        # 如果reasoning太长，截断（保持原始响应完整）
        if len(reasoning) > 500:
            reasoning = reasoning[:497] + "..."
            
        return answer, reasoning
    
    def predict_answer(self, prompt: str) -> Tuple[str, str, str]:
        """
        使用模型预测答案
        
        Args:
            prompt: 构建的prompt
            
        Returns:
            Tuple[str, str, str]: (预测的答案, 思考过程, 原始响应)
        """
        # 编码输入
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        # 生成回答 - 增加max_new_tokens以便有足够空间输出思考过程
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                max_new_tokens=200,  # 增加token数量以容纳思考过程
                temperature=0.1,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # 解码输出
        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], 
                                         skip_special_tokens=True)
        
        # 提取答案和思考过程
        answer, reasoning = self.extract_answer_and_reasoning(response)
        return answer, reasoning, response
    
    def process_questions(self) -> List[Dict]:
        """
        处理所有题目
        
        Returns:
            List[Dict]: 处理结果列表
        """
        results = []
        question_files = [f for f in os.listdir(self.questions_dir) 
                         if f.endswith('.json')]
        
        print(f"找到 {len(question_files)} 个题目文件")
        
        for filename in question_files:
            filepath = os.path.join(self.questions_dir, filename)
            
            try:
                # 读取题目文件
                with open(filepath, 'r', encoding='utf-8') as f:
                    question_data = json.load(f)
                
                # 构建prompt
                prompt = self.create_prompt(question_data)
                
                # 获取模型预测
                start_time = time.time()
                predicted_answer, reasoning, raw_response = self.predict_answer(prompt)
                inference_time = time.time() - start_time
                
                # 获取标准答案（处理可能的多选情况）
                correct_answers = question_data["answer"]
                correct_answer = correct_answers[0] if correct_answers else ""
                
                # 检查是否正确
                is_correct = predicted_answer.upper() == correct_answer.upper() if predicted_answer else False
                
                # 记录结果
                result = {
                    "filename": filename,
                    "question_type": question_data.get("type", "Unknown"),
                    "question_stem": question_data["question"]["question_stem"],
                    "specific_question": question_data["question"]["question"],
                    "options": question_data["question"]["options"],
                    "predicted_answer": predicted_answer,
                    "predicted_reasoning": reasoning,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "inference_time": round(inference_time, 2),
                    "raw_response": raw_response,
                    "model_path": self.model_path,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                results.append(result)
                
                print(f"处理: {filename} | 预测: {predicted_answer} | 正确答案: {correct_answer} | 正确: {is_correct}")
                
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {str(e)}")
                results.append({
                    "filename": filename,
                    "error": str(e),
                    "is_correct": False,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return results
    
    def save_results_to_csv(self, results: List[Dict], output_file: str = "evaluation_results_qwen.csv"):
        """
        保存结果到CSV文件
        
        Args:
            results: 处理结果
            output_file: 输出文件名
        """
        if not results:
            print("没有结果可保存")
            return
        
        # 准备CSV数据
        csv_data = []
        for result in results:
            if "error" in result:
                # 处理出错的情况
                row = {
                    "filename": result.get("filename", ""),
                    "question_type": "ERROR",
                    "predicted_answer": "",
                    "predicted_reasoning": "",
                    "correct_answer": "",
                    "is_correct": False,
                    "inference_time_seconds": 0,
                    "specific_question": "",
                    "error": result.get("error", "")
                }
            else:
                row = {
                    "filename": result.get("filename", ""),
                    "question_type": result.get("question_type", ""),
                    "predicted_answer": result.get("predicted_answer", ""),
                    "predicted_reasoning": result.get("predicted_reasoning", ""),
                    "correct_answer": result.get("correct_answer", ""),
                    "is_correct": result.get("is_correct", False),
                    "inference_time_seconds": result.get("inference_time", 0),
                    "specific_question": result.get("specific_question", "")[:200],  # 截断以便在CSV中显示
                    "raw_response_preview": result.get("raw_response", "")[:200] + "..." if len(result.get("raw_response", "")) > 200 else result.get("raw_response", "")
                }
            csv_data.append(row)
        
        # 写入CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ["filename", "question_type", "predicted_answer", 
                         "predicted_reasoning", "correct_answer", "is_correct", 
                         "inference_time_seconds", "specific_question", 
                         "raw_response_preview", "error"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"CSV结果已保存到: {output_file}")
    
    def save_results_to_json(self, results: List[Dict], output_file: str = "evaluation_results.json"):
        """
        保存完整结果到JSON文件
        
        Args:
            results: 处理结果
            output_file: 输出文件名
        """
        if not results:
            print("没有结果可保存到JSON")
            return
        
        # 计算统计信息
        total = len(results)
        correct_results = [r for r in results if r.get("is_correct", False) and "error" not in r]
        correct = len(correct_results)
        accuracy = correct / total * 100 if total > 0 else 0
        
        # 创建完整的JSON结构
        json_output = {
            "metadata": {
                "model_path": self.model_path,
                "total_questions": total,
                "correct_answers": correct,
                "accuracy": round(accuracy, 2),
                "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "device": str(self.device)
            },
            "results": results,
            "summary_by_type": self._get_summary_by_type(results)
        }
        
        # 写入JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, ensure_ascii=False, indent=2)
        
        print(f"JSON结果已保存到: {output_file}")
        
        # 打印统计信息
        self._print_summary(total, correct, accuracy)
    
    def _get_summary_by_type(self, results: List[Dict]) -> Dict:
        """
        按题目类型统计
        
        Args:
            results: 处理结果
            
        Returns:
            Dict: 按类型统计的结果
        """
        type_stats = {}
        for result in results:
            if "error" in result:
                continue
                
            q_type = result.get("question_type", "Unknown")
            if q_type not in type_stats:
                type_stats[q_type] = {"total": 0, "correct": 0}
            type_stats[q_type]["total"] += 1
            if result.get("is_correct", False):
                type_stats[q_type]["correct"] += 1
        
        # 计算准确率
        for q_type in type_stats:
            if type_stats[q_type]["total"] > 0:
                type_stats[q_type]["accuracy"] = round(
                    type_stats[q_type]["correct"] / type_stats[q_type]["total"] * 100, 2
                )
        
        return type_stats
    
    def _print_summary(self, total: int, correct: int, accuracy: float):
        """
        打印统计摘要
        
        Args:
            total: 总题目数
            correct: 正确数
            accuracy: 准确率
        """
        print(f"\n{'='*60}")
        print(f"评估完成！")
        print(f"总题目数: {total}")
        print(f"正确数: {correct}")
        print(f"准确率: {accuracy:.2f}%")
        print(f"{'='*60}")
        
        # 生成详细报告
        self.generate_detailed_report(total, correct, accuracy)
    
    def generate_detailed_report(self, total: int, correct: int, accuracy: float):
        """
        生成详细统计报告
        
        Args:
            total: 总题目数
            correct: 正确数
            accuracy: 总体准确率
        """
        report_file = "evaluation_summary.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("题目评估结果汇总\n")
            f.write("="*80 + "\n\n")
            
            # 总体统计
            f.write(f"总体统计:\n")
            f.write(f"- 总题目数: {total}\n")
            f.write(f"- 正确数: {correct}\n")
            f.write(f"- 准确率: {accuracy:.2f}%\n")
            f.write(f"- 模型路径: {self.model_path}\n")
            f.write(f"- 评估时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- 运行设备: {self.device}\n\n")
            
            # 按题目类型统计
            f.write("按题目类型统计:\n")
            f.write("-" * 40 + "\n")
            f.write(f"{'类型':<20} {'正确数':<10} {'总数':<10} {'准确率':<10}\n")
            f.write("-" * 40 + "\n")
            
            # 这里需要results数据，我们会在调用时从JSON文件读取或传递
            f.write("（详细类型统计请查看JSON文件）\n\n")
            
            # 建议和改进
            f.write("改进建议:\n")
            f.write("1. 检查模型是否遵循输出格式要求\n")
            f.write("2. 查看错误题目，分析常见错误类型\n")
            f.write("3. 考虑调整prompt以改进模型表现\n")
            f.write("4. 检查训练数据质量\n")
        
        print(f"详细报告已保存到: {report_file}")

def main():
    # 配置路径
    MODEL_PATH = "/data/qwen"  # 你的微调模型路径
    QUESTIONS_DIR = "/data/questions"  # 题目文件夹路径
    
    # 确保文件夹存在
    if not os.path.exists(QUESTIONS_DIR):
        print(f"错误: 题目文件夹 '{QUESTIONS_DIR}' 不存在！")
        return
    
    if not os.path.exists(MODEL_PATH):
        print(f"错误: 模型文件夹 '{MODEL_PATH}' 不存在！")
        return
    
    # 创建评估器并运行
    evaluator = QuestionEvaluator(MODEL_PATH, QUESTIONS_DIR)
    
    print("开始处理题目...")
    results = evaluator.process_questions()
    
    # 保存结果到CSV和JSON
    evaluator.save_results_to_csv(results, "evaluation_results_qwen.csv")
    evaluator.save_results_to_json(results, "evaluation_results_qwen.json")
    
    print("\n评估完成！结果已保存到:")
    print("- evaluation_results_qwen.csv (包含答案和思考过程)")
    print("- evaluation_results_qwen.json (完整详细结果)")
    print("- evaluation_summary_qwen.txt (统计摘要)")

if __name__ == "__main__":
    main()