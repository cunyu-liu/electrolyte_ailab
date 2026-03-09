import random
import json
from typing import Dict, List, Any
import logging
import sys
import os

# 添加文本挖掘算法路径
sys.path.append(r'D:\electrolyte\ChemMind_pdfExtractor')
CHESTMIND_AVAILABLE = False

try:
    # 尝试直接导入ChemMind模块
    from main_port import main_port
    CHESTMIND_AVAILABLE = True
    logging.info("ChemMind文本挖掘模块加载成功")

    # 设置必要的文件路径
    import os
    os.environ['CSV_PATH'] = r'C:\Users\electrolyte\Desktop\ChemMind_backend\ChemMind_pdfExtractor\battery_papers_combined.csv'
    os.environ['BASE_DIR'] = r'F:\paper\downloads'
    os.environ['JSON_OUTPUT_PATH'] = r'D:\electrolyte\code\temp_text_mining_output.json'

except ImportError as e:
    logging.warning(f"ChemMind文本挖掘模块不可用: {e}")
    CHESTMIND_AVAILABLE = False
except Exception as e:
    logging.warning(f"ChemMind模块加载失败: {e}")
    CHESTMIND_AVAILABLE = False

from .bm25_searcher import extract_keywords_from_parameters

# 导入外部的BM25搜索函数
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("newsearch", r"D:\electrolyte\BO\dbsearch.py")
newsearch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newsearch_module)
bm25_search_from_postgres = newsearch_module.bm25_search_from_postgres

logger = logging.getLogger(__name__)

class DataMiner:
    """文献挖掘与数据扩增器"""

    def __init__(self):
        # 常用溶剂
        self.common_solvents = [
            {'name': 'EC', 'chemical_formula': 'C3H4O3', 'type': 'solvent', 'properties': {'dielectric_constant': 90, 'viscosity': 1.9, 'boiling_point': 248}},
            {'name': 'DEC', 'chemical_formula': 'C5H10O3', 'type': 'solvent', 'properties': {'dielectric_constant': 2.8, 'viscosity': 0.75, 'boiling_point': 126}},
            {'name': 'DMC', 'chemical_formula': 'C3H6O3', 'type': 'solvent', 'properties': {'dielectric_constant': 3.1, 'viscosity': 0.59, 'boiling_point': 90}},
            {'name': 'EMC', 'chemical_formula': 'C4H8O3', 'type': 'solvent', 'properties': {'dielectric_constant': 2.9, 'viscosity': 0.65, 'boiling_point': 110}},
            {'name': 'PC', 'chemical_formula': 'C4H6O3', 'type': 'solvent', 'properties': {'dielectric_constant': 65, 'viscosity': 2.5, 'boiling_point': 242}}
        ]

        # 常用锂盐
        self.common_salts = [
            {'name': 'LiPF6', 'chemical_formula': 'LiPF6', 'type': 'salt', 'properties': {'conductivity': 10.2, 'stability': 'good', 'cost': 'medium'}},
            {'name': 'LiBF4', 'chemical_formula': 'LiBF4', 'type': 'salt', 'properties': {'conductivity': 8.5, 'stability': 'excellent', 'cost': 'high'}},
            {'name': 'LiClO4', 'chemical_formula': 'LiClO4', 'type': 'salt', 'properties': {'conductivity': 11.3, 'stability': 'poor', 'cost': 'low'}},
            {'name': 'LiTFSI', 'chemical_formula': 'LiTFSI', 'type': 'salt', 'properties': {'conductivity': 9.8, 'stability': 'excellent', 'cost': 'high'}}
        ]

        # 常用添加剂
        self.common_additives = [
            {'name': 'VC', 'chemical_formula': 'C3H4O3', 'type': 'additive', 'properties': {'sei_formation': 'excellent', 'stability': 'good', 'concentration_range': [1, 5]}},
            {'name': 'FEC', 'chemical_formula': 'C3H5FO3', 'type': 'additive', 'properties': {'sei_formation': 'excellent', 'stability': 'excellent', 'concentration_range': [2, 10]}},
            {'name': 'PS', 'chemical_formula': 'C8H8O3S', 'type': 'additive', 'properties': {'sei_formation': 'good', 'stability': 'medium', 'concentration_range': [0.5, 2]}},
            {'name': 'DTD', 'chemical_formula': 'C4H6O4S2', 'type': 'additive', 'properties': {'sei_formation': 'good', 'stability': 'good', 'concentration_range': [1, 3]}},
            {'name': 'LiBOB', 'chemical_formula': 'C4BO8Li', 'type': 'additive', 'properties': {'sei_formation': 'good', 'stability': 'excellent', 'concentration_range': [2, 8]}}
        ]

  
    
    def mine_and_augment(self, confirmed_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        文献挖掘与数据扩增

        Args:
            confirmed_parameters: 用户确认的参数

        Returns:
            包含原始和扩增配方的数据集
        """
        try:
            logger.info(f"开始文献挖掘和数据扩增，参数: {json.dumps(confirmed_parameters, ensure_ascii=False)}")

            # 1. 从参数中提取关键词
            keywords = extract_keywords_from_parameters(confirmed_parameters)
            logger.info(f"提取的关键词: {keywords}")

            # 2. 执行BM25搜索（必须使用真实数据库，带超时控制）
            bm25_results = []
            literature_titles = []
            if keywords:
                try:
                    logger.info(f"开始BM25搜索，关键词: {keywords}")

                    # 使用线程进行超时控制
                    import threading
                    import queue

                    bm25_queue = queue.Queue()

                    def run_bm25_search():
                        try:
                            # 重定向标准输出以避免编码问题
                            import io
                            import sys
                            old_stdout = sys.stdout
                            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

                            # 使用D:\electrolyte\BO\newsearch.py中的函数
                            results, titles = bm25_search_from_postgres(
                                dbname="postgres",
                                user="postgres",
                                password="123456",
                                host="localhost",
                                port=5432,
                                keywords=keywords,
                                top_k=5  # 限制结果数量以加快速度
                            )

                            # 恢复标准输出
                            sys.stdout = old_stdout
                            bm25_queue.put(("success", results, titles))
                        except Exception as e:
                            # 恢复标准输出
                            try:
                                sys.stdout = old_stdout
                            except:
                                pass
                            bm25_queue.put(("error", str(e), []))

                    # 启动BM25搜索线程
                    bm25_thread = threading.Thread(target=run_bm25_search)
                    bm25_thread.daemon = True
                    bm25_thread.start()

                    # 等待最多30秒
                    bm25_thread.join(timeout=30)

                    if bm25_thread.is_alive():
                        # BM25搜索超时
                        logger.warning("BM25搜索超时（30秒），跳过文献匹配")
                        bm25_results = []
                        literature_titles = []
                    else:
                        # 获取BM25搜索结果
                        try:
                            status, results, titles = bm25_queue.get_nowait()
                            if status == "success":
                                bm25_results = results
                                literature_titles = titles
                                logger.info(f"BM25搜索返回 {len(bm25_results)} 个结果")
                            else:
                                logger.error(f"BM25搜索失败: {results}")
                                raise Exception(f"BM25数据库搜索失败: {results}")
                        except queue.Empty:
                            logger.error("BM25搜索结果获取失败")
                            raise Exception("BM25搜索结果获取失败")

                    if len(bm25_results) == 0:
                        logger.warning("BM25搜索未找到任何相关文献")

                except Exception as bm25_error:
                    logger.error(f"BM25搜索过程出错: {str(bm25_error)}")
                    raise Exception(f"文献挖掘失败: {str(bm25_error)}. 请确保PostgreSQL数据库正在运行并包含papers表.")

            # 3. 传统文献挖掘（作为BM25的补充或备选）
            mined_formulas = self._mine_literature(confirmed_parameters)

            # 4. 文本挖掘处理BM25结果（简化版，避免超时）
            text_mining_results = []
            if literature_titles and CHESTMIND_AVAILABLE:
                try:
                    logger.info(f"开始对 {len(literature_titles)} 篇文献进行文本挖掘（最多处理前2篇）")

                    # 严格限制处理的文献数量
                    limited_titles = literature_titles[:2] if len(literature_titles) > 2 else literature_titles
                    logger.info(f"实际处理 {len(limited_titles)} 篇文献")

                    # 构建用户需求文本
                    user_requests = self._build_user_request_text(confirmed_parameters)

                    # 调用ChemMind文本挖掘算法
                    api_key = "sk-6236f3f7c04a42539febd13766f383d8"
                    model = "deepseek-chat"

                    # 确保输出目录存在
                    os.makedirs(os.path.dirname(r'D:\electrolyte\code\temp_text_mining_output.json'), exist_ok=True)

                    # 使用线程进行超时控制
                    import threading
                    import queue

                    result_queue = queue.Queue()

                    def run_text_mining():
                        try:
                            output = main_port(user_requests, api_key, model, limited_titles)
                            result_queue.put(("success", output))
                        except Exception as e:
                            result_queue.put(("error", str(e)))

                    # 启动文本挖掘线程
                    mining_thread = threading.Thread(target=run_text_mining)
                    mining_thread.daemon = True
                    mining_thread.start()

                    # 等待最多45秒
                    mining_thread.join(timeout=45)

                    if mining_thread.is_alive():
                        # 线程仍在运行，说明超时了
                        logger.warning("文本挖掘超时（45秒），跳过此步骤")
                        text_mining_results = [{"type": "timeout", "message": "文本挖掘超时，已跳过"}]
                    else:
                        # 线程已完成，获取结果
                        try:
                            status, output = result_queue.get_nowait()
                            if status == "success":
                                logger.info("文本挖掘完成")
                                text_mining_results = self._parse_text_mining_output(output)
                                logger.info(f"文本挖掘获得 {len(text_mining_results)} 个结果")
                            else:
                                logger.error(f"文本挖掘失败: {output}")
                                text_mining_results = [{"type": "error", "message": f"文本挖掘失败: {output}"}]
                        except queue.Empty:
                            text_mining_results = [{"type": "error", "message": "文本挖掘结果获取失败"}]

                except Exception as text_mining_error:
                    logger.error(f"文本挖掘过程出错: {str(text_mining_error)}")
                    # 文本挖掘失败不影响整体流程，但记录错误
                    text_mining_results = [{"type": "error", "message": f"文本挖掘过程出错: {str(text_mining_error)}"}]

            # 5. 数据扩增
            augmented_formulas = self._augment_data(mined_formulas, confirmed_parameters)

            # 6. 组合结果
            formula_dataset = {
                'original_formulas': mined_formulas,
                'augmented_formulas': augmented_formulas,
                'total_count': len(mined_formulas) + len(augmented_formulas),
                'source_parameters': confirmed_parameters,
                'generation_timestamp': self._get_timestamp(),
                # 添加BM25搜索结果
                'bm25_search_results': bm25_results,
                'extracted_keywords': keywords,
                'text_mining_results': text_mining_results,
                'search_summary': {
                    'keywords_count': len(keywords),
                    'bm25_results_count': len(bm25_results),
                    'text_mining_count': len(text_mining_results),
                    'literature_mined_count': len(mined_formulas)
                }
            }

            logger.info(f"数据挖掘和扩增完成，共生成 {formula_dataset['total_count']} 个配方，BM25搜索到 {len(bm25_results)} 篇相关文献，文本挖掘获得 {len(text_mining_results)} 个结果")
            return formula_dataset

        except Exception as e:
            logger.error(f"数据挖掘和扩增时出错: {str(e)}")
            raise Exception(f"数据挖掘和扩增失败: {str(e)}")

    def _mine_literature(self, parameters: Dict[str, Any]) -> List[Dict]:
        """文献挖掘 - 现在只依赖BM25搜索结果"""
        # 由于移除了模拟文献数据库，这里返回空列表
        # 文献挖掘现在完全依赖mine_and_augment中的BM25搜索结果
        return []

    
    def _augment_data(self, mined_formulas: List[Dict], parameters: Dict) -> List[Dict]:
        """数据扩增"""
        augmented_formulas = []

        # 生成方法1: 组合变异
        for base_formula in mined_formulas[:5]:  # 取前5个作为基础
            variants = self._generate_combination_variants(base_formula, parameters)
            augmented_formulas.extend(variants)

        # 生成方法2: 基于分子数据库的新分子
        novel_formulas = self._generate_novel_formulas(parameters)
        augmented_formulas.extend(novel_formulas)

        # 生成方法3: 基于机器学习的生成
        ml_formulas = self._generate_ml_formulas(parameters)
        augmented_formulas.extend(ml_formulas)

        return augmented_formulas

    def _generate_combination_variants(self, base_formula: Dict, parameters: Dict) -> List[Dict]:
        """生成组合变异"""
        variants = []

        # 变异1: 替换溶剂
        for _ in range(2):
            variant = base_formula.copy()
            # 随机替换一个溶剂
            if len(variant['solvent_ratios']) > 1:
                idx_to_replace = random.randint(0, len(variant['solvent_ratios']) - 1)
                new_solvent = random.choice(self.common_solvents)
                variant['solvent_ratios'][idx_to_replace] = {
                    'name': new_solvent['name'],
                    'ratio': variant['solvent_ratios'][idx_to_replace]['ratio'],
                    'properties': new_solvent['properties']
                }
                variant['source'] = 'combination_variant_solvent'
                variants.append(variant)

        # 变异2: 调整添加剂
        for _ in range(2):
            variant = base_formula.copy()
            # 调整添加剂浓度
            for additive in variant['additive_concentrations']:
                adjustment = random.uniform(0.8, 1.2)
                additive['concentration'] *= adjustment
            variant['source'] = 'combination_variant_additive'
            variants.append(variant)

        return variants

    def _generate_novel_formulas(self, parameters: Dict) -> List[Dict]:
        """基于分子数据库生成新配方"""
        novel_formulas = []

        for _ in range(5):
            # 随机选择组件
            selected_solvents = random.sample(self.common_solvents, random.randint(2, 3))
            selected_salt = random.choice(self.common_salts)
            selected_additives = random.sample(self.common_additives, random.randint(1, 2))

            formula = {
                'solvent_ratios': [
                    {
                        'name': s['name'],
                        'ratio': 1.0 / len(selected_solvents),
                        'properties': s['properties']
                    } for s in selected_solvents
                ],
                'salt_concentration': {
                    'name': selected_salt['name'],
                    'concentration': random.uniform(0.8, 1.5),
                    'unit': 'M',
                    'properties': selected_salt['properties']
                },
                'additive_concentrations': [
                    {
                        'name': a['name'],
                        'concentration': random.uniform(*a['properties']['concentration_range']),
                        'unit': 'wt%',
                        'properties': a['properties']
                    } for a in selected_additives
                ],
                'source': 'novel_generation'
            }

            novel_formulas.append(formula)

        return novel_formulas

    def _generate_ml_formulas(self, parameters: Dict) -> List[Dict]:
        """基于机器学习生成配方"""
        ml_formulas = []

        # 这里模拟机器学习生成过程
        # 实际实现中会调用训练好的生成模型

        for i in range(3):
            # 基于参数分布生成
            formula = {
                'solvent_ratios': [
                    {
                        'name': 'EC',
                        'ratio': 0.4 + random.uniform(-0.1, 0.1),
                        'properties': self.common_solvents[0]['properties']
                    },
                    {
                        'name': 'EMC',
                        'ratio': 0.6 + random.uniform(-0.1, 0.1),
                        'properties': self.common_solvents[3]['properties']
                    }
                ],
                'salt_concentration': {
                    'name': 'LiPF6',
                    'concentration': 1.0 + random.uniform(-0.2, 0.2),
                    'unit': 'M',
                    'properties': self.common_salts[0]['properties']
                },
                'additive_concentrations': [
                    {
                        'name': 'VC',
                        'concentration': 2.0 + random.uniform(-0.5, 0.5),
                        'unit': 'wt%',
                        'properties': self.common_additives[0]['properties']
                    }
                ],
                'source': 'ml_generation',
                'model_confidence': random.uniform(0.7, 0.95)
            }

            ml_formulas.append(formula)

        return ml_formulas

    
    def _build_user_request_text(self, parameters: Dict) -> str:
        """构建用户需求文本"""
        requests = []

        # 系统类型
        system_type = parameters.get('system_type', {}).get('value', '') if isinstance(parameters.get('system_type'), dict) else parameters.get('system_type', '')
        if system_type:
            requests.append(f"电池类型: {system_type}")

        # 应用场景
        application = parameters.get('application_scenario', {}).get('value', '') if isinstance(parameters.get('application_scenario'), dict) else parameters.get('application_scenario', '')
        if application:
            requests.append(f"应用场景: {application}")

        # 性能要求
        performance = parameters.get('performance_requirements', {})
        if isinstance(performance, dict):
            for key, value in performance.items():
                if value:
                    requests.append(f"性能要求: {value}")

        # 能量和功率目标
        target_energy = parameters.get('target_energy', {})
        if isinstance(target_energy, dict):
            value = target_energy.get('value', '')
            unit = target_energy.get('unit', '')
            if value and unit:
                requests.append(f"能量密度: {value} {unit}")

        target_power = parameters.get('target_power', {})
        if isinstance(target_power, dict):
            value = target_power.get('value', '')
            unit = target_power.get('unit', '')
            if value and unit:
                requests.append(f"功率密度: {value} {unit}")

        return "; ".join(requests) if requests else "通用电解液配方设计"

    def _parse_text_mining_output(self, text_mining_output: str) -> List[Dict]:
        """解析文本挖掘输出结果"""
        try:
            import json

            # 尝试解析JSON输出
            if isinstance(text_mining_output, str):
                # 清理可能的markdown标记
                if '```json' in text_mining_output:
                    json_str = text_mining_output.split('```json')[1].split('```')[0].strip()
                elif text_mining_output.strip().startswith('{'):
                    json_str = text_mining_output.strip()
                else:
                    # 如果不是JSON，直接返回包装的结果
                    return [{"type": "text_result", "content": text_mining_output}]

                data = json.loads(json_str)

                # 根据实际返回结构处理
                if isinstance(data, dict):
                    return [{"type": "structured_result", "data": data}]
                elif isinstance(data, list):
                    return [{"type": "list_result", "items": data}]
                else:
                    return [{"type": "raw_result", "data": data}]

            else:
                return [{"type": "direct_result", "data": text_mining_output}]

        except Exception as e:
            logger.error(f"解析文本挖掘输出失败: {str(e)}")
            return [{"type": "error", "message": str(e), "raw_output": str(text_mining_output)}]

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()