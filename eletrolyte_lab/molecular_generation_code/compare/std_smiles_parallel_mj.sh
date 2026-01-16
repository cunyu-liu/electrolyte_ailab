#!/bin/bash
#SBATCH -J main_std
#SBATCH -N 1
#SBATCH -n 4
#SBATCH -o /home/gaoyuchen/Molecular_generation/compare/log/stdout_process.%j 
#SBATCH -e /home/gaoyuchen/Molecular_generation/compare/log/stderr_process.%j


# 本脚本用于标准化smiles文件，并行提交多个作业

find_smi_files() {
    local directory=$1
    # 遍历目录中的所有文件
    for file in "$directory"/*; do
        if [ -d "$file" ]; then
            find_smi_files "$file"
        elif [[ "$file" == *.smi ]]; then
            # 如果是.smi文件，则执行sh脚本
            input_file="$file"
            output_file="/home/gaoyuchen/Molecular_generation/compare/res_0403/$(basename "$input_file" .smi)_std.smi"

            
            # 检查当前的作业数量，直到作业数小于10
            while [ $(squeue -u gaoyuchen | wc -l) -gt 10 ]; do
                echo "当前作业数已达上限，等待中..."
                sleep 300  # 等待5min后再次检查
            done
            
            echo "提交作业：$input_file 到 $output_file"
            sbatch "/home/gaoyuchen/Molecular_generation/compare/std_smiles_parallel_1.sh" "$input_file" "$output_file"
        fi
    done
}

# 指定起始目录，替换为实际路径
root_directory0="/home/gaoyuchen/Molecular_generation/test_0325/1_CHO_20250327"
root_directory1=/home/gaoyuchen/Molecular_generation/test_0325/2_CH_20250327
root_directory2=/home/gaoyuchen/Molecular_generation/test_0325/3_CHF_20250327
root_directory3=/home/gaoyuchen/Molecular_generation/test_0325/4_CHOF_20250327
root_directory4=/home/gaoyuchen/Molecular_generation/test_0325/5_CHS_20250327

# 调用函数开始查找
find_smi_files "$root_directory0"
echo "1_CHO 已经处理完"

find_smi_files "$root_directory1"
echo "2_CH 已经处理完"

find_smi_files "$root_directory2"
echo "3_CHF 已经处理完"

find_smi_files "$root_directory3"
echo "4_CHOF 已经处理完"

find_smi_files "$root_directory4"
echo "5_CHS 已经处理完"