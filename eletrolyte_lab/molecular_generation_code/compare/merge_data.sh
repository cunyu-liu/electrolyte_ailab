#!/bin/bash
#SBATCH -J py_gyc_merge
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -o /home/gaoyuchen/Molecular_generation/compare/log/stdout.%j 
#SBATCH -e /home/gaoyuchen/Molecular_generation/compare/log/stderr.%j

module load conda
conda activate molecular


# 合并smi为一个文件
python "/home/gaoyuchen/Molecular_generation/compare/merge_all_data.py"