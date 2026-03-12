import argparse
import base64
import json
import multiprocessing as mp
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from threading import Lock, Thread
from typing import Dict, List, Union, Optional

import pandas as pd
import yaml
import torch
from loguru import logger
from openai import OpenAI
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

"""
希望这个代码是可以对模型的思维链进行评分的
缺少：prompt_en_cot.txt
输入数据 (--input) 必须包含以下列：
uuid: 唯一标识符（用于去重和合并）。
question_en: 英文问题文本。
options_en: 选项字典（如 {'A': '...', 'B': '...'}）。
explanation_en: 标准答案的解析（用于给裁判做参考）。
model_answer_en (可选): 如果跳过推理直接评测，必须有此列。
"""
dir = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(dir, 'config.yaml')
if not os.path.exists(config_path):
    default_config = {'model_list': [{'model': 'your-evaluator-model-name', 'base_url': 'your-api-base-url', 'api_key': 'your-api-key'}]}
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f)
    logger.warning(f"Config file not found. A default config.yaml has been created. Please edit it.")
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

clients = {}
if 'model_list' in config and config['model_list']:
    for model_config in config['model_list']:
        model, base_url, api_key = model_config.get('model'), model_config.get('base_url'), model_config.get('api_key')
        if model and base_url and api_key:
            clients[model] = OpenAI(base_url=base_url, api_key=api_key)
else:
    logger.error("Model configuration is missing or empty in config.yaml.")
    # exit(1) # Allow running without API config if only doing inference, checking later.

languages = ['en'] 
prompts = {}
for l in languages:
    # 确保目录下有 prompt_en_cot.txt
    prompt_file_path = os.path.join(dir, f'prompt_{l}_cot.txt')
    if os.path.exists(prompt_file_path):
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompts[l] = f.read()
    else:
    logger.error(f"Prompt file not found at: {prompt_file_path}. Cannot proceed.")
    exit(1)
write_lock = Lock()

"""
Functions - Inference Phase (New Added)
"""

def load_local_model(ckpt_path: str):
    """
    Load the Qwen model and tokenizer from the checkpoint path.
    """
    logger.info(f"Loading model from checkpoint: {ckpt_path}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(ckpt_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            ckpt_path,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        )
        return model, tokenizer
    except Exception as e:
        logger.error(f"Failed to load model from {ckpt_path}: {e}")
        exit(1)

def run_inference(input_path: str, output_path: str, ckpt_path: str, language: str):
    """
    Run inference using the local checkpoint to generate answers.
    """
    # 1. Load Data
    if input_path.endswith('.parquet'):
        df = pd.read_parquet(input_path)
    elif input_path.endswith('.jsonl'):
        df = pd.read_json(input_path, lines=True)
    else:
        raise ValueError("Unsupported input format")
    
    # Check if output already exists to resume
    start_idx = 0
    existing_data = []
    if os.path.exists(output_path):
        logger.info(f"Inference output file exists: {output_path}. Checking for resumption...")
        existing_df = pd.read_json(output_path, lines=True)
        existing_uuids = set(existing_df['uuid'].tolist())
        # Filter out already processed rows
        df = df[~df['uuid'].isin(existing_uuids)]
        logger.info(f"Resuming inference. Remaining items: {len(df)}")
    
    if df.empty:
        logger.info("All items already have answers. Skipping inference.")
        return

    # 2. Load Model
    model, tokenizer = load_local_model(ckpt_path)
    model.eval()

    # 3. Inference Loop
    results = []
    logger.info("Starting inference...")
    
    # Answer column name convention from original script
    answer_col = f'llm_output' 

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Inference"):
        question = row.get(f'question_{language}', '')
        options_dict = row.get(f'options_{language}', {})
        
        # Format input (Qwen Style)
        # Assuming typical Q&A format. Adjust prompt style if needed for specific Qwen tuning.
        options_str = ""
        if isinstance(options_dict, dict):
            for k, v in options_dict.items():
                if v: options_str += f"{k}: {v}\n"
        
        content = f"Question: {question}\nOptions:\n{options_str}\nPlease answer the question and explain your reasoning."
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": content}
        ]
        
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            generated_ids = model.generate(
                model_inputs.input_ids,
                max_new_tokens=2048, # Adjust based on needs
                temperature=0.7,     # Adjust for evaluation stability
                top_p=0.9
            )
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # Save result format
        result_item = {
            "uuid": row['uuid'],
            answer_col: response
        }
        
        # Write immediately to file to allow resume
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(result_item, ensure_ascii=False) + '\n')
            
    logger.info(f"Inference completed. Results saved to {output_path}")
    
    # Cleanup to free GPU memory for the next phase (if evaluator runs on same GPU, though API usually doesn't)
    del model
    del tokenizer
    torch.cuda.empty_cache()


"""
Functions - Evaluation Phase (Original Logic)
"""

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Qwen model checkpoint.")
    parser.add_argument('--input', type=str, required=True, help='Path to the QUESTIONS file.')
    
    # CHANGED: Optional, because we might generate it
    parser.add_argument('--answers-input', type=str, default=None, help="Path to existing ANSWERS file. If not provided, --checkpoint-path is required.")
    
    # NEW: Checkpoint path argument
    parser.add_argument('--checkpoint-path', type=str, default=None, help="Path to local Qwen checkpoint. If provided, inference will run first.")
    
    parser.add_argument('--output', type=str, required=True, help='Path to the evaluation output file.')
    parser.add_argument('--model', type=str, required=True, help='Name of the EVALUATOR (Judge) model.')
    parser.add_argument('--reasoning-effort', type=str, default=None, choices=['low', 'medium', 'high'])
    parser.add_argument('--temperature', type=float, default=1.0)
    parser.add_argument('--language', type=str, required=True, choices=languages)
    parser.add_argument('--pass-k', type=int, default=1)
    parser.add_argument('--max-retries', type=int, default=5)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--n-procs', type=int, default=1)
    parser.add_argument('--n-threads', type=int, default=1)
    
    # Force user to provide either answers or a checkpoint
    args = parser.parse_args()
    if not args.answers_input and not args.checkpoint_path:
        parser.error("You must provide either --answers-input (to evaluate existing answers) or --checkpoint-path (to generate new answers).")
    return args

def load_and_merge_data(questions_path: str, answers_path: str, language: str) -> pd.DataFrame:
    logger.info(f"Loading questions from {questions_path}")
    if questions_path.endswith('.parquet'):
        questions_df = pd.read_parquet(questions_path)
    elif questions_path.endswith('.jsonl'):
        questions_df = pd.read_json(questions_path, lines=True)
    else:
        raise ValueError("Unsupported file format for questions.")
    
    logger.info(f"Loading answers from {answers_path}")
    if not os.path.exists(answers_path):
        logger.error(f"Answers file not found: {answers_path}")
        exit(1)
    answers_df = pd.read_json(answers_path, lines=True)
    
    # Adapt to the column name usually generated
    possible_cols = ['llm_output', f'model_answer_{language}']
    target_col = None
    for col in possible_cols:
        if col in answers_df.columns:
            target_col = col
            break
            
    if not target_col:
        logger.error(f"Answer column not found in {answers_path}. Expected 'llm_output' or 'model_answer_{language}'")
        exit(1)
    
    answer_col_name = f'model_answer_{language}'
    answers_df_subset = answers_df[['uuid', target_col]].rename(columns={target_col: answer_col_name})
    
    answers_df_unique = answers_df_subset.drop_duplicates(subset='uuid', keep='first')
    merged_df = pd.merge(questions_df, answers_df_unique, on='uuid', how='left')
    merged_df[answer_col_name] = merged_df[answer_col_name].fillna('')
    
    return merged_df

def check_incomplete(input_df: pd.DataFrame, output_df: pd.DataFrame, pass_k: int) -> pd.DataFrame:
    if output_df.empty:
        incomplete_df = input_df.loc[input_df.index.repeat(pass_k)]
    else:
        completed_counts = output_df[output_df['status'] == True].groupby('uuid').size()
        remaining_counts = input_df['uuid'].map(lambda x: pass_k - completed_counts.get(x, 0))
        mask = remaining_counts > 0
        incomplete_df = input_df[mask].loc[input_df[mask].index.repeat(remaining_counts[mask])]
    logger.info(f"Found {len(incomplete_df)} incomplete evaluations.")
    return incomplete_df.reset_index(drop=True)

def generate_message(input_line: pd.Series, language: str) -> List[Dict]:
    prompt = prompts[language]
    question = input_line.get(f'question_{language}', '')
    options_dict = input_line.get(f'options_{language}', {})
    ground_truth = input_line.get(f'explanation_{language}', '')
    model_answer = input_line.get(f'model_answer_{language}', '') 
    
    options = ''
    if isinstance(options_dict, dict):
        for key in sorted(options_dict.keys()):
            if options_dict.get(key) is not None:
                options += f"{key}: {options_dict[key]}\n"
                
    prompt = prompt.replace('{question}', str(question))
    prompt = prompt.replace('{options}', options)
    prompt = prompt.replace('{ground_truth_analysis}', str(ground_truth))
    prompt = prompt.replace('{model_answer}', str(model_answer))
    
    return [{'role': 'user', 'content': prompt}]

def parse_evaluation_response(response: str) -> Dict:
    pattern = r'```json\s*([\s\S]*?)\s*```'
    match = re.search(pattern, response)
    if match:
        json_str = match.group(1)
    else:
        match = re.search(r'\{[\s\S]*\}', response)
        json_str = match.group(0) if match else None
        
    if not json_str:
        raise ValueError("No valid JSON structure found.")
    
    try:
        parsed = json.loads(json_str)
        if 'checkpoint_details' not in parsed or not isinstance(parsed['checkpoint_details'], list):
            # Try to be lenient or raise error based on strictness
            pass 
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON: {e}")

def save_result(output_path: str, result: dict):
    with write_lock:
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

def handle_request(input_line: pd.Series, model: str, reasoning_effort: Optional[str], temperature: float, language: str, timeout: int):
    client = clients[model]
    messages = generate_message(input_line, language)
    parameters = {
        'model': model, 'messages': messages, 'temperature': temperature, 'timeout': timeout,
        'stream': True, 'max_tokens': 4096, 'stream_options': {"include_usage": True},
    }
    if reasoning_effort: parameters['reasoning_effort'] = reasoning_effort
    
    response = client.chat.completions.create(**parameters)
    content, finish_reason = '', None
    prompt_usage, completion_usage = 0, 0
    
    for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta and delta.content: content += delta.content
            if chunk.choices[0].finish_reason: finish_reason = chunk.choices[0].finish_reason
        if hasattr(chunk, 'usage') and chunk.usage:
            prompt_usage, completion_usage = chunk.usage.prompt_tokens, chunk.usage.completion_tokens
            
    return content, finish_reason, prompt_usage, completion_usage

def single_task(input_line: pd.Series, model: str, reasoning_effort: Optional[str], temperature: float, language: str, max_retries: int, timeout: int) -> Dict:
    retries_count, time_wait = 0, 5
    while retries_count < max_retries:
        try:
            content, finish_reason, prompt_usage, completion_usage = handle_request(
                input_line, model, reasoning_effort, temperature, language, timeout)
            
            parsed = parse_evaluation_response(content)
            details = parsed.get('checkpoint_details', [])
            matched_checkpoints = sum(1 for item in details if isinstance(item, dict) and item.get('is_matched') is True)

            return {
                'uuid': input_line['uuid'],
                'matched_checkpoints': matched_checkpoints,
                'total_checkpoints': len(details),
                'evaluation_details': details,
                'llm_output': content,
                'finish_reason': finish_reason,
                'prompt_usage': prompt_usage,
                'completion_usage': completion_usage,
                'model': model,
                'status': True,
            }
        except Exception as e:
            retries_count += 1
            if retries_count >= max_retries:
                return {
                    'uuid': input_line['uuid'], 'model': model, 'status': False, 'error': str(e), 'llm_output': content if 'content' in locals() else ''
                }
            time.sleep(time_wait)

def worker(task_queue, args, process_id, thread_id, progress_counter, progress_lock):
    output_path, model, reasoning_effort, temp, lang, max_retries, timeout = args
    while True:
        try:
            task_data = task_queue.get(timeout=1)
            if task_data is None: break
            result = single_task(pd.Series(task_data), model, reasoning_effort, temp, lang, max_retries, timeout)
            save_result(output_path, result)
            with progress_lock: progress_counter.value += 1
        except Exception:
            continue

def process_worker(task_queue, args, n_threads, process_id, progress_counter, progress_lock):
    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures = [executor.submit(worker, task_queue, args, process_id, i, progress_counter, progress_lock) for i in range(n_threads)]
        for future in futures: future.result()

def main():
    args = parse_args()
    
    # --- STEP 1: INFERENCE (Optional but prioritized) ---
    answers_file = args.answers_input
    
    if args.checkpoint_path:
        # Determine output file name for generated answers
        ckpt_name = os.path.basename(os.path.normpath(args.checkpoint_path))
        generated_answers_path = os.path.join(os.path.dirname(args.output), f"answers_{ckpt_name}.jsonl")
        
        logger.info(f"Checkpoint provided: {args.checkpoint_path}")
        logger.info(f"Will generate answers to: {generated_answers_path}")
        
        # Run inference logic (This runs on GPU, sequentially or single process)
        # Note: We run this BEFORE creating the multiprocessing pool for evaluation to avoid CUDA/Fork issues
        run_inference(args.input, generated_answers_path, args.checkpoint_path, args.language)
        
        # Use the generated file as the answers input for the next step
        answers_file = generated_answers_path

    # --- STEP 2: EVALUATION (LLM-as-a-Judge) ---
    logger.info(f"Starting Evaluation using answers from: {answers_file}")
    
    # Use Manager to handle queue in multiprocessing
    manager = mp.Manager()
    task_queue = manager.Queue()
    
    merged_df = load_and_merge_data(args.input, answers_file, args.language)
    output_df = pd.read_json(args.output, lines=True) if os.path.exists(args.output) else pd.DataFrame()
    incomplete_df = check_incomplete(merged_df, output_df, args.pass_k)

    if incomplete_df.empty:
        logger.info("No incomplete evaluation tasks found. Exiting.")
        return
    
    progress_counter = manager.Value('i', 0)
    progress_lock = manager.Lock()
    
    with tqdm(total=len(incomplete_df), desc="Evaluating") as pbar:
        def update_progress():
            last_val = 0
            while progress_counter.value < len(incomplete_df):
                if progress_counter.value > last_val:
                    pbar.update(progress_counter.value - last_val)
                    last_val = progress_counter.value
                time.sleep(0.1)
            pbar.update(len(incomplete_df) - last_val)

        progress_thread = Thread(target=update_progress)
        progress_thread.start()

        for _, row in incomplete_df.iterrows(): task_queue.put(row.to_dict())
        for _ in range(args.n_procs * args.n_threads): task_queue.put(None)
        
        worker_args = (args.output, args.model, args.reasoning_effort, args.temperature, args.language,
                       args.max_retries, args.timeout)
        
        if args.n_procs == 1:
            process_worker(task_queue, worker_args, args.n_threads, 0, progress_counter, progress_lock)
        else:
            with ProcessPoolExecutor(max_workers=args.n_procs) as executor:
                futures = [executor.submit(process_worker, task_queue, worker_args, args.n_threads, i, progress_counter, progress_lock) for i in range(args.n_procs)]
                for future in futures: future.result()

        progress_thread.join()
        
    logger.info("Evaluation pipeline completed successfully.")

if __name__ == "__main__":
    # Ensure standard forking behavior to avoid mixed mp methods
    mp.set_start_method('spawn', force=True)
    main()