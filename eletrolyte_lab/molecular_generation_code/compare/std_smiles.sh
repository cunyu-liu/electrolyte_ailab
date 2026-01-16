#!/bin/bash
#SBATCH -J py_gyc_std
#SBATCH --partition gpu
#SBATCH --gpus t4:1
#SBATCH -N 1
#SBATCH -n 5
#SBATCH -o /home/gaoyuchen/Molecular_generation/compare/log/stdout.%j 
#SBATCH -e /home/gaoyuchen/Molecular_generation/compare/log/stderr.%j


# 标准化一个文件
module load conda
conda activate uni_core
python /home/gaoyuchen/Molecular_generation/compare/3_standard_smiles.py