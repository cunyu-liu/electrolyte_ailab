#!/bin/bash
#SBATCH -J py_gyc
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -o stdout.%j
#SBATCH -e stderr.%j

source $(conda info --base)/etc/profile.d/conda.sh # mac 环境
# module load conda
conda activate molecular

csv_file="DFD-NPSSi-20230816.csv"

python_script="Isomers_2.py"

if [ ! -f "$csv_file" ]; then
    echo "CSV文件不存在，请检查文件路径"
    exit 1
fi

while IFS=, read -r index ids smiles; do
    dir_name="${index}_${ids}"
    mkdir -p "$dir_name"

    python "$python_script" "$index" "$ids" "$smiles" "5"
done < "$csv_file"
