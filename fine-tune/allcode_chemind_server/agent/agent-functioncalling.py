import os
import json
import operator
import torch
import random  # 用于模拟实验结果
from typing import TypedDict, Annotated, List, Dict, Union
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import chromadb
from chromadb.utils import embedding_functions

# ==========================================
# 1. 模拟你的自研算法与硬件接口 (Mock Tools)
# ==========================================

class ProprietaryTools:
    """
    这里模拟你提到的所有自研算法和硬件接口
    """
    
    @staticmethod
    def literature_mining(docs: List[str]) -> Dict:
        """模拟：从匹配的论文中挖掘基准配方和分子"""
        print(f"  [Tool] 正在从 {len(docs)} 篇论文中挖掘电解液信息...")
        # 模拟返回一个基准配方：EC, DEC, LiPF6
        return {
            "base_components": ["EC", "DEC", "LiPF6"],
            "suggested_ratio": [1.0, 1.0, 1.0] # 初始比例
        }

    @staticmethod
    def molecular_expansion_and_screening(base_molecules: List[str]) -> List[str]:
        """模拟：分子扩增和性质预测筛选"""
        print(f"  [Tool] 对 {base_molecules} 进行扩增和性质预测...")
        # 模拟增加了一个添加剂 FEC
        return base_molecules + ["FEC"]

    @staticmethod
    def run_hardware_experiment(recipe: Dict[str, float]) -> Dict[str, float]:
        """模拟：硬件实验接口，输入配方，返回电池属性"""
        print(f"\n  >>> [Hardware] 正在执行实验，配方: {recipe}...")
        # 模拟产生实验数据，这里随机生成以演示闭环
        # 假设目标是 循环寿命 > 800
        cycle_life = random.randint(500, 900)
        conductivity = random.uniform(8.0, 12.0)
        print(f"  <<< [Hardware] 实验结束。循环寿命: {cycle_life}, 电导率: {conductivity} mS/cm")
        return {"cycle_life": cycle_life, "conductivity": conductivity}

    @staticmethod
    def bayesian_optimization(history: List[Dict], bounds: Dict) -> Dict[str, float]:
        """模拟：贝叶斯优化算法，根据历史数据推荐新配方"""
        print(f"  [Tool] 调用贝叶斯优化，基于 {len(history)} 组历史数据优化配方...")
        # 简单模拟：在上一轮基础上微调
        last_recipe = history[-1]['recipe']
        new_recipe = {k: round(v + random.uniform(-0.1, 0.1), 2) for k, v in last_recipe.items()}
        # 归一化处理略...
        return new_recipe

# ==========================================
# 2. 本地模型与向量库封装 (Infrastructure)
# ==========================================

class LocalQwenWrapper:
    """
    封装本地 Qwen 模型，使其行为类似 LangChain 的 ChatModel
    """
    def __init__(self, model_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"正在加载本地 Qwen 模型: {model_path} ({self.device})...")
        # 这里仅做代码示意，实际需要加载 tokenizer 和 model
        # from transformers import AutoTokenizer, AutoModelForCausalLM
        # self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        # self.model = AutoModelForCausalLM.from_pretrained(model_path, ...).to(self.device)
        pass

    def invoke(self, prompt_text: str) -> str:
        """
        模拟模型推理
        """
        # 实际代码:
        # inputs = self.tokenizer(prompt_text, return_tensors="pt").to(self.device)
        # outputs = self.model.generate(**inputs, max_new_tokens=512)
        # return self.tokenizer.decode(outputs[0])
        
        # 为了演示跑通，这里返回伪造的 LLM 响应
        if "分析原因" in prompt_text:
            return "根据实验结果，循环寿命未达标。RAG检索显示，FEC含量过低可能导致SEI膜不稳定。建议增加FEC比例，并适当降低EC含量以保持粘度。"
        if "JSON" in prompt_text:
            return json.dumps({"target": "High Cycle Life", "voltage": 4.5})
        return "Thinking..."

class KnowledgeBase:
    from pymilvus import (
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection, utility
)
from sentence_transformers import SentenceTransformer

class IndustrialKnowledgeBase:
    def __init__(self, host="localhost", port="19530"):
        # 1. 连接 Milvus 数据库服务 (内网连接，外部无法访问)
        print("正在连接 Milvus 向量数据库...")
        connections.connect("default", host=host, port=port)
        
        # 加载 Embedding 模型 (比如 BGE-M3)
        self.encoder = SentenceTransformer('BAAI/bge-large-zh-v1.5')
        self.dim = 1024 # 模型输出维度，bge-large 是 1024
        
        # 2. 定义集合结构 (Schema)
        self.collection_name = "electrolyte_papers"
        self._init_collection()

    def _init_collection(self):
        """初始化表结构，如果不存在则创建"""
        if not utility.has_collection(self.collection_name):
            fields = [
                # 主键 ID
                FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
                # 向量字段 (核心)
                FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
                # 存原始文本 (为了省事，工业界通常这里存 oss 路径，但存文本也行)
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                # 元数据：存年份、材料体系，用于过滤
                FieldSchema(name="metadata", dtype=DataType.JSON) 
            ]
            schema = CollectionSchema(fields, "电解液论文知识库")
            self.collection = Collection(self.collection_name, schema)
            
            # 3. 创建索引 (IVF_FLAT 或 HNSW) - 这是查询速度快的关键！
            # 对 1000万级数据，HNSW 是最快的
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64}
            }
            self.collection.create_index(field_name="embeddings", index_params=index_params)
            print("集合与索引创建完毕。")
        else:
            self.collection = Collection(self.collection_name)
            self.collection.load() # 加载到内存准备查询

    def add_papers(self, texts: list[str], metadatas: list[dict]):
        """
        批量插入数据 (Data Ingestion)
        对于 30万篇文档，建议每批次插入 100-500 条
        """
        # 1. 向量化
        vectors = self.encoder.encode(texts)
        
        # 2. 插入 Milvus
        entities = [
            vectors,  # embeddings
            texts,    # content
            metadatas # metadata
        ]
        self.collection.insert(entities)
        self.collection.flush() # 确保数据落盘

    def search(self, query: str, top_k=3):
        """
        高性能检索
        """
        # 1. 查询向量化
        query_vector = self.encoder.encode([query])
        
        # 2. 向量搜索
        search_params = {"metric_type": "COSINE", "params": {"ef": 10}}
        results = self.collection.search(
            data=query_vector,
            anns_field="embeddings",
            param=search_params,
            limit=top_k,
            output_fields=["content", "metadata"] # 同时也把文本取回来
        )
        
        # 3. 格式化返回
        ret = []
        for hits in results:
            for hit in hits:
                ret.append(hit.entity.get("content"))
        return ret

# ==========================================
# 3. 定义状态 (State Definition)
# ==========================================

class ExperimentState(TypedDict):
    # 输入信息
    user_requirement: str        # 用户原始需求
    parsed_req: Dict             # 解析后的结构化需求
    
    # 流程数据
    rag_context: List[str]       # 检索到的论文片段
    molecule_candidates: List[str] # 筛选出的分子
    
    # 实验迭代数据
    current_recipe: Dict[str, float] # 当前配方
    experiment_history: Annotated[List[Dict], operator.add] # 历史记录（自动追加）
    iteration_count: int         # 当前迭代轮次
    
    # 状态标志
    is_success: bool             # 是否达成目标
    analysis_report: str         # LLM 的分析报告

# ==========================================
# 4. 定义节点 (Nodes) - 核心逻辑
# ==========================================

# 初始化资源
kb = KnowledgeBase()
tools = ProprietaryTools()
# 替换你的模型路径
llm = LocalQwenWrapper("/path/to/your/qwen/model") 

def node_design_initial(state: ExperimentState):
    """
    阶段1：设计。解析需求 -> RAG -> 挖掘 -> 初始配方
    """
    print("\n--- [Stage 1: Intelligent Design] ---")
    user_req = state["user_requirement"]
    
    # 1. LLM 解析需求
    # prompt = f"提取以下需求的结构化参数 JSON: {user_req}"
    # parsed_json = llm.invoke(prompt)
    state["parsed_req"] = {"target_metric": "cycle_life > 800"} # 模拟结果
    
    # 2. RAG 检索
    docs = kb.search(user_req)
    state["rag_context"] = docs
    print(f"  [RAG] 检索到 {len(docs)} 条相关知识")
    
    # 3. 调用自研算法挖掘和筛选
    mining_data = tools.literature_mining(docs)
    screened_mols = tools.molecular_expansion_and_screening(mining_data["base_components"])
    state["molecule_candidates"] = screened_mols
    
    # 4. 生成初始配方 (这里简化处理，实际可能由 LLM 结合挖掘数据生成)
    initial_recipe = {mol: 1.0/len(screened_mols) for mol in screened_mols}
    
    return {
        "current_recipe": initial_recipe, 
        "iteration_count": 0,
        "experiment_history": []
    }

def node_execute_experiment(state: ExperimentState):
    """
    阶段2：实验。调用硬件接口
    """
    print(f"\n--- [Stage 2: Automation Experiment] (Iter: {state['iteration_count']}) ---")
    recipe = state["current_recipe"]
    
    # 调用硬件封装函数
    result = tools.run_hardware_experiment(recipe)
    
    # 记录历史
    record = {
        "iteration": state["iteration_count"],
        "recipe": recipe,
        "result": result
    }
    
    # 简单的成功判断逻辑 (实际应更复杂)
    success = result["cycle_life"] > 800
    
    return {
        "experiment_history": [record], # Append mode
        "is_success": success
    }

def node_optimize_loop(state: ExperimentState):
    """
    阶段3：闭环优化。LLM 分析 -> 贝叶斯优化 -> 新配方
    """
    print("\n--- [Stage 3: Closed-Loop Optimization] ---")
    history = state["experiment_history"]
    last_result = history[-1]
    
    # 1. LLM 分析原因
    # 将 RAG 知识和实验结果一起喂给 Qwen
    prompt = f"""
    背景知识: {state['rag_context']}
    用户目标: {state['user_requirement']}
    当前配方: {last_result['recipe']}
    实验结果: {last_result['result']}
    
    请分析实验失败的原因，并给出调整方向。
    """
    analysis = llm.invoke(prompt)
    state["analysis_report"] = analysis
    print(f"  [LLM Analyst] {analysis}")
    
    # 2. 调用贝叶斯优化生成新配方
    # 贝叶斯算法利用所有的 history 数据
    new_recipe = tools.bayesian_optimization(history, bounds={})
    
    return {
        "current_recipe": new_recipe,
        "iteration_count": state["iteration_count"] + 1
    }

# ==========================================
# 5. 构建 LangGraph 图 (Graph Construction)
# ==========================================

workflow = StateGraph(ExperimentState)

# 添加节点
workflow.add_node("design", node_design_initial)
workflow.add_node("experiment", node_execute_experiment)
workflow.add_node("optimize", node_optimize_loop)

# 设置入口
workflow.set_entry_point("design")

# 定义条件边：判断实验是否成功或达到最大迭代次数
def check_condition(state: ExperimentState):
    if state["is_success"]:
        print("\n>>> 🎯 目标达成！实验成功！")
        return END
    
    if state["iteration_count"] >= 5: # 最大迭代 5 次
        print("\n>>> 🛑 达到最大迭代次数，停止。")
        return END
    
    return "optimize"

# 连接节点
workflow.add_edge("design", "experiment") # 设计完直接去实验
workflow.add_conditional_edges(
    "experiment",
    check_condition,
    {
        END: END,
        "optimize": "optimize"
    }
)
workflow.add_edge("optimize", "experiment") # 优化完通过新配方再次实验 (闭环)

# 编译图
app = workflow.compile()

# ==========================================
# 6. 运行 Agent (Execution)
# ==========================================

if __name__ == "__main__":
    # 用户输入需求
    user_input = "设计一款高电压(4.5V)的三元锂电池电解液，要求循环寿命大于800圈"
    
    # 初始状态
    initial_state = {
        "user_requirement": user_input,
        "experiment_history": [],
        "iteration_count": 0,
        "is_success": False
    }
    
    # 运行流
    print(f"🚀 启动 AI 电解液研发平台 Agent...")
    for output in app.stream(initial_state):
        pass # 实时输出已在节点 print 中打印
    
    print("\n✅ 流程结束。")