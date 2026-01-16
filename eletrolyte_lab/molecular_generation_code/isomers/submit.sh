#!/bin/bash
#SBATCH --job-name=isomer_calcs
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --output=output_%j.log
#SBATCH --error=error_%j.log
#SBATCH --time=24:00:00

module load conda
conda activate molecular

csv_file="DFD-NPSSi-20230816.csv"

if [ ! -f "$csv_file" ]; then
    echo "CSV文件不存在，请检查文件路径"
    exit 1
fi

while IFS=, read -r index ids smiles; do
    dir_name="${index}_${ids}"
    mkdir -p "$dir_name"

    srun python Isomers_2.py "$index" "$ids" "$smiles" "5" &
done < "$csv_file"

wait