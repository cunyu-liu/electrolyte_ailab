import psycopg2
from rank_bm25 import BM25Okapi
from nltk.tokenize import word_tokenize
import nltk
import logging

logger = logging.getLogger(__name__)

def bm25_search_from_postgres(
    dbname,
    user,
    password,
    host,
    port,
    keywords,
    top_k=10
):
    """
    从 PostgreSQL 读取 papers 表，使用 BM25 进行文本检索，并返回结果。

    参数：
    ----------
    dbname : str
    user : str
    password : str
    host : str
    port : int
    keywords : list[str]   # 查询关键词列表（英文）
    top_k : int            # 返回前 top_k 条结果

    返回：
    ----------
    results : list[dict]
        每条结果包含：
        score, title, abstract, doi, year, authors, journal
    """

    try:
        # === 1. 下载 NLTK 资源（只在第一次真正下载）===
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)

        # === 2. PostgreSQL 连接 ===
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cur = conn.cursor()

        # === 3. 取出全部文档（标题 + 摘要）===
        cur.execute("""
            SELECT title, abstract, doi, year, authors, journal
            FROM papers
            WHERE abstract IS NOT NULL AND abstract <> ''
        """)
        rows = cur.fetchall()

        titles = []
        abstracts = []

        for r in rows:
            titles.append(r[0])
            abstracts.append(r[1])

        print(f"共载入 {len(abstracts)} 篇文档用于 BM25 检索")

        if len(abstracts) == 0:
            logger.warning("没有找到任何有效的文献摘要")
            return []

        # === 4. 构建 BM25 语料库 ===
        tokenized_corpus = [word_tokenize(abs.lower()) for abs in abstracts]
        bm25 = BM25Okapi(tokenized_corpus)

        # === 5. 构建查询 ===
        query_string = " ".join(keywords).lower()
        tokenized_query = word_tokenize(query_string)

        # === 6. BM25 排名 ===
        scores = bm25.get_scores(tokenized_query)

        ranked = sorted(
            list(zip(scores, rows)),
            key=lambda x: x[0],
            reverse=True
        )

        # === 7. 组织输出结果 ===
        results = []
        for i, (score, doc) in enumerate(ranked[:top_k]):
            title, abstract, doi, year, authors, journal = doc

            # 确保分数大于0才添加到结果中
            if score > 0:
                results.append({
                    "score": float(score),
                    "title": title,
                    "abstract": abstract,
                    "doi": doi,
                    "year": year,
                    "authors": authors,
                    "journal": journal
                })

        print(f"BM25排名完成，有效结果: {len(results)} / {len(ranked)}")

        # === 8. 打印结果（保持你原来的输出风格）===
        try:
            print(f"\n=== BM25 排名前 {top_k} 的文档 ===")
            for i, item in enumerate(results):
                print("\n---------------------------------")
                print(f"Rank {i+1}  |  Score = {item['score']:.4f}")
                print("Title:", str(item["title"]).encode('ascii', 'ignore').decode('ascii'))
                print("Year:", item["year"])
                print("DOI:", item["doi"])
                print("Journal:", item["journal"])
                print("Authors:", item["authors"])
                abstract_snippet = str(item["abstract"][:300] + "...") if item["abstract"] else "No abstract"
                print("Abstract snippet:", abstract_snippet)
        except Exception as print_error:
            logger.warning(f"打印BM25结果时出错: {str(print_error)}")
            print(f"BM25搜索完成，找到 {len(results)} 篇相关文献")

        # === 9. 关闭数据库连接 ===
        cur.close()
        conn.close()

        # === 10. 返回结果给外部程序使用 ===
        return results

    except Exception as e:
        logger.error(f"BM25搜索过程中出错: {str(e)}")
        # 在出错时返回空结果，而不是让整个流程崩溃
        return []

def extract_keywords_from_parameters(parameters):
    """
    从用户确认的参数中提取英文关键词

    Args:
        parameters (dict): 用户确认的参数字典

    Returns:
        list[str]: 提取的关键词列表
    """
    keywords = []

    # 参数英文映射表
    parameter_mapping = {
        'system_type': {
            '锂离子电池': ['lithium-ion battery', 'Li-ion battery'],
            '钠离子电池': ['sodium-ion battery', 'Na-ion battery'],
            '锂硫电池': ['lithium-sulfur battery', 'Li-S battery'],
            '锌离子电池': ['zinc-ion battery', 'Zn-ion battery']
        },
        'application_scenario': {
            '电动汽车': ['electric vehicle', 'EV', 'automotive'],
            '储能系统': ['energy storage system', 'ESS', 'grid storage'],
            '消费电子': ['consumer electronics', 'portable devices'],
            '航空航天': ['aerospace', 'aviation', 'spacecraft']
        },
        'performance_requirements': {
            '高能量密度': ['high energy density'],
            '高功率密度': ['high power density', 'high rate'],
            '长循环寿命': ['long cycle life', 'cycle stability'],
            '高安全性': ['high safety', 'safety requirements'],
            '低温性能': ['low temperature performance', 'cold temperature'],
            '高温性能': ['high temperature performance', 'thermal stability']
        },
        'target_energy': {
            'Wh/kg': ['energy density', 'specific energy'],
            'Wh/L': ['volumetric energy density', 'energy density']
        },
        'target_power': {
            'W/kg': ['power density', 'specific power'],
            'W/L': ['volumetric power density']
        }
    }

    try:
        # 提取系统类型关键词
        system_type = parameters.get('system_type', {}).get('value', '')
        if system_type in parameter_mapping['system_type']:
            keywords.extend(parameter_mapping['system_type'][system_type])

        # 提取应用场景关键词
        application = parameters.get('application_scenario', {}).get('value', '')
        if application in parameter_mapping['application_scenario']:
            keywords.extend(parameter_mapping['application_scenario'][application])

        # 提取性能要求关键词
        performance = parameters.get('performance_requirements', {})
        if isinstance(performance, dict):
            for req_value in performance.values():
                if req_value in parameter_mapping['performance_requirements']:
                    keywords.extend(parameter_mapping['performance_requirements'][req_value])

        # 提取目标和值关键词
        target_energy = parameters.get('target_energy', {})
        if isinstance(target_energy, dict):
            value = target_energy.get('value', '')
            unit = target_energy.get('unit', '')
            if unit in parameter_mapping['target_energy']:
                keywords.extend(parameter_mapping['target_energy'][unit])
                # 添加数值范围作为关键词
                if value:
                    keywords.append(f"{value} {unit}")

        target_power = parameters.get('target_power', {})
        if isinstance(target_power, dict):
            value = target_power.get('value', '')
            unit = target_power.get('unit', '')
            if unit in parameter_mapping['target_power']:
                keywords.extend(parameter_mapping['target_power'][unit])
                # 添加数值范围作为关键词
                if value:
                    keywords.append(f"{value} {unit}")

        # 提取其他可能有用的关键词
        other_params = ['working_temperature', 'cycle_life', 'cost_requirements']
        for param in other_params:
            param_data = parameters.get(param, {})
            if isinstance(param_data, dict) and param_data.get('value'):
                keywords.append(param_data['value'])

        # 去重并过滤空值
        keywords = list(set([kw for kw in keywords if kw and len(kw.strip()) > 0]))

        logger.info(f"从参数中提取的关键词: {keywords}")

    except Exception as e:
        logger.error(f"提取关键词时出错: {str(e)}")
        # 返回一些默认关键词
        keywords = ['electrolyte', 'battery', 'energy storage']

    return keywords