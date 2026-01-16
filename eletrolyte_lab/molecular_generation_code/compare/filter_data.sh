#!/bin/bash
#SBATCH -J py_gyc_filter
#SBATCH --partition gpu
#SBATCH --gpus t4:1
#SBATCH -N 1
#SBATCH -n 20
#SBATCH -o /home/gaoyuchen/Molecular_generation/compare/log/stdout.%j 
#SBATCH -e /home/gaoyuchen/Molecular_generation/compare/log/stderr.%j

module load conda
conda activate molecular


# ==== 启动任务 ====
python "/home/gaoyuchen/Molecular_generation/compare/filter_smiles.py"