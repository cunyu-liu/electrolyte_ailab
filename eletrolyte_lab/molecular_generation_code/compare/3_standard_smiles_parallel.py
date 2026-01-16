import multiprocessing
from rdkit import Chem
import argparse
import gc
import os

# 用于线程安全地写入文件的锁
lock = multiprocessing.Lock()

def standardize_smiles_batch(smiles_list):
    """
    批量处理 SMILES 标准化
    """
    results = []
    for smiles in smiles_list:
        try:
            mol = Chem.MolFromSmiles(smiles.strip())
            if mol:
                standardized = Chem.MolToSmiles(mol, canonical=True)
                results.append(standardized)
            else:
                results.append(None)
        except Exception as e:
            results.append(None)
            print(f"错误: {e}，SMILES: {smiles}")
    return results

def worker(smiles_batch, output_file):
    """
    处理一批 SMILES 数据，并立即写入结果到输出文件
    """
    print(f"Worker 正在处理 {len(smiles_batch)} 条 SMILES 数据")
    results = standardize_smiles_batch(smiles_batch)

    # 使用锁保证线程安全地写入文件
    with lock:
        with open(output_file, 'a') as out_f:
            for smi in results:
                if smi:
                    out_f.write(smi + '\n')

    print(f"Worker 完成处理 {len(smiles_batch)} 条 SMILES 数据，已写入文件", flush=True)

    # 处理完后显式删除不需要的变量并调用垃圾回收
    del smiles_batch  # 删除当前批次的数据
    del results  # 删除标准化后的结果数据
    gc.collect()  # 显式调用垃圾回收

def process_in_parallel(input_file, output_file, num_processes, batch_size):
    """
    使用多进程并行处理 SMILES 标准化
    """
    print(f"开启 {num_processes} 个进程进行并行处理")
    pool = multiprocessing.Pool(processes=num_processes)

    total = 0
    valid = 0
    invalid = 0

    tasks = []
    batch = []

    with open(input_file, 'r') as in_f:
        print(f"开始读取输入文件 {input_file}")
        for line in in_f:
            line = line.strip()
            if line:
                batch.append(line)
                if len(batch) == batch_size:
                    # 直接传递 batch，避免复制
                    tasks.append(pool.apply_async(worker, (batch, output_file)))
                    batch.clear()  # 清空当前批次，准备下一批数据

        # 提交最后一个 batch（如果有剩余数据）
        if batch:
            print(f"提交最后一个任务：处理剩余的 {len(batch)} 条 SMILES 数据",flush=True)
            tasks.append(pool.apply_async(worker, (batch, output_file)))

    # 等待所有任务完成
    print(f"等待所有任务完成...")
    pool.close()
    pool.join()
    print(f"处理完毕")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', required=True)
    parser.add_argument('--output_file', required=True)
    parser.add_argument('--num_processes', type=int, default=4)
    parser.add_argument('--batch_size', type=int, default=1000)
    args = parser.parse_args()

    process_in_parallel(args.input_file, args.output_file, args.num_processes, args.batch_size)