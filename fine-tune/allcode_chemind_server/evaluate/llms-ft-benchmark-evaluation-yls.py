
# [新增] 引入本地模型推理所需的库
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import gc
import sys
from concurrent.futures import ThreadPoolExecutor
import logging
import concurrent.futures
import concurrent.futures
import os
import re
import json
import time
from math import isclose
from difflib import SequenceMatcher
from collections import Counter
# from utils import retry_with_json
from tqdm import tqdm
import more_itertools


# 配置日志输出到文件和控制台
log_formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s (line %(lineno)d): %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 控制台日志
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# # 文件日志（滚动保存）
# file_handler = RotatingFileHandler(
#     "app.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
# )
# file_handler.setFormatter(log_formatter)

# 基础配置
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler]
)
# [新增] 全局变量存储本地模型
LOCAL_MODEL = None
LOCAL_TOKENIZER = None
def clean_json_text(text: str) -> str:
    """
    进行了深度的修复应该可以应对各种转义
    提取 JSON 部分并清理 Markdown、全角引号及非法引号问题
    新增反斜杠转义处理
    """
    # 去掉 Markdown 代码块标记
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)

    # 提取 JSON 主体
    json_match = re.search(r'(\{.*\}|\[.*\])', text, flags=re.DOTALL)
    if not json_match:
        raise ValueError("❌ 文本中未找到 JSON 部分")
    json_text = json_match.group(0)

    # 删除 ASCII 控制字符 (0x00 - 0x1F), 保留 \n \r \t
    json_text = re.sub(r'\\x[0-9a-fA-F]{2}', '', json_text)

    # 修复全角引号
    json_text = json_text.replace("“", r'\"').replace("”", r'\"').replace("‘", "'").replace("’", "'")

    # 新增：处理反斜杠转义问题
    def escape_backslashes_in_strings(match):
        """处理字符串值中的反斜杠"""
        string_content = match.group(1)
        # 转义反斜杠，但保留已转义的序列（如 \n, \t 等）
        # 匹配未转义的反斜杠（前面没有反斜杠的反斜杠）
        string_content = re.sub(r'(?<!\\)\\(?![\\"bfnrtu])', r'\\\\', string_content)
        return '"' + string_content + '"'

    # 处理所有JSON字符串中的反斜杠
    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_backslashes_in_strings, json_text)

    # 修复非法的内部引号（不影响已转义的 \")
    def escape_inner_quotes(match):
        inner = match.group(1)
        # 只替换未转义的 "
        fixed_inner = re.sub(r'(?<!\\)"', r'\"', inner)
        return '"' + fixed_inner + '"'

    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_inner_quotes, json_text)

    return json_text

def retry_with_json(func, *args, max_retries=2, retry_delay=0, length_check=None, **kwargs):
    """
    多次重试执行函数并解析 JSON。

    Args:
        func: 要执行的函数（返回字符串）。
        *args, **kwargs: 传给 func 的参数。
        max_retries: 最大重试次数。
        retry_delay: 重试之间的延迟（秒）。
        length_check: 如果传入一个 int，会检查解析结果长度是否匹配。

    Returns:
        解析后的 JSON 对象。

    Raises:
        ValueError: 超过重试次数仍解析失败。
    """
    for attempt in range(1, max_retries + 1):
        t = time.time()
        # with open(f"tmp", 'w', encoding="utf-8") as fp:
        #     fp.write(raw_output)
        try:
            raw_output = func(*args, **kwargs)
            logging.info(f"{func.__name__} took {time.time() - t:.2f} seconds (attempt {attempt}/{max_retries})")

            results = json.loads(clean_json_text(raw_output))

            if length_check is not None and len(results) != length_check:
                raise ValueError(f"Length mismatch: expected {length_check}, got {len(results)}")

            return results  # 成功解析，直接返回

        except Exception as e:
            logging.error(f"Error parsing JSON from {func.__name__} (attempt {attempt}/{max_retries}): {e}")
            try:
                logging.error(f"Raw output: {raw_output}")
            except:
                pass
            import random
            r=str(random.random())[:5]
            try:
                with open(f"tmp_{r}", 'w', encoding="utf-8") as fp:
                    fp.write(raw_output)
            except:
                pass
            if attempt >= max_retries:
                raise ValueError(f"{func.__name__} failed after max retries") from e

            if retry_delay > 0:
                time.sleep(retry_delay)

    # 理论上不会走到这里
    raise ValueError(f"{func.__name__} failed unexpectedly")

# [新增] 初始化本地模型
def init_local_model(model_path):
    global LOCAL_MODEL, LOCAL_TOKENIZER
    print(f"Loading local model from {model_path}...")
    LOCAL_TOKENIZER = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    LOCAL_MODEL = AutoModelForCausalLM.from_pretrained(
        model_path, 
        device_map="auto", 
        torch_dtype=torch.float16, 
        trust_remote_code=True
    ).eval()

# [新增] 清理本地模型释放显存
def clear_local_model():
    global LOCAL_MODEL, LOCAL_TOKENIZER
    import gc
    del LOCAL_MODEL
    del LOCAL_TOKENIZER
    LOCAL_MODEL = None
    LOCAL_TOKENIZER = None
    gc.collect()
    torch.cuda.empty_cache()
    print("Local model cleared.")

def is_low_quality_problem(problem_answer,filename):
    if problem_answer["is_figure_question"]:
        return  True
    if problem_answer["evaluation"]["correctness"] == "Low":
        return  True
    # if problem_answer["question_type"] not in ["True/False","Calculation","ShortAnswer&Proof","ShortAnswer&Proof&Calculation","Choice"]:
    #     return  True

    if "repaired_translated" in problem_answer:
        if not problem_answer["repaired_translated"]["answer"]:

            return  True

    if "lidi" in filename:
        if "思考题" in problem_answer["question_num"]:
            return  True

    return  False





def create_LLM_answer_process_main():
    from openai import OpenAI
    API_KEY = "sk-e387e1a310824ad7ac7b84f6f82cd284"  # 或你的环境变量名
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com/v1")
    MODEL_NAME="qwen3-8b"#"deepseek-chat"
    WWXQ_API_KEY="sk-yeqwxkqsinzddrwz"
    WWXQ_MY_API_KEY="sk-2xoohlqxvrqwv6fq"
    WWXQ_BASE_URL="https://cloud.infini-ai.com/maas/v1"
    wwxq_client = OpenAI(api_key=WWXQ_MY_API_KEY, base_url=WWXQ_BASE_URL)

    input_json_list=json.load(open(PROBLEM_FILE,"r",encoding="utf-8"),)
    input_json_list_chunks = [input_json_list[i:i + 20] for i in range(0, len(input_json_list), 20)]
    def LLM_get_answer(text_json):
        sys_prompt="""
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

Begin processing the question list now.
"""

        # [修改] 插入本地模型推理逻辑
        if LOCAL_MODEL is not None:
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text_json}
            ]
            # 应用聊天模板
            text = LOCAL_TOKENIZER.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            model_inputs = LOCAL_TOKENIZER([text], return_tensors="pt").to(LOCAL_MODEL.device)
            
            with torch.no_grad():
                generated_ids = LOCAL_MODEL.generate(
                    **model_inputs,
                    max_new_tokens=4096,  # 根据题目长度需要调整，Qwen通常支持较长
                    temperature=0.7,      # 保持一定的多样性
                    top_p=0.9
                )
            # 裁剪掉输入部分的token
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            raw_output = LOCAL_TOKENIZER.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return raw_output
            
        elif MODEL_NAME == "qwen3-8b":
 
            # from utils import client as client
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": text_json}
                ],
            )
            raw_output = response.choices[0].message.content
            return raw_output
        else:
            # from utils import wwxq_client as client,WWXQ_MY_API_KEY as WWXQ_API_KEY,WWXQ_BASE_URL

            import requests
            url = f"{WWXQ_BASE_URL}/chat/completions"
            payload = {
                "model":MODEL_NAME,
                "messages":[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": text_json}
                ],
                #"enable_thinking": True,
                "stream": False
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream, */*",
                "Authorization": f"Bearer {WWXQ_API_KEY}"
            }
            response = requests.post(url, json=payload, headers=headers)
            try:
                raw_output=json.loads(response.content)["choices"][0]["message"]["content"]
            except:
                raw_output = response.content
            return raw_output

    def process_file(problem_answer_list,chunk_id):


        output_json_file = os.path.join(LLM_ANSWER_DIR, f"{chunk_id}_answer.json")
        if os.path.exists(output_json_file):
            tmp_data_list=json.load(open(output_json_file, "r", encoding="utf-8"))
            if len(tmp_data_list)==20:

                return f"Skipped {chunk_id}"
            else:
                return (rf"less:{len(tmp_data_list)} {chunk_id}")


        print(f"Processing {chunk_id}")

        problem_list=[]

        for problem_answer in problem_answer_list:

            try:
                problem_list.append({
                "filename":problem_answer["filename"],
                "question_number": problem_answer["question_number"],
                "sub_id":problem_answer["sub_id"],
                "question": problem_answer["question"],
                "type": problem_answer["type"],
                "answer_data_type": problem_answer["answer_data_type"],
                "domain": problem_answer["domain"],
                })
            except:
                print(problem_answer)
        print("OK ", chunk_id)

        problem_text=json.dumps(problem_list)
        # 处理数据
        try:
            question_answer_json = retry_with_json(LLM_get_answer,
                                               problem_text,max_retries=2,retry_delay=60)
        except Exception as e:
            print( e)
            return f"Failed {chunk_id}"

        for i in range(3):
            if len(question_answer_json) != len(problem_list):
                print(chunk_id, "len(question_answer_json) != len(problem_list)", i)
                try:
                    question_answer_json=retry_with_json(LLM_get_answer,
                                problem_text)
                except:
                    print(chunk_id, "retry_with_json")

            else:
                break




        # 保存结果
        with open(output_json_file, "w", encoding="utf-8") as fp:
            json.dump(question_answer_json, fp, ensure_ascii=False, indent=4)

        return f"Completed {chunk_id}"


    # for i in range(len(input_json_list_chunks)):
    #         print(process_file(input_json_list_chunks[i],i))
    # 使用线程池执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        results = executor.map(
            lambda args: process_file(*args),
            [(chunk, i) for i, chunk in enumerate(input_json_list_chunks)]
        )
        for result in tqdm(results):
            print(result)



def get_answer_pair_dict():
    answer_pair_dict = {}
    ground_truth_answer_list = json.load(open(PROBLEM_FILE, "r", encoding="utf-8"))
    for problem_answer_data in tqdm(ground_truth_answer_list, desc="Loading ground truth answers",):
        filename=problem_answer_data["filename"].replace(" ", "")#LLM把文件名中的空格删掉了
        question_number = problem_answer_data["question_number"]
        sub_id=problem_answer_data["sub_id"]
        if "original_type" in problem_answer_data:
            original_type=problem_answer_data["original_type"].replace(" ", "")
        else:
            original_type=problem_answer_data["type"]
        answer_pair_dict["%s_%s_%s"%(filename,question_number,sub_id)]={
            "gt_answer": problem_answer_data["answer"],
            "question": problem_answer_data["question"],
            "type": problem_answer_data["type"],
            "original_type":original_type,
            "solution":problem_answer_data["solution"],
            "domain":problem_answer_data["domain"],
            "correctness":problem_answer_data["correctness"],
            "notes":problem_answer_data["notes"],
        }
    # 假设 answer_pair_dict 已经构建好
    type_counter = Counter()
    original_type_counter = Counter()
    domain_counter = Counter()
    correctness_counter = Counter()

    for entry in answer_pair_dict.values():
        type_counter[entry["type"]] += 1
        original_type_counter[entry["original_type"]] += 1
        domain_counter[entry["domain"]] += 1
        correctness_counter[entry["correctness"]] += 1

    print("不同 type 及数量:", dict(type_counter))
    print("不同 original_type 及数量:", dict(original_type_counter))
    print("不同 domain 及数量:", dict(domain_counter))
    print("不同 correctness 及数量:", dict(correctness_counter))

    for filename in tqdm(os.listdir(LLM_ANSWER_DIR), desc="Loading LLM answers"):
        if not filename.endswith(".json"):
            continue
        if filename=="answer_pair_dict.json":
            continue
        try:
            tmp_answer_json_list=json.load(open(os.path.join(LLM_ANSWER_DIR, filename), "r", encoding="utf-8"))
        except:
            print("Error loading", filename)
            continue
        for answer_data in tmp_answer_json_list:

            tmp_filename = answer_data["filename"].replace(" ", "")

            question_number = answer_data["question_number"]
            sub_id = answer_data["sub_id"]
            if "%s_%s_%s"%(tmp_filename, question_number, sub_id) not in answer_pair_dict:
                print("No ground truth answer for", filename,tmp_filename, question_number, sub_id)
                continue
            answer_pair_dict["%s_%s_%s"%(tmp_filename, question_number, sub_id)]["llm_answer"]= answer_data["answer"],



    with open(os.path.join(LLM_ANSWER_DIR, f"answer_pair_dict.json"), "w", encoding="utf-8") as f:
        json.dump(answer_pair_dict, f, ensure_ascii=False, indent=4)


def get_evluation_score():
    with open(os.path.join(LLM_ANSWER_DIR, f"answer_pair_dict.json"), "r", encoding="utf-8") as f:
        answer_pair_dict = json.load(f)

    evaluation_result_file=os.path.join(LLM_ANSWER_DIR, "evaluation_result.json")
    results = []
    total_score, total_answered_count,total_non_answered_count = 0, 0, 0
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
    from more_itertools import collapse
    for question_key in answer_pair_dict:
        answer_pair_data=answer_pair_dict[question_key]
        type=answer_pair_data["type"]

        if "llm_answer" not in answer_pair_data:
            total_non_answered_count+=1
            continue

        if type=="Calculation":
            gt_answer = answer_pair_data["gt_answer"]
            llm_answer = [answer_pair_data["llm_answer"]]
            llm_answer= list(collapse(llm_answer))
            try:
                llm_answer=float(llm_answer[0])
            except:
                llm_answer=0
            score=int(isclose(float(gt_answer), float(llm_answer), rel_tol=1e-2, abs_tol=1e-3))
            total_calculation_score+=score
            total_calculation_count+=1
        elif type=="Choice":
            gt_answer = set(answer_pair_data["gt_answer"])


            llm_answer=set(list(collapse(answer_pair_data["llm_answer"])))

            score=int(gt_answer==llm_answer)
            total_choice_score+=score
            total_choice_count+=1

            if answer_pair_data["original_type"]=="ShortAnswer":
                total_short_answer_score+=score
                total_short_answer_count+=1
            elif answer_pair_data["original_type"]=="Choice":
                total_original_choice_score+=score
                total_original_choice_count+=1
        elif type=="True/False":
            gt_answer = answer_pair_data["gt_answer"]

            llm_answer = list(collapse(answer_pair_data["llm_answer"]))[0]
            score=int(gt_answer==llm_answer)
            total_true_false_score+=score
            total_true_false_count+=1
        else:
            print("Invalid question type:", type)
            continue




        if "electrochemistry" not in answer_pair_data["domain"]:
            if type=="Choice":
                total_general_choice_score+=score
                total_general_choice_count+=1
            elif type=="Calculation":
                total_general_calculation_score+=score
                total_general_calculation_count+=1
        else:
            total_electrochemistry_score += score
            total_electrochemistry_count += 1
            if type=="Choice":
                total_electrochemistry_choice_count+=1
                total_electrochemistry_choice_score+=score

            elif type=="Calculation":
                total_electrochemistry_calculation_count+=1
                total_electrochemistry_calculation_score+=score

        total_score += score
        total_answered_count += 1
        if total_answered_count%3==0:
            continue
        results.append({
            "question_key":question_key,
            "gt": gt_answer,
            "llm": llm_answer,
            "score": score,
            "type": type,
        })

    average_general_choice_score=total_general_choice_score / total_general_choice_count if total_general_choice_count else 0
    average_general_calculation_score= total_general_calculation_score / total_general_calculation_count if total_general_calculation_count else 0
    average_electrochemistry_choice_score= total_electrochemistry_choice_score / total_electrochemistry_choice_count if total_electrochemistry_choice_count else 0
    average_electrochemistry_calculation_score= total_electrochemistry_calculation_score / total_electrochemistry_calculation_count if total_electrochemistry_calculation_count else 0

    summary = {
        "total_answered_questions": total_answered_count,
        "average_score": total_score / total_answered_count if total_answered_count else 0,
        "total_non_answered_count":total_non_answered_count,
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
        "average_general_calculation_score":  average_general_calculation_score,
        "total_electrochemistry_choice_questions": total_electrochemistry_choice_count,
        "average_electrochemistry_choice_score": average_electrochemistry_choice_score,
        "total_electrochemistry_calculation_questions": total_electrochemistry_calculation_count,
        "average_electrochemistry_calculation_score": average_electrochemistry_calculation_score,
        "weighted_score":average_general_choice_score*1+average_general_calculation_score*2+
                         average_electrochemistry_choice_score*2+average_electrochemistry_calculation_score*3
    }

    output = summary
    print(f"MODEL_NAME:{MODEL_NAME}")
    print(json.dumps( output, indent=2, ensure_ascii=False))
    print(f"✅ 评测完成，总答题数 {total_answered_count}，平均得分 {summary['average_score']:.2f}，未答题数量 {total_non_answered_count}")
    return output



if __name__ == "__main__":
    PROBLEM_FILE= r"/home/chemind/allcode_chemind_server/SFTdata/习题问答对.json"
    NUM_WORKERS=5

    #MODEL_NAME="deepseek-reasoner"
    #MODEL_NAME="qwen3-235b-a22b-instruct-2507"
    #MODEL_NAME="qwen2.5-14b-instruct"
    #MODEL_NAME = "qwen3-14b"
    #MODEL_NAME="qwen3-235b-a22b-instruct-2507_no_reason"

    all_dict={}
    for MODEL_NAME in [
        # "deepseek-reasoner",
        # "qwen3-235b-a22b-instruct-2507",
        # "qwen3-235b-a22b-instruct-2507_no_reason",
        # "qwen2.5-14b-instruct",
        # "qwen3-14b",
        # 在这里填入你的 ckpt 路径，例如:
        # r"/home/chemind/allcode_chemind_server/SFToutput/checkpoint-100",
        "qwen3-8b",
    ]:
        # [新增] 判断是否为本地路径
        is_local_path = os.path.isdir(MODEL_NAME) or "/" in MODEL_NAME or "\\" in MODEL_NAME
        
        # [新增] 如果是本地模型，强制使用 output 目录名为路径的最后一部分 (防止路径斜杠导致报错)
        if is_local_path:
            model_dir_name = os.path.basename(os.path.normpath(MODEL_NAME))
            LLM_ANSWER_DIR = rf"/home/chemind/allcode_chemind_server/testoutput/{model_dir_name}"
        else:
            LLM_ANSWER_DIR = rf"/home/chemind/allcode_chemind_server/testoutput/{MODEL_NAME}"
            
        if os.path.exists(LLM_ANSWER_DIR) == False:
            os.mkdir(LLM_ANSWER_DIR)

        # [新增] 动态调整线程数：本地模型强制单线程，API模型保持原设置
        current_num_workers = 1 if is_local_path else 5
        # 临时修改全局变量 NUM_WORKERS 供 create_LLM_answer_process_main 读取
        NUM_WORKERS = current_num_workers

        # [新增] 加载/卸载逻辑
        if is_local_path:
            init_local_model(MODEL_NAME)
        
        try:
            create_LLM_answer_process_main()
        finally:
            # 确保无论跑完与否都释放显存
            if is_local_path:
                clear_local_model()

        get_answer_pair_dict()
        summary_dict=get_evluation_score()
        
        # 使用路径的最后一段作为 key 存入 csv，避免路径太长
        key_name = os.path.basename(os.path.normpath(MODEL_NAME)) if is_local_path else MODEL_NAME
        all_dict[key_name]=summary_dict

    import pandas as pd
    # 转换成 DataFrame
    df = pd.DataFrame.from_dict(all_dict, orient="index")

    # 保存成 CSV
    df.to_csv("model_evaluation_results.csv", encoding="utf-8-sig")

    exit()
