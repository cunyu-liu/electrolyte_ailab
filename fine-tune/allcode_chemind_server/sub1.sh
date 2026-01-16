#!/bin/bash
#SBATCH --job-name=qwen3-8b-dora
#SBATCH --partition=gpu
#SBATCH --account=local
#SBATCH --nodelist=gpu1
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --time=7-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

source ~/.bashrc
conda activate qwen_finetune

# export TOKENIZERS_PARALLELISM=false
# export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# export NCCL_DEBUG=warn
# export NCCL_IB_DISABLE=1
# export NCCL_P2P_LEVEL=NVL

nvidia-smi

torchrun llamafactory-cli train /home/ChemMind/LLaMA-Factory/examples/train_lora/lora_sft.yaml
