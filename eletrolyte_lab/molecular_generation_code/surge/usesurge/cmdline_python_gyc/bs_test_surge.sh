#!/bin/bash
#SBATCH -J py_gyc
#SBATCH -N 1
#SBATCH -n 32
#SBATCH -o stdout.%j
#SBATCH -e stderr.%j

module load conda

dir="1_CHO_20230611"
num=4

if [ ! -d "$dir" ]; then
  mkdir -p "$dir"
fi

subdir="${dir}/${num}_CHO"
if [ ! -d "$subdir" ]; then
  mkdir -p "$subdir"
fi

python test_GDB.py --n ${num}