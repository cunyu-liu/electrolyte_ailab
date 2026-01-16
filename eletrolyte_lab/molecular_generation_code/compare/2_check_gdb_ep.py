import pandas as pd
import os
def build_smiles_index(smi_file):
    """生成器函数逐块读取大文件"""
    chunk_size = 1_000_000  # 每次读取1M行
    current_chunk = set()
    
    with open(smi_file, 'r') as f:
        for i, line in enumerate(f):
            current_chunk.add(line.strip())
            # 当块达到指定大小时返回
            if (i+1) % chunk_size == 0:
                yield current_chunk
                current_chunk = set()  # 重置块
        # 返回最后一个不满的块
        if current_chunk:
            yield current_chunk

def main():
    # 读取目标CSV文件（约占用500MB内存）
    print("正在加载目标CSV文件...")
    target_df = pd.read_csv(r"D:\测试代码\std1.CSV")
    total_rows = len(target_df)
    print(f"成功加载{total_rows:,}行数据")
    
    # 初始化匹配状态数组（约占用1MB/百万行）
    matched = pd.Series(False, index=target_df.index)
    
    # 分块处理标准库文件
    processed_chunks = 0
    for std_chunk in build_smiles_index(r"D:\测试代码\cyc1.CSV"):
        # 批量匹配当前块
        matched |= target_df['SMILES'].isin(std_chunk)
        
        # 进度报告
        processed_chunks += 1
        found = matched.sum()
        print(f"已处理 {processed_chunks}M 标准条目 | 已匹配 {found}/{total_rows} ({found/total_rows:.1%})")
        
        # 及时释放内存
        del std_chunk
    
    # 生成最终结果
    print("\n正在生成未匹配记录...")
    unmatched_df = target_df[~matched]
    
    # 保存结果
    output_file = r'D:/测试代码/unmatched_records.csv'
    unmatched_df.to_csv(output_file, index=False)
    print(f"完成！共找到 {len(unmatched_df):,} 条未匹配记录")
    print(f"结果已保存至 {output_file}")

if __name__ == '__main__':
    main()