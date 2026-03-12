# AGENTS.md - 项目智能体指南

## 项目概述

本项目是一个**电解质研究知识图谱系统**，集成了文本挖掘、知识图谱构建与可视化、以及基于知识图谱的智能问答功能。

**开发者**: Jiahua Xiao, Xiongfei Du  
**创建日期**: 2026/02/06

---

## 系统架构

系统由三大核心模块组成：

```
┌─────────────────────────────────────────────────────────────────┐
│                      电解质知识图谱系统                           │
├─────────────────┬─────────────────────┬─────────────────────────┤
│   模块1: 文本挖掘  │   模块2: 知识图谱构建   │   模块3: 智能问答系统     │
├─────────────────┼─────────────────────┼─────────────────────────┤
│ • PDF文本提取    │ • 实体ID分配         │ • 实体向量化            │
│ • 信息抽取      │ • CSV格式转换        │ • 相似度搜索            │
│ • JSON输出      │ • Neo4j导入         │ • GUI交互界面           │
│                │ • 实体融合           │ • LLM回答生成           │
└─────────────────┴─────────────────────┴─────────────────────────┘
```

---

## 核心文件说明

### 1. 配置文件

| 文件 | 说明 |
|------|------|
| `ontology_v2.json` | 本体定义文件，包含实体类型、关系类型和属性 schema |

### 2. 文本挖掘模块

| 文件 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `pdf_to_cleaned_text.py` | PDF 转清洗文本 | `research_paper_store_here/*.pdf` | `paper_text_json_cleaned/*.json` |
| `process_miner_by_patch.py` | 批量处理文本挖掘 | 清洗后的 JSON | `entities_info/*.json` |
| `KG_info_miner.py` | 核心挖掘逻辑（被调用） | 文本块 | 实体/关系提取结果 |

### 3. 知识图谱构建模块

| 文件 | 功能 | 依赖 |
|------|------|------|
| `assign_id_to_entities.py` | 为实体分配唯一ID | `entities_info/` → `entities_info_with_id/` |
| `ontology_csv_container.py` | 生成本体 CSV 模板 | `ontology_v2.json` → CSV 文件 |
| `sort_KG_miner_output.py` | 整理实体关系到 CSV | 配合 Neo4j 导入格式 |
| `neo4j_KG_importer.py` | Neo4j 数据库导入 | Neo4j 连接配置 |
| `neo4j_fuser.py` | 实体融合（去重合并） | Neo4j 中已导入的数据 |

### 4. 智能问答模块

| 文件 | 功能 |
|------|------|
| `entities_embedder.py` | 生成实体嵌入向量 |
| `query_search_entities.py` | 查询处理与语义搜索 |
| `query_chunker.py` | 查询分块处理 |
| `main_GUI.py` | Tkinter 图形界面 |

---

## 目录结构

```
项目根目录/
├── research_paper_store_here/      # 存放原始 PDF 论文
├── paper_text_json_cleaned/        # PDF 转换后的清洗文本
├── entities_info/                  # 提取的实体信息（原始）
├── entities_info_fused/            # 融合后的实体信息
├── entity_embeddings/              # 实体向量嵌入
├── eval_output_json/               # 评估输出
├── eval_output_json_with_ids/      # 带ID的评估输出
├── ontology_v2.json                # 本体定义
└── *.py                            # 各功能脚本
```

---

## 使用流程

### 🔧 前置准备

1. 确保已安装所有依赖包（需要逐个 `pip install`）
2. 准备好 `ontology_v2.json` 本体定义文件
3. 确保本体格式与示例完全一致

---

### 📖 功能一：文本挖掘

**步骤 1**: 将 PDF 论文放入 `research_paper_store_here/` 目录

**步骤 2**: 运行 PDF 转换脚本
```bash
python pdf_to_cleaned_text.py
```
- 修改 `main()` 中的 `INPUT_DIRECTORY` 和 `OUTPUT_DIRECTORY`

**步骤 3**: 运行信息挖掘
```bash
python process_miner_by_patch.py
```
- 修改 `main()` 中的输入输出目录
- **重要**: 在 `KG_info_miner.py` 中配置：
  - `entity_relationships` 字典
  - `relationship_attributes` 字典  
  - `entity_schemas` 字典
  - **DeepSeek API 配置**

---

### 🕸️ 功能二：知识图谱构建与可视化

**步骤 4**: 为实体分配 ID
```bash
python assign_id_to_entities.py
```
- 从 `ontology_v2.json` 复制 `relationship_attributes` 到脚本中

**步骤 5**: 生成 CSV 容器
```bash
python ontology_csv_container.py
```

**步骤 6**: 整理数据到 CSV
```bash
python sort_KG_miner_output.py
```
- 配置 `csv_path` 和 `ontology_path`

**步骤 7**: 导入 Neo4j
```bash
python neo4j_KG_importer.py
```
- 修改脚本底部的 `CONFIG` 配置

✅ **现在可以登录 Neo4j 浏览器查看知识图谱**

**步骤 8**: 实体融合（可选）
```bash
python neo4j_fuser.py
```
- 配置 Neo4j 连接信息和本体路径

✅ **现在可以查看融合后的知识图谱**

---

### 💬 功能三：智能问答系统

**步骤 9**: 生成实体嵌入
```bash
python entities_embedder.py
```

**步骤 10**: 启动 GUI
```bash
python main_GUI.py
```
- 在 `query_search_entities.py` 中配置 API 信息

✅ **现在可以在 GUI 中输入查询，约 1 分钟后获得基于知识图谱的回答**

---

## 本体 Schema 定义

### 实体类型

| 实体类型 | 说明 | 关键属性 |
|---------|------|---------|
| `RESEARCH_PAPER` | 研究论文 | doi, title, year, keywords |
| `Electrolyte` | 电解质 | name, type, description |
| `Ionic_Conductivity_Property` | 离子电导率 | ion_type, value, unit |
| `Polymers` | 聚合物 | name, cas, smiles, abbreviation |
| `Monomers` | 单体 | name, cas, smiles |
| `Salts` | 盐 | name, cas, smiles |
| `Additives` | 添加剂 | name, cas, smiles |
| `Initiators` | 引发剂 | name, cas, smiles |

### 关系类型

| 关系 | 源实体 → 目标实体 | 属性 |
|------|------------------|------|
| `REPORTS` | RESEARCH_PAPER → Electrolyte | description, section_in_paper |
| `CONTAINS_DATA_ON` | RESEARCH_PAPER → Ionic_Conductivity_Property | description, data_location |
| `MEASUREMENT` | Electrolyte → Ionic_Conductivity_Property | Temperature_condition |
| `CONSISTS_OF` | Electrolyte → (Polymers/Monomers/Salts/Additives/Initiators) | concentration, ratio, role |

---

## 开发注意事项

### API 配置

项目使用 DeepSeek API 进行文本挖掘和问答生成，需要在以下文件中配置：
- `KG_info_miner.py` - 信息抽取
- `query_search_entities.py` - 查询回答

### Neo4j 配置

以下文件需要配置 Neo4j 连接信息：
- `neo4j_KG_importer.py`
- `neo4j_fuser.py`

配置项包括：`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

### 自定义提示词

如需让机器人回答**非电解质推荐类**的问题，可修改：
- 文件：`query_search_entities.py`
- 函数：`retrieve_and_analyze_summaries()`
- 修改 LLM 的 prompt 模板

---

## 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 实体抽取为空 | API 配置错误 | 检查 DeepSeek API Key |
| Neo4j 导入失败 | 格式不匹配 | 检查 CSV 格式和本体定义一致性 |
| 查询无结果 | 向量未生成 | 确认已运行 `entities_embedder.py` |
| GUI 无法启动 | Tkinter 未安装 | `pip install tk` |

---

## 开发者寄语

> To someone who finds this very last 彩蛋：
> I wish you all the best and succeed in whatever future/path you choose to take!

祝使用愉快！如有问题，请参考 `README.txt` 或检查各脚本内的注释。
