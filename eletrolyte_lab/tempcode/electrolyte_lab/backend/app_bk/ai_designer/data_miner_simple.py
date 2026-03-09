"""
简化的文献挖掘与数据扩增器 - 专注于快速演示功能
"""
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DataMiner:
    """文献挖掘与数据扩增器 - 简化版本"""

    def __init__(self):
        logger.info("DataMiner简化版本初始化")

    def mine_and_augment(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行文献挖掘和数据扩增

        Args:
            parameters: 用户确认的性能参数

        Returns:
            Dict: 包含文献搜索结果和扩增配方数据的数据集
        """
        try:
            logger.info("开始文献挖掘与数据扩增")

            # 提取关键词
            keywords = self._extract_keywords(parameters)
            logger.info(f"提取的关键词: {keywords}")

            # 生成模拟文献搜索结果
            bm25_results = self._create_mock_literature_results(keywords)
            literature_titles = [result['title'] for result in bm25_results]

            # 生成模拟文本挖掘结果
            text_mining_results = self._create_mock_text_mining_results(literature_titles)

            # 生成扩增配方数据
            augmented_formulas = self._create_augmented_formulas(parameters)

            # 构建返回数据集
            dataset = {
                'augmented_formulas': augmented_formulas,
                'bm25_search_results': bm25_results,
                'text_mining_results': text_mining_results,
                'extracted_keywords': keywords,
                'literature_count': len(bm25_results),
                'formulation_count': len(augmented_formulas),
                'mining_timestamp': datetime.now().isoformat()
            }

            logger.info(f"文献挖掘与数据扩增完成: 文献={len(bm25_results)}, 配方={len(augmented_formulas)}")
            return dataset

        except Exception as e:
            logger.error(f"文献挖掘与数据扩增失败: {str(e)}")
            raise Exception(f"文献挖掘与数据扩增失败: {str(e)}")

    def _extract_keywords(self, parameters: Dict[str, Any]) -> List[str]:
        """从参数中提取英文关键词"""
        keywords = []

        try:
            # 性能参数
            performance_params = parameters.get('performance_params', {})
            if isinstance(performance_params, dict):
                for key, perf_data in performance_params.items():
                    if isinstance(perf_data, dict):
                        perf_value = perf_data.get('value')
                    else:
                        perf_value = perf_data

                    if perf_value:
                        if key == 'energy_density':
                            keywords.append(f"energy density {perf_value}")
                        elif key == 'power_density':
                            keywords.append(f"power density {perf_value}")
                        elif key == 'cycle_life':
                            keywords.append(f"cycle life {perf_value}")
                        elif key == 'working_temperature':
                            keywords.append(f"temperature {perf_value}")

            # 系统类型
            system_type = parameters.get('system_type')
            if system_type and isinstance(system_type, dict):
                st_value = system_type.get('value')
                if st_value:
                    keywords.append(f"{st_value} material")

            # 应用场景
            app_scenario = parameters.get('application_scenario')
            if app_scenario and isinstance(app_scenario, dict):
                app_value = app_scenario.get('value')
                if app_value:
                    keywords.append(f"{app_value} application")

            # 通用关键词
            keywords.extend(['electrolyte', 'battery', 'energy storage'])

            # 去重
            keywords = list(set(keywords))
            logger.info(f"提取的关键词: {keywords}")

        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            keywords = ['electrolyte', 'battery']

        return keywords

    def _create_mock_literature_results(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """创建模拟文献搜索结果"""
        mock_results = []

        # 基于关键词生成相关的模拟文献
        base_titles = [
            "High-Energy Density Electrolytes for Lithium-Ion Batteries",
            "Advanced Electrolyte Systems for Electric Vehicle Applications",
            "Novel Electrolyte Additives for Enhanced Battery Performance",
            "Optimization of Electrolyte Composition for High-Rate Applications",
            "Safety-Enhanced Electrolyte Design for Commercial Battery Systems"
        ]

        # 基于关键词调整标题
        adjusted_titles = list(base_titles)
        if any('energy density' in kw.lower() for kw in keywords):
            adjusted_titles[0] = "High-Energy Density Electrolytes for Advanced Lithium-Ion Batteries"
        if any('power density' in kw.lower() for kw in keywords):
            adjusted_titles[2] = "High-Power Density Electrolyte Additives for Fast Charging Applications"
        if any('cycle life' in kw.lower() for kw in keywords):
            adjusted_titles[1] = "Long-Cycle-Life Electrolyte Systems for Battery Applications"

        for i, title in enumerate(adjusted_titles):
            score = round(random.uniform(20.0, 45.0), 2)
            mock_results.append({
                "score": score,
                "title": title,
                "abstract": f"This paper discusses advanced electrolyte formulations for battery applications. The research focuses on improving performance metrics such as energy density, power density, and cycle life. Experimental results show significant improvements over conventional electrolyte systems with enhanced safety characteristics and longer cycle life.",
                "doi": f"10.1002/chemrev.{2023 + i}.{1000 + i * 100}",
                "year": 2023 + i,
                "authors": f"Smith, J.; Johnson, A.; Williams, B.; Brown, C.; Davis, M.",
                "journal": "Journal of Power Sources" if i % 2 == 0 else "Electrochimica Acta"
            })

        # 按评分排序
        mock_results.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"生成 {len(mock_results)} 条模拟文献结果")
        return mock_results

    def _create_mock_text_mining_results(self, literature_titles: List[str]) -> List[Dict[str, Any]]:
        """创建模拟文本挖掘结果"""
        text_mining_results = []

        # 为每个文献生成挖掘结果
        for i, title in enumerate(literature_titles[:5]):  # 限制前5篇
            result = {
                "type": "structured_result",
                "source_title": title,
                "extracted_data": {
                    "electrolyte_components": [
                        {
                            "name": random.choice(["EC", "DEC", "EMC", "PC"]),
                            "concentration": round(random.uniform(20, 40), 1),
                            "role": "solvent"
                        },
                        {
                            "name": random.choice(["LiPF6", "LiTFSI", "LiFSI"]),
                            "concentration": round(random.uniform(0.8, 1.5), 2),
                            "role": "salt"
                        }
                    ],
                    "performance_metrics": {
                        "energy_density": round(random.uniform(250, 350), 1),
                        "power_density": round(random.uniform(1000, 3000), 1),
                        "cycle_life": round(random.uniform(1000, 3000), 1),
                        "safety_score": round(random.uniform(0.7, 0.95), 2)
                    },
                    "key_findings": [
                        "Improved electrolyte stability",
                        "Enhanced ionic conductivity",
                        "Better thermal performance"
                    ]
                },
                "confidence_score": round(random.uniform(0.75, 0.95), 2)
            }
            text_mining_results.append(result)

        # 添加一个总体分析结果
        text_mining_results.append({
            "type": "summary_analysis",
            "total_papers_analyzed": len(literature_titles),
            "trend_analysis": {
                "common_components": ["EC", "LiPF6", "EMC"],
                "performance_trends": {
                    "average_energy_density": 280,
                    "average_cycle_life": 1500,
                    "safety_improvement": "Significant"
                },
                "research_directions": [
                    "High-voltage electrolytes",
                    "Flame-retardant additives",
                    "Low-temperature performance"
                ]
            }
        })

        logger.info(f"生成 {len(text_mining_results)} 条文本挖掘结果")
        return text_mining_results

    def _create_augmented_formulas(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成扩增的电解质配方数据"""
        formulas = []

        # 溶剂数据
        solvents = [
            {"name": "EC", "properties": {"dielectric_constant": 90, "viscosity": 1.9, "boiling_point": 248}},
            {"name": "DEC", "properties": {"dielectric_constant": 2.8, "viscosity": 0.75, "boiling_point": 126}},
            {"name": "EMC", "properties": {"dielectric_constant": 2.9, "viscosity": 0.65, "boiling_point": 110}},
            {"name": "PC", "properties": {"dielectric_constant": 65, "viscosity": 2.5, "boiling_point": 242}}
        ]

        # 锂盐数据
        salts = [
            {"name": "LiPF6", "properties": {"conductivity": 10.2, "cost": "medium", "stability": "good"}},
            {"name": "LiTFSI", "properties": {"conductivity": 9.8, "cost": "high", "stability": "excellent"}},
            {"name": "LiFSI", "properties": {"conductivity": 10.5, "cost": "high", "stability": "excellent"}},
            {"name": "LiBF4", "properties": {"conductivity": 8.5, "cost": "high", "stability": "excellent"}}
        ]

        # 添加剂数据
        additives = [
            {"name": "VC", "properties": {"concentration_range": [1, 5], "sei_formation": "excellent", "stability": "good"}},
            {"name": "FEC", "properties": {"concentration_range": [2, 10], "sei_formation": "excellent", "stability": "excellent"}},
            {"name": "DTD", "properties": {"concentration_range": [1, 3], "sei_formation": "good", "stability": "good"}},
            {"name": "PS", "properties": {"concentration_range": [0.5, 2], "sei_formation": "good", "stability": "medium"}}
        ]

        # 生成6个配方
        for i in range(6):
            formula = {
                "source": "novel_generation",
                "solvent_ratios": [],
                "salt_concentration": None,
                "additive_concentrations": []
            }

            # 选择2-3种溶剂
            selected_solvents = random.sample(solvents, random.randint(2, 3))
            total_ratio = 1.0
            for j, solvent in enumerate(selected_solvents):
                if j == len(selected_solvents) - 1:
                    ratio = total_ratio
                else:
                    ratio = round(random.uniform(0.2, 0.5), 3)
                    total_ratio -= ratio

                formula["solvent_ratios"].append({
                    "name": solvent["name"],
                    "ratio": ratio,
                    "properties": solvent["properties"]
                })

            # 选择一种锂盐
            salt = random.choice(salts)
            formula["salt_concentration"] = {
                "name": salt["name"],
                "concentration": round(random.uniform(0.8, 1.5), 2),
                "unit": "M",
                "properties": salt["properties"]
            }

            # 选择1-2种添加剂
            selected_additives = random.sample(additives, random.randint(1, 2))
            for additive in selected_additives:
                conc_range = additive["properties"]["concentration_range"]
                formula["additive_concentrations"].append({
                    "name": additive["name"],
                    "concentration": round(random.uniform(conc_range[0], conc_range[1]), 2),
                    "unit": "wt%",
                    "properties": additive["properties"]
                })

            formulas.append(formula)

        logger.info(f"生成 {len(formulas)} 个电解质配方")
        return formulas