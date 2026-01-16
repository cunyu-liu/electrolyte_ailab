#!/bin/bash
#SBATCH -J py_gyc
#SBATCH --partition gpu
#SBATCH --gpus t4:1
#SBATCH -N 1
#SBATCH -n 5
#SBATCH -o stderr_out/stdout.%j
#SBATCH -e stderr_out/stderr.%j

module load conda
conda activate uni_core
python 3_standard_smiles.py
