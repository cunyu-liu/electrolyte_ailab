import os
import re
import glob
import pandas as pd
from rdkit import Chem

def count_atoms(smiles):
    """计算SMILES字符串表示的分子中的原子数量
    
    参数:
        smiles (str): 分子的SMILES表示
        
    返回:
        int: 分子中的原子数量，如果SMILES无效则返回0
    """
    # 从SMILES字符串创建分子对象
    mol = Chem.MolFromSmiles(smiles)
    # 检查分子是否有效
    if mol is None:
        return 0
    # 返回分子中的原子数量
    return mol.GetNumAtoms()

def main():
    # 包含所有结果文件夹的基础目录
    base_dir = r"D:\测试代码\测试数据.CSV"
    
    # 匹配结果目录的模式（如"1_ep-980812"到"26_ep-980837"）
    pattern = "[0-9]*_ep-*"
    
    # 创建字典存储结果，键为原子数量，值为分子数量
    results = {}
    
    # 查找所有符合模式的结果目录
    result_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and re.match(pattern, d)]
    
    print(f"找到 {len(result_dirs)} 个结果目录")
    
    # 处理每个目录
    for dir_name in sorted(result_dirs):
        dir_path = os.path.join(base_dir, dir_name)
        
        # 查找所有结果子目录（如1_0_results, 1_1_results等）
        result_subdirs = glob.glob(os.path.join(dir_path, "1_*_results"))
        print(f"在 {dir_name} 中找到 {len(result_subdirs)} 个结果子目录，\n result_subdirs: {result_subdirs}")
        
        for subdir in result_subdirs:
            # 从目录名称中提取循环次数
            cycle_match = re.search(r'1_(\d+)_results', subdir)
            print(f"cycle_match: {cycle_match}")
            print(f"cycle: {cycle_match.group(1)}")
            if not cycle_match:
                continue
            
            # 将循环次数转换为整数
            cycle = int(cycle_match.group(1))
            
            # 查找该子目录中的所有SMILES文件
            smi_files = glob.glob(os.path.join(subdir, "*.smi"))
            
            for smi_file in smi_files:
                try:
                    # 读取文件中的SMILES字符串
                    with open(smi_file, 'r') as f:
                        # 去除空行并去除每行的首尾空白字符
                        smiles_list = [line.strip() for line in f if line.strip()]
                    
                    # 计算每个分子的原子数量
                    for smiles in smiles_list:
                        atom_count = count_atoms(smiles)
                        
                        # 如果这个原子数量还没有在结果字典中，初始化计数器
                        if atom_count not in results:
                            results[atom_count] = 0
                        
                        # 增加计数器
                        results[atom_count] += 1
                        
                except Exception as e:
                    # 处理文件读取或分子解析过程中可能出现的错误
                    print(f"处理文件 {smi_file} 时出错: {e}")
    
    # 按原子数量排序结果
    sorted_results = {k: results[k] for k in sorted(results.keys())}
    
    # 创建DataFrame以便更好地显示结果
    df = pd.DataFrame({
        'Atom Count': sorted_results.keys(),
        'Number of Molecules': sorted_results.values()
    })
    
    # 将结果保存到CSV文件
    output_file = os.path.join(base_dir, "atom_count_summary.csv")
    df.to_csv(output_file, index=False)
    
    # 输出结果摘要
    print(f"\nResults saved to {output_file}")
    print("\nSummary:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
