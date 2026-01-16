#!/bin/bash
#SBATCH -J formula_test
#SBATCH -N 1
#SBATCH -n 10
#SBATCH -o /home/gaoyuchen/Molecular_generation/compare/log/stdout.%j 
#SBATCH -e /home/gaoyuchen/Molecular_generation/compare/log/stderr.%j

module load conda
conda activate molecular


# ==== 启动任务 ====
python "/home/gaoyuchen/Molecular_generation/compare/get_formula.py" 