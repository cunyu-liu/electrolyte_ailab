#!/bin/bash
#SBATCH -J qwen1
#SBATCH -p standard
#SBATCH -N 1
#SBATCH -n 16


python -u t.py
