# ChemMind - Chemistry LLM Fine-tuning & RAG System

## Project Overview

ChemMind is a domain-specific AI system for chemistry research, focusing on:
1. **LLM Fine-tuning**: Supervised fine-tuning (SFT) of Qwen models for chemistry question answering
2. **RAG (Retrieval-Augmented Generation)**: Multi-agent RAG system for electrolyte research with deep research capabilities
3. **Evaluation**: Comprehensive evaluation framework for chemistry benchmarks (SUPERChem)

The project combines modern LLM training techniques (LoRA, DoRA) with vector search (Milvus + Elasticsearch) to provide accurate chemistry knowledge retrieval and question answering.

## Technology Stack

### Core Frameworks
- **LLaMA-Factory** (v0.9.4): Primary fine-tuning framework for Qwen models
- **PyTorch** (v2.9.1): Deep learning framework
- **Transformers** (v4.57.1): Hugging Face model library
- **PEFT** (v0.17.1): Parameter-efficient fine-tuning (LoRA/DoRA)

### Model & Training
- **Base Model**: Qwen/Qwen3-8B (primary), Qwen2.5 series supported
- **Fine-tuning Method**: LoRA/DoRA with rank 8-64
- **Training Types**: 
  - SFT (Supervised Fine-Tuning) - `lora_sft.yaml`
  - CPT (Continual Pre-Training) - `lora_pretrain.yaml`
- **Experiment Tracking**: SwanLab (configured in training configs)

### RAG Infrastructure
- **Vector Database**: Milvus (v2.x) for semantic search
- **Text Search**: Elasticsearch for keyword search
- **Embedding Model**: BGE-M3 (1024-dimension embeddings)
- **Reranker**: BGE-Reranker-v2-M3
- **API Framework**: FastAPI + uvicorn

### Environment
- **Python**: 3.11
- **Conda Environment**: `qwen_finetune`
- **GPU**: CUDA 12.x, supports RTX 5090, multi-GPU training with DDP

## Project Structure

```
allcode_chemind_server/
├── agent/                          # RAG Agents and Vector DB
│   ├── agent_rag_v[1-6].py        # Iterative RAG agent versions (v6 is latest multi-agent)
│   ├── test_*.py                  # Agent testing scripts
│   └── vectordb/                  # Vector database utilities
│       ├── gpu_loader_mac_v*.py   # PDF processing & Milvus ingestion scripts
│       ├── cpu_parser.py          # CPU-based PDF parsing
│       ├── bge_download.py        # Embedding model downloader
│       ├── reset_db.py            # Database reset utilities
│       └── paper_text_clean/      # Processed paper text storage
├── SFTdata/                       # Supervised Fine-Tuning Data
│   ├── allsftdata.jsonl           # Main SFT dataset (ShareGPT format)
│   ├── superchem_sft_data*.jsonl  # Chemistry-specific SFT data
│   ├── md_*.jsonl                 # Markdown-based QA datasets
│   ├── SFTsplitdataset.py         # Train/test split utility
│   ├── SFTdataShuffle.py          # Data shuffling
│   └── v1/, v2/                   # Dataset version directories
├── CPTdata/                       # Continual Pre-Training Data
│   ├── alldata.jsonl
│   └── cpt_*.jsonl
├── evaluate/                      # Evaluation Framework
│   ├── answer_v2_gpu.py           # Main GPU evaluation script (batch processing)
│   ├── answer_v1*.py              # Alternative evaluation scripts
│   ├── eval_dataset/              # Evaluation datasets
│   │   ├── v1/, v2/               # Dataset versions
│   │   └── 习题问答对*.jsonl      # Chemistry exercise QA pairs
│   └── SUPERChem_eval-main/       # SUPERChem benchmark suite
│       ├── eval/                  # Evaluation scripts
│       ├── analysis/              # Result analysis tools
│       └── view/                  # Visualization app
├── testoutput/                    # Model evaluation outputs
│   └── *_eval/                    # Per-model evaluation results
├── lora_sft.yaml                  # SFT training configuration
├── lora_pretrain.yaml             # Pre-training configuration
├── merge_config.yaml              # LoRA merge configuration
├── dataset_info.json              # LLaMA-Factory dataset registry
├── my_env.yaml                    # Conda environment specification
├── sub1.sh                        # SLURM submission script (GPU)
├── sub.sh                         # SLURM submission script (CPU)
├── slurm                          # SLURM usage documentation
├── test.py                        # Standalone model evaluation script
└── downloadQwen.py                # Model download script
```

## Build and Training Commands

### Environment Setup
```bash
# Load conda and activate environment
module load conda
conda activate qwen_finetune

# Or create from spec
conda env create -f my_env.yaml
```

### Data Preparation
```bash
# Prepare SFT data in ShareGPT format
# Data should be in SFTdata/allsftdata.jsonl

# Update dataset_info.json to register new datasets
```

### Training

#### LoRA SFT Training
```bash
# Using SLURM (recommended for cluster)
sbatch sub1.sh

# Or run directly
torchrun llamafactory-cli train lora_sft.yaml
```

Key training parameters (from `lora_sft.yaml`):
- Model: Qwen/Qwen3-8B
- LoRA rank: 8
- Target modules: all
- Use DoRA: true
- Epochs: 3
- Learning rate: 1e-4
- Batch size: 1 per device, gradient accumulation: 8
- Max length: 2048 tokens
- Output: `/home/ChemMind/Allcode/output/qwen3-8b-sft`

#### LoRA Merging
```bash
llamafactory-cli export merge_config.yaml
```

#### Continual Pre-training
```bash
llamafactory-cli train lora_pretrain.yaml
```

### Evaluation

#### Batch Evaluation (GPU)
```bash
python evaluate/answer_v2_gpu.py
```

This script:
1. Loads merged model from `mergedoutput/`
2. Processes questions in batches (chunk size: 20)
3. Generates answers with JSON output format
4. Calculates accuracy by question type (Choice/Calculation/TrueFalse)
5. Outputs weighted scores for electrochemistry vs general chemistry

#### Single Model Evaluation
```bash
python test.py
```

Configure paths in the file:
- `MODEL_PATH`: Path to LoRA adapter or merged model
- `BASE_MODEL`: Base model path (if using LoRA)
- `TEST_DATA_PATH`: Path to test questions

### RAG System Deployment

#### Start RAG Server (v6 - Multi-Agent)
```bash
python agent/agent_rag_v6.py
```

Features:
- FastAPI server with async endpoints
- Milvus + Elasticsearch hybrid search
- Deep research engine with recursive exploration
- Multi-agent message bus architecture
- Experiment data management with access control

#### Vector Database Setup
```bash
cd agent/vectordb

# Download embedding models
python bge_download.py

# Process papers and ingest to Milvus
python gpu_loader_mac_v3.py

# Reset database if needed
python reset_milvus.py
```

## Code Style Guidelines

### Python Code Style
- Use **Chinese comments** for business logic explanation
- Use **English** for variable names and function names
- Follow PEP 8 formatting
- Use type hints for function parameters and returns
- Include docstrings for class and function documentation

### Example:
```python
async def deep_research(self, query: str, depth: int = None) -> Tuple[List[ResearchFinding], Dict]:
    """
    执行深度研究，递归探索相关文献
    
    Args:
        query: 研究查询问题
        depth: 探索深度（默认为配置中的 MAX_DEPTH）
    
    Returns:
        Tuple of (findings列表, 元数据字典)
    """
```

### Data Format Standards

#### SFT Data Format (ShareGPT)
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

#### Evaluation Data Format
```json
{
  "filename": "source_doc",
  "question_number": "1",
  "sub_id": "1",
  "question": {
    "question_stem": "context",
    "question": "specific question",
    "options": ["A. ...", "B. ..."]
  },
  "type": "Choice/Calculation/TrueFalse",
  "answer": ["A"],
  "domain": "electrochemistry"
}
```

## Testing Instructions

### Unit Testing
No formal unit test framework is configured. Test files follow the pattern `test_*.py`:
- `agent/test_agent_v456.py` - Test RAG agent versions
- `agent/testrag_v123456.py` - Test RAG retrieval
- `agent/test_multiagent.py` - Test multi-agent communication
- `agent/test_deepresearch.py` - Test deep research functionality

### Manual Testing Workflow

1. **Data Preparation Test**:
   ```bash
   python SFTdata/SFTsplitdataset.py
   # Verify train/test split output
   ```

2. **Training Sanity Check**:
   - Set `max_samples: 100` in config
   - Run training for 1 epoch
   - Verify loss decreases

3. **Model Evaluation Test**:
   ```bash
   # Test with small subset
   python evaluate/answer_v2_gpu.py
   # Check output in testoutput/
   ```

4. **RAG System Test**:
   ```bash
   python agent/test_deepresearch.py
   ```

### SLURM Job Management

```bash
# Submit job
sbatch sub1.sh

# Check status
squeue -u $(whoami)

# Cancel job
scancel <JOBID>

# View logs
tail -f logs/<job_name>-<jobid>.out
```

## Deployment Process

### Model Deployment
1. Complete training and merge LoRA weights
2. Copy merged model to `mergedoutput/`
3. Run evaluation to verify accuracy
4. Deploy via FastAPI or LLaMA-Factory web UI

### RAG System Deployment
1. Ensure Milvus and Elasticsearch are running
2. Load paper embeddings to Milvus collection
3. Start FastAPI server: `python agent/agent_rag_v6.py`
4. API endpoints available at `http://localhost:8000`

## Security Considerations

1. **API Keys**: No hardcoded API keys in source files
2. **Data Access**: RAG system implements access control in `SecureStateManager`
3. **LLM Agent Restrictions**: Raw numerical recipe data is protected from direct LLM access
4. **Input Validation**: All API inputs use Pydantic models for validation

## Common Issues

1. **CUDA Out of Memory**: Reduce `per_device_train_batch_size` or use gradient checkpointing
2. **Tokenizer Parallelism**: Set `TOKENIZERS_PARALLELISM=false` if encountering deadlocks
3. **NCCL Issues**: Uncomment NCCL environment variables in `sub1.sh` for multi-GPU training
4. **Milvus Connection**: Ensure Milvus server is running at `localhost:19530`

## Key File Reference

| File | Purpose |
|------|---------|
| `lora_sft.yaml` | Main SFT training configuration |
| `dataset_info.json` | Dataset registry for LLaMA-Factory |
| `sub1.sh` | SLURM job submission for GPU training |
| `agent/agent_rag_v6.py` | Latest multi-agent RAG implementation |
| `evaluate/answer_v2_gpu.py` | Primary evaluation script |
| `SFTdata/allsftdata.jsonl` | Main training dataset |
