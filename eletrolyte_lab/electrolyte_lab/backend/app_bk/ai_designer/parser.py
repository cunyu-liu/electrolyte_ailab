import re
import json
import time
import os
from typing import Dict, List, Any
import logging
from openai import OpenAI
from dotenv import load_dotenv

# 确保环境变量被加载
load_dotenv()

logger = logging.getLogger(__name__)

class RequestParser:
    """需求解析器 - Agent1/LLMs1"""

    def __init__(self):
        # 初始化 LLM 客户端
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30.0  # 设置30秒超时
            )
        else:
            logger.warning("DeepSeek API key not found, falling back to rule-based parsing")
            self.client = None

        # 预定义的关键词映射（作为备选方案）
        self.system_types = {
            '正极': ['正极', '阴极', 'cathode', 'positive'],
            '负极': ['负极', '阳极', 'anode', 'negative']
        }

        # 材料名称识别字典
        self.material_names = {
            '正极材料': {
                'NCM': ['NCM', 'NCM111', 'NCM523', 'NCM622', 'NCM811', '镍钴锰酸锂'],
                'NCA': ['NCA', '镍钴铝酸锂', 'LiNiCoAl'],
                'LFP': ['LFP', '磷酸铁锂', 'LiFePO4'],
                'LCO': ['LCO', '钴酸锂', 'LiCoO2'],
                'LMO': ['LMO', '锰酸锂', 'LiMn2O4'],
                'NMC': ['NMC', '三元材料'],
                '高镍': ['高镍', '高镍三元', 'NCM811', 'NCA'],
                '富锂': ['富锂', '富锂锰基', 'xLi2MnO3'],
                '三元': ['三元材料', 'NCM', 'NCA']
            },
            '负极材料': {
                '石墨': ['石墨', '天然石墨', '人造石墨', 'Graphite'],
                '硅基': ['硅', '硅碳', 'Si', 'SiC', '硅基', '硅负极'],
                'Si/C': ['Si/C', '硅碳复合', '硅碳'],
                '硬碳': ['硬碳', 'Hard Carbon'],
                '软碳': ['软碳', 'Soft Carbon'],
                '钛酸锂': ['LTO', '钛酸锂', 'Li4Ti5O12'],
                '金属锂': ['金属锂', '锂金属', 'Li'],
                '合金': ['合金', '锡基合金', '硅合金']
            }
        }

        self.application_scenarios = {
            '蓄能': ['蓄能', '储能', 'storage', 'energy storage'],
            '动力': ['动力', '汽车', '电动车', 'vehicle', 'automotive', 'EV'],
            '3C': ['3c', '手机', '电脑', '消费电子', 'consumer', 'mobile', 'laptop']
        }

        self.performance_metrics = {
            '能量密度': ['能量密度', '比能量', 'energy density', 'specific energy'],
            '功率密度': ['功率密度', '比功率', 'power density', 'specific power'],
            '安全性': ['安全', 'stable', 'safety', 'stable'],
            '循环寿命': ['寿命', '循环', 'lifetime', 'cycle life', 'durability'],
            '工作温度': ['温度', '温域', 'temperature', 'thermal'],
            '成本': ['成本', '便宜', 'cost', 'cheap', 'price']
        }

        # 参数范围定义
        self.parameter_ranges = {
            '能量密度': {'min': 100, 'max': 500, 'unit': 'Wh/kg'},
            '功率密度': {'min': 100, 'max': 5000, 'unit': 'W/kg'},
            '循环寿命': {'min': 100, 'max': 10000, 'unit': 'cycles'},
            '工作温度': {'min': -40, 'max': 80, 'unit': '°C'}
        }

    def parse_request(self, natural_language_input: str) -> Dict[str, Any]:
        """
        解析自然语言需求，提取关键参数

        Args:
            natural_language_input: 用户输入的自然语言文本

        Returns:
            结构化的key-value参数对象，便于前端展示和修改
        """
        try:
            logger.info(f"开始解析用户需求: {natural_language_input}")

            # 优先使用 LLM 解析
            if self.client:
                try:
                    structured_params = self._parse_with_llm(natural_language_input)
                    logger.info("使用 LLM 解析成功")
                    # 应用增强解析结果逻辑（处理正负极材料识别）
                    processed_input = self._preprocess_input(natural_language_input)
                    self._enhance_parsing_result(structured_params, processed_input)
                    # 应用后处理优化
                    optimized_params = self._post_process_optimization(structured_params, natural_language_input)
                    return optimized_params
                except Exception as e:
                    logger.warning(f"LLM 解析失败，回退到规则解析: {str(e)}")
                    # 回退到规则解析
                    logger.info("使用规则解析方法")
                    # 使用增强的规则解析
                    return self._enhanced_rule_parsing(natural_language_input)

        except Exception as e:
            logger.error(f"解析需求时出错: {str(e)}")
            raise Exception(f"需求解析失败: {str(e)}")

    def _extract_system_type(self, input_text: str) -> str:
        """提取体系类型"""
        input_text_lower = input_text.lower()
        logger.info(f"提取体系类型，输入文本: {input_text}")

        # 统计关键词出现次数，优先选择出现次数更多的体系类型
        type_counts = {}
        found_keywords = {}
        for system_type, keywords in self.system_types.items():
            count = 0
            found = []
            for keyword in keywords:
                # 对于英文关键词使用小写匹配，中文保持原样
                if keyword.isascii():
                    if keyword.lower() in input_text_lower:
                        count += 1
                        found.append(keyword)
                else:
                    if keyword in input_text:
                        count += 1
                        found.append(keyword)
            type_counts[system_type] = count
            found_keywords[system_type] = found

        logger.info(f"关键词统计结果: {type_counts}, 找到的关键词: {found_keywords}")

        # 返回出现次数最多的体系类型
        if type_counts['负极'] > type_counts['正极']:
            logger.info(f"选择负极体系（计数更高）")
            return '负极'
        elif type_counts['正极'] > type_counts['负极']:
            logger.info(f"选择正极体系（计数更高）")
            return '正极'
        elif type_counts['负极'] > 0 or type_counts['正极'] > 0:
            # 如果次数相等但大于0，优先检查负极（因为负极可能更少被明确提及）
            logger.info(f"计数相等，优先检查负极")
            for system_type, keywords in self.system_types.items():
                if system_type == '负极':  # 优先检查负极
                    for keyword in keywords:
                        if keyword.isascii():
                            if keyword.lower() in input_text_lower:
                                logger.info(f"选择负极体系（优先匹配）: {keyword}")
                                return system_type
                        else:
                            if keyword in input_text:
                                logger.info(f"选择负极体系（优先匹配）: {keyword}")
                                return system_type
            # 再检查正极
            for system_type, keywords in self.system_types.items():
                if system_type == '正极':
                    for keyword in keywords:
                        if keyword.isascii():
                            if keyword.lower() in input_text_lower:
                                logger.info(f"选择正极体系: {keyword}")
                                return system_type
                        else:
                            if keyword in input_text:
                                logger.info(f"选择正极体系: {keyword}")
                                return system_type

        logger.info(f"未找到明确的体系类型")
        return None

    def _extract_material_name(self, input_text: str, system_type: str) -> str:
        """提取具体材料名称 - 改进版，支持上下文相关的材料识别"""
        input_text_lower = input_text.lower()

        # 根据体系类型选择对应的材料字典
        if system_type == '正极':
            materials_dict = self.material_names['正极材料']
        elif system_type == '负极':
            materials_dict = self.material_names['负极材料']
        else:
            return ""

        # 检查是否在文本中明确提到了对应的电极类型
        electrode_keywords = {
            '正极': ['正极', '正极材料', '阴极', 'positive electrode', 'cathode'],
            '负极': ['负极', '负极材料', '阳极', 'negative electrode', 'anode']
        }

        # 如果明确提到了电极类型，则只在该上下文中搜索材料
        if any(keyword in input_text for keyword in electrode_keywords.get(system_type, [])):
            return self._extract_material_with_context(input_text, system_type, materials_dict)
        else:
            # 如果没有明确提到电极类型，使用全局搜索
            return self._extract_material_global(input_text, materials_dict)

    def _extract_material_with_context(self, input_text: str, system_type: str, materials_dict: Dict) -> str:
        """在明确的电极上下文中提取材料"""
        # 分割文本，查找包含电极关键词的部分
        electrode_keywords = {
            '正极': ['正极', '正极材料', '阴极'],
            '负极': ['负极', '负极材料', '阳极']
        }

        # 查找包含电极关键词的文本片段
        relevant_text = ""
        for keyword in electrode_keywords.get(system_type, []):
            if keyword in input_text:
                # 提取包含关键词的句子或短语
                sentences = input_text.split('，')
                for sentence in sentences:
                    if keyword in sentence:
                        relevant_text += sentence + " "

        if not relevant_text:
            relevant_text = input_text

        # 在相关文本中搜索材料
        return self._search_material_in_text(relevant_text, materials_dict)

    def _extract_material_global(self, input_text: str, materials_dict: Dict) -> str:
        """在全局文本中提取材料"""
        return self._search_material_in_text(input_text, materials_dict)

    def _search_material_in_text(self, text: str, materials_dict: Dict) -> str:
        """在指定文本中搜索材料"""
        input_text_lower = text.lower()

        # 按优先级顺序查找材料名称
        priority_materials = [
            'NCM811', 'NCA', 'LFP', 'LCO', 'LMO', 'Si/C', '石墨', '硬碳', '软碳', 'LTO',
            'NCM622', 'NCM523', 'NCM111', '三元材料', '高镍', '富锂'
        ]

        # 首先按优先级查找
        for material in priority_materials:
            if material in text:
                return material

        # 如果没找到优先级材料，则遍历所有材料类别
        for category, keywords in materials_dict.items():
            for keyword in keywords:
                if keyword.lower() in input_text_lower:
                    return keyword if not keyword.isascii() else keyword

        # 如果没有找到具体材料，返回空字符串
        return ""

    def _extract_both_materials(self, input_text: str) -> tuple:
        """同时提取正负极材料 - 改进版，支持上下文分离"""
        # 分割输入文本为句子或短语
        sentences = []
        for separator in ['，', '。', '；', ';', ',', '.', ' and ', ' 与', ' 和', ' 及']:
            if separator in input_text:
                sentences.extend(input_text.split(separator))
                break
        else:
            sentences.append(input_text)

        positive_material = ""
        negative_material = ""

        # 遍历每个句子，识别材料
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 检查句子中是否包含电极关键词
            if any(keyword in sentence for keyword in ['正极', '正极材料', '阴极', 'positive', 'cathode']):
                material = self._extract_material_name(sentence, '正极')
                if material:
                    positive_material = material

            if any(keyword in sentence for keyword in ['负极', '负极材料', '阳极', 'negative', 'anode']):
                material = self._extract_material_name(sentence, '负极')
                if material:
                    negative_material = material

        # 如果在句子中没有找到，尝试在整个文本中查找
        if not positive_material:
            positive_material = self._extract_material_name(input_text, '正极')
        if not negative_material:
            negative_material = self._extract_material_name(input_text, '负极')

        return positive_material, negative_material

    def _extract_application_scenario(self, input_text: str) -> str:
        """提取应用场景"""
        for scenario, keywords in self.application_scenarios.items():
            for keyword in keywords:
                if keyword in input_text:
                    return scenario
        return None

    def _extract_performance_requirements(self, input_text: str) -> Dict[str, Any]:
        """提取性能需求"""
        requirements = {}

        # 使用正则表达式提取数值
        for metric, keywords in self.performance_metrics.items():
            for keyword in keywords:
                # 匹配数字和单位的模式
                patterns = [
                    rf'{keyword}[:\s]*(\d+(?:\.\d+)?)\s*([a-zA-Z/°]+)',
                    rf'(\d+(?:\.\d+)?)\s*([a-zA-Z/°]+)\s*{keyword}',
                    rf'{keyword}.*?(\d+(?:\.\d+)?)',
                    rf'(\d+(?:\.\d+)?).*?{keyword}'
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, input_text, re.IGNORECASE)
                    if matches:
                        if len(matches[0]) == 2:
                            value, unit = matches[0]
                        else:
                            value = matches[0]
                            unit = self._infer_unit(metric, value)

                        requirements[metric] = {
                            'target_value': float(value),
                            'unit': unit,
                            'keyword_found': keyword
                        }
                        break

                if metric in requirements:
                    break

        # 处理相对描述（如"高能量密度"、"低成本"）
        relative_descriptions = {
            '高': 1.2,
            '中': 1.0,
            '低': 0.8,
            '优秀': 1.3,
            '良好': 1.1,
            '一般': 1.0,
            '差': 0.7
        }

        for desc, multiplier in relative_descriptions.items():
            if desc in input_text:
                # 根据应用场景设置基准值
                baseline_values = self._get_baseline_values(
                    requirements.get('application_scenario', '3C')
                )
                for metric, baseline in baseline_values.items():
                    if metric not in requirements:
                        requirements[metric] = {
                            'target_value': baseline * multiplier,
                            'unit': self.parameter_ranges[metric]['unit'],
                            'description': f'{desc}要求'
                        }
                break

        return requirements

    def _infer_unit(self, metric: str, value: str) -> str:
        """推断单位"""
        if metric in self.parameter_ranges:
            return self.parameter_ranges[metric]['unit']
        return ''

    def _get_baseline_values(self, application_scenario: str) -> Dict[str, float]:
        """获取不同应用场景的基准值"""
        baselines = {
            '蓄能': {
                '能量密度': 200,
                '功率密度': 500,
                '循环寿命': 5000,
                '工作温度': 25  # 常温
            },
            '动力': {
                '能量密度': 250,
                '功率密度': 2000,
                '循环寿命': 2000,
                '工作温度': 25
            },
            '3C': {
                '能量密度': 180,
                '功率密度': 1000,
                '循环寿命': 1000,
                '工作温度': 25
            }
        }
        return baselines.get(application_scenario, baselines['3C'])

    def _validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数范围"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        # 验证性能参数
        performance_reqs = parameters.get('performance_requirements', {})
        for metric, req_data in performance_reqs.items():
            if metric in self.parameter_ranges:
                range_info = self.parameter_ranges[metric]
                value = req_data.get('target_value')

                if value < range_info['min'] or value > range_info['max']:
                    validation_result['errors'].append(
                        f"{metric}的值{value}超出合理范围[{range_info['min']}-{range_info['max']}]"
                    )
                    validation_result['is_valid'] = False

        return validation_result

    def _generate_given_list(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成给定清单"""
        given_list = []

        # 基本参数
        if 'system_type' in parameters:
            given_list.append({
                'category': '体系参数',
                'name': '体系类型',
                'value': parameters['system_type'],
                'type': 'select',
                'required': True,
                'options': list(self.system_types.keys())
            })

        if 'application_scenario' in parameters:
            given_list.append({
                'category': '应用参数',
                'name': '应用场景',
                'value': parameters['application_scenario'],
                'type': 'select',
                'required': False,
                'options': list(self.application_scenarios.keys())
            })

        # 性能参数
        performance_reqs = parameters.get('performance_requirements', {})
        for metric, req_data in performance_reqs.items():
            param_info = {
                'category': '性能参数',
                'name': metric,
                'value': req_data.get('target_value'),
                'unit': req_data.get('unit'),
                'type': 'number',
                'required': True
            }

            if metric in self.parameter_ranges:
                range_info = self.parameter_ranges[metric]
                param_info.update({
                    'min': range_info['min'],
                    'max': range_info['max']
                })

            given_list.append(param_info)

        return given_list

    def _parse_basic_parameters(self, input_text: str, structured_params: Dict[str, Any]) -> None:
        """解析基本参数"""
        # 识别体系类型
        system_type = self._extract_system_type(input_text)
        if system_type:
            structured_params['basic_info']['system_type']['value'] = system_type
            # 动态设置label为"正极"或"负极"
            structured_params['basic_info']['system_type']['label'] = system_type
            # 提取具体材料名称
            material_name = self._extract_material_name(input_text, system_type)
            if material_name:
                structured_params['basic_info']['system_type']['material_name'] = material_name
                structured_params['basic_info']['system_type']['confidence'] = 0.95
            else:
                structured_params['basic_info']['system_type']['confidence'] = 0.9
        else:
            structured_params['metadata']['warnings'].append('未明确指定正极或负极体系')

        # 识别应用场景
        application_scenario = self._extract_application_scenario(input_text)
        if application_scenario:
            structured_params['basic_info']['application_scenario']['value'] = application_scenario
            structured_params['basic_info']['application_scenario']['confidence'] = 0.8

    def _parse_performance_parameters(self, input_text: str, structured_params: Dict[str, Any]) -> None:
        """解析性能参数"""
        # 使用正则表达式提取数值
        param_mappings = {
            'energy_density': ['能量密度', '比能量', 'energy density', 'specific energy'],
            'power_density': ['功率密度', '比功率', 'power density', 'specific power'],
            'cycle_life': ['寿命', '循环', 'lifetime', 'cycle life', 'durability'],
            'working_temperature': ['温度', '温域', 'temperature', 'thermal'],
            'safety': ['安全', 'stable', 'safety', 'stable']
        }

        for param_key, keywords in param_mappings.items():
            for keyword in keywords:
                # 匹配数字和单位的模式
                patterns = [
                    rf'{keyword}[:\s]*(\d+(?:\.\d+)?)\s*([a-zA-Z/°]+)',
                    rf'(\d+(?:\.\d+)?)\s*([a-zA-Z/°]+)\s*{keyword}',
                    rf'{keyword}.*?(\d+(?:\.\d+)?)',
                    rf'(\d+(?:\.\d+)?).*?{keyword}'
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, input_text, re.IGNORECASE)
                    if matches:
                        if len(matches[0]) == 2:
                            value, unit = matches[0]
                        else:
                            value = matches[0]
                            unit = structured_params['performance_params'][param_key]['unit']

                        structured_params['performance_params'][param_key]['value'] = float(value)
                        structured_params['performance_params'][param_key]['confidence'] = 0.85
                        break

                if structured_params['performance_params'][param_key]['value'] is not None:
                    break

        # 处理相对描述（如"高能量密度"、"低成本"）
        relative_descriptions = {
            '高': 1.2,
            '中': 1.0,
            '低': 0.8,
            '优秀': 1.3,
            '良好': 1.1,
            '一般': 1.0,
            '差': 0.7
        }

        for desc, multiplier in relative_descriptions.items():
            if desc in input_text:
                # 根据应用场景设置基准值
                application_scenario = structured_params['basic_info']['application_scenario']['value'] or '3C'
                baseline_values = self._get_baseline_values(application_scenario)

                for param_key, baseline in baseline_values.items():
                    if structured_params['performance_params'][param_key]['value'] is None:
                        structured_params['performance_params'][param_key]['value'] = baseline * multiplier
                        structured_params['performance_params'][param_key]['confidence'] = 0.6

                        # 添加描述信息
                        if param_key == 'safety':
                            # 安全性转换为1-5等级
                            safety_level = min(5, max(1, int(multiplier * 3)))
                            structured_params['performance_params'][param_key]['value'] = safety_level
                        else:
                            structured_params['performance_params'][param_key]['description'] += f'（{desc}要求）'
                break

        # 特殊处理安全性关键词
        safety_keywords = ['安全性好', '安全', '稳定', '可靠']
        for keyword in safety_keywords:
            if keyword in input_text:
                if structured_params['performance_params']['safety']['value'] is None:
                    structured_params['performance_params']['safety']['value'] = 4  # 默认高安全等级
                    structured_params['performance_params']['safety']['confidence'] = 0.7
                break

    def _calculate_overall_confidence(self, structured_params: Dict[str, Any]) -> None:
        """计算总体置信度"""
        confidences = []

        # 基本参数置信度
        for param in structured_params['basic_info'].values():
            if param['confidence'] > 0:
                confidences.append(param['confidence'])

        # 性能参数置信度
        for param in structured_params['performance_params'].values():
            if param['confidence'] > 0:
                confidences.append(param['confidence'])

        if confidences:
            structured_params['metadata']['total_confidence'] = sum(confidences) / len(confidences)
        else:
            structured_params['metadata']['total_confidence'] = 0.0

    def _validate_completeness(self, structured_params: Dict[str, Any]) -> None:
        """验证参数完整性"""
        missing_required = []

        # 检查基本参数
        for param in structured_params['basic_info'].values():
            if param['required'] and param['value'] is None:
                missing_required.append(param['label'])

        # 检查性能参数
        for param in structured_params['performance_params'].values():
            if param['required'] and param['value'] is None:
                missing_required.append(param['label'])

        structured_params['metadata']['missing_required'] = missing_required

        if missing_required:
            structured_params['metadata']['warnings'].append(f'缺少必需参数: {", ".join(missing_required)}')

    def _get_baseline_values(self, application_scenario: str) -> Dict[str, float]:
        """获取不同应用场景的基准值"""
        baselines = {
            '蓄能': {
                'energy_density': 200,
                'power_density': 500,
                'cycle_life': 5000,
                'working_temperature': 25,
                'safety': 4
            },
            '动力': {
                'energy_density': 250,
                'power_density': 2000,
                'cycle_life': 2000,
                'working_temperature': 25,
                'safety': 5
            },
            '3C': {
                'energy_density': 180,
                'power_density': 1000,
                'cycle_life': 1000,
                'working_temperature': 25,
                'safety': 3
            }
        }
        return baselines.get(application_scenario, baselines['3C'])

    def _parse_with_llm(self, natural_language_input: str) -> Dict[str, Any]:
        """使用 LLM 解析需求"""

        # 预处理输入文本
        processed_input = self._preprocess_input(natural_language_input)

        prompt = f"""
你是一个专业的电池系统需求分析专家。请分析用户的自然语言需求，提取并结构化电池相关的关键参数。

用户需求:
{natural_language_input}

解析要求:
1. 仔细分析用户描述中的正极材料和负极材料
2. 识别具体的应用场景（蓄能/动力/3C）
3. 提取具体的性能指标数值
4. 识别相对描述并转换为具体数值
5. 根据应用场景设定合理的基准值

请按照以下JSON格式返回解析结果，确保返回的是有效的JSON格式:

{{
  "basic_info": {{
    "positive_electrode": {{
      "key": "positive_electrode",
      "label": "正极材料",
      "value": "LFP、LCO、NMC811、NMC523或其他自定义材料",
      "type": "select",
      "required": false,
      "options": ["LFP", "LCO", "NMC811", "NMC523"],
      "description": "电池正极材料类型",
      "confidence": 0.9
    }},
    "negative_electrode": {{
      "key": "negative_electrode",
      "label": "负极材料",
      "value": "SiC、Li、石墨或其他自定义材料",
      "type": "select",
      "required": false,
      "options": ["SiC", "Li", "石墨"],
      "description": "电池负极材料类型",
      "confidence": 0.9
    }},
    "system_type": {{
      "key": "system_type",
      "label": "体系类型",
      "value": "正极或负极或全电池",
      "type": "select",
      "required": true,
      "options": ["正极", "负极", "全电池"],
      "description": "电池体系类型（用于向后兼容）",
      "confidence": 0.9
    }},
    "application_scenario": {{
      "key": "application_scenario",
      "label": "应用场景",
      "value": "蓄能、动力或3C",
      "type": "select",
      "required": false,
      "options": ["蓄能", "动力", "3C"],
      "description": "电池应用场景",
      "confidence": 0.8
    }}
  }},
  "performance_params": {{
    "energy_density": {{
      "key": "energy_density",
      "label": "能量密度",
      "value": 数值或null,
      "type": "number",
      "required": true,
      "unit": "Wh/kg",
      "min": 100,
      "max": 500,
      "description": "电池能量密度要求",
      "confidence": 0.85
    }},
    "power_density": {{
      "key": "power_density",
      "label": "功率密度",
      "value": 数值或null,
      "type": "number",
      "required": true,
      "unit": "W/kg",
      "min": 100,
      "max": 5000,
      "description": "电池功率密度要求",
      "confidence": 0.85
    }},
    "cycle_life": {{
      "key": "cycle_life",
      "label": "循环寿命",
      "value": 数值或null,
      "type": "number",
      "required": true,
      "unit": "cycles",
      "min": 100,
      "max": 10000,
      "description": "电池循环寿命要求",
      "confidence": 0.85
    }},
    "working_temperature": {{
      "key": "working_temperature",
      "label": "工作温度",
      "value": 数值或null,
      "type": "number",
      "required": true,
      "unit": "°C",
      "min": -40,
      "max": 80,
      "description": "电池工作温度范围",
      "confidence": 0.85
    }},
    "safety": {{
      "key": "safety",
      "label": "安全性",
      "value": 1-5的整数或null,
      "type": "rating",
      "required": true,
      "unit": "level",
      "min": 1,
      "max": 5,
      "description": "电池安全等级要求",
      "confidence": 0.85
    }}
  }},
  "metadata": {{
    "original_input": "{natural_language_input}",
        "parsing_timestamp": {{"timestamp": "2025-10-{__import__('random').randint(1,31):02d}T{__import__('random').randint(0,23):02d}:{__import__('random').randint(0,59):02d}:{__import__('random').randint(0,59):02d}"}},
    "total_confidence": 0.85,
    "missing_required": [],
    "warnings": []
  }}
}}

解析指南:
1. 正负极材料识别（重要）:
   - 正极材料识别（优先选择预定义选项）：
     * LFP（磷酸铁锂）: 用户提到LFP、磷酸铁锂、LiFePO4
     * LCO（钴酸锂）: 用户提到LCO、钴酸锂、LiCoO2
     * NMC811（高镍三元）: 用户提到NCM811、高镍三元、811
     * NMC523（中镍三元）: 用户提到NCM523、523、中镍三元
     * 其他正极材料: NCA、LMO、NCM622、NCM111等，提取为用户自定义输入
   - 负极材料识别（优先选择预定义选项）：
     * SiC（硅碳）: 用户提到SiC、硅碳、硅碳复合、Si/C
     * Li（金属锂）: 用户提到Li、金属锂、锂金属
     * 石墨: 用户提到石墨、天然石墨、人造石墨
     * 其他负极材料: 硬碳、软碳、LTO、钛酸锂等，提取为用户自定义输入
   - 如果用户同时提到正极和负极材料，请分别填写到positive_electrode和negative_electrode字段
   - 如果用户只提到一种材料，根据材料类型判断是正极还是负极
   - system_type字段：根据识别到的材料自动设置（只有正极则填"正极"，只有负极则填"负极"，都有则填"全电池"）

2. 应用场景识别:
   - 蓄能: 提到储能电站、电网储能、蓄能、energy storage等
   - 动力: 提到电动汽车、动力电池、汽车、EV、vehicle等
   - 3C: 提到手机、电脑、消费电子、3C产品、mobile等

3. 性能参数数值设定:
   - 能量密度: 蓄能200-250Wh/kg, 动力250-300Wh/kg, 3C180-220Wh/kg
   - 功率密度: 蓄能500-800W/kg, 动力2000-3000W/kg, 3C1000-1500W/kg
   - 循环寿命: 蓄能4000-6000次, 动力1500-2500次, 3C800-1500次
   - 工作温度: 一般-20到60°C，特殊需求可调整
   - 安全性: 1-5级，一般应用3级，高要求4-5级

4. 相对描述转换:
   - "高"/"优秀"/"很好": +20%
   - "中"/"一般"/"正常": 基准值
   - "低"/"差": -20%

5. 置信度评估:
   - 明确数值: 0.9-1.0
   - 相对描述: 0.7-0.8
   - 推断得出: 0.5-0.6

请确保返回的是有效的JSON格式，不要包含任何markdown标记或额外文本。
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful battery system requirement analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=130  # 30秒超时
            )

            raw_output = response.choices[0].message.content
            logger.info(f"LLM 原始输出: {raw_output}")

            # 清理和解析JSON
            cleaned_json = self._clean_json_text(raw_output)

        except Exception as api_error:
            logger.error(f"LLM API调用失败: {str(api_error)}")
            raise Exception(f"网络连接失败或API服务不可用: {str(api_error)}")
        try:
            structured_params = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.error(f"清理后的JSON文本: {cleaned_json}")
            # 当JSON解析失败时，使用fallback结构
            structured_params = self._get_fallback_response(input_text)

        # 更新时间戳
        structured_params['metadata']['parsing_timestamp'] = json.dumps(
            {'timestamp': __import__('datetime').datetime.now().isoformat()},
            ensure_ascii=False
        )

        # 计算实际置信度
        self._calculate_overall_confidence(structured_params)
        self._validate_completeness(structured_params)

        return structured_params

    def _parse_with_rules(self, natural_language_input: str) -> Dict[str, Any]:
        """使用规则解析需求（备选方案）"""
        # 转换为小写以便匹配
        input_lower = natural_language_input.lower()

        # 初始化结构化参数对象
        structured_params = {
            'basic_info': {
                'system_type': {
                    'key': 'system_type',
                    'label': '体系类型',
                    'value': None,
                    'type': 'select',
                    'required': True,
                    'options': ['正极', '负极'],
                    'description': '电池体系类型',
                    'confidence': 0.0
                },
                'application_scenario': {
                    'key': 'application_scenario',
                    'label': '应用场景',
                    'value': None,
                    'type': 'select',
                    'required': False,
                    'options': ['蓄能', '动力', '3C'],
                    'description': '电池应用场景',
                    'confidence': 0.0
                }
            },
            'performance_params': {
                'energy_density': {
                    'key': 'energy_density',
                    'label': '能量密度',
                    'value': None,
                    'type': 'number',
                    'required': True,
                    'unit': 'Wh/kg',
                    'min': 100,
                    'max': 500,
                    'description': '电池能量密度要求',
                    'confidence': 0.0
                },
                'power_density': {
                    'key': 'power_density',
                    'label': '功率密度',
                    'value': None,
                    'type': 'number',
                    'required': True,
                    'unit': 'W/kg',
                    'min': 100,
                    'max': 5000,
                    'description': '电池功率密度要求',
                    'confidence': 0.0
                },
                'cycle_life': {
                    'key': 'cycle_life',
                    'label': '循环寿命',
                    'value': None,
                    'type': 'number',
                    'required': True,
                    'unit': 'cycles',
                    'min': 100,
                    'max': 10000,
                    'description': '电池循环寿命要求',
                    'confidence': 0.0
                },
                'working_temperature': {
                    'key': 'working_temperature',
                    'label': '工作温度',
                    'value': None,
                    'type': 'number',
                    'required': True,
                    'unit': '°C',
                    'min': -40,
                    'max': 80,
                    'description': '电池工作温度范围',
                    'confidence': 0.0
                },
                'safety': {
                    'key': 'safety',
                    'label': '安全性',
                    'value': None,
                    'type': 'rating',
                    'required': True,
                    'unit': 'level',
                    'min': 1,
                    'max': 5,
                    'description': '电池安全等级要求',
                    'confidence': 0.0
                }
            },
            'metadata': {
                'original_input': natural_language_input,
                'parsing_timestamp': json.dumps({'timestamp': __import__('datetime').datetime.now().isoformat()}, ensure_ascii=False),
                'total_confidence': 0.0,
                'missing_required': [],
                'warnings': ['使用规则解析方法，准确性可能较低']
            }
        }

        # 1. 解析基本参数
        self._parse_basic_parameters(input_lower, structured_params)

        # 2. 解析性能参数
        self._parse_performance_parameters(natural_language_input, structured_params)

        # 3. 计算总体置信度
        self._calculate_overall_confidence(structured_params)

        # 4. 验证参数完整性
        self._validate_completeness(structured_params)

        return structured_params

    def _clean_json_text(self, text: str) -> str:
        """清理 LLM 输出的 JSON 文本"""
        if not text:
            raise ValueError("输入文本为空")

        # 更彻底的清理：移除所有前导和尾随空白字符，包括换行符
        text = text.strip()

        # 如果开头仍然有换行符或其他空白字符，再次清理
        while text and (text.startswith('\n') or text.startswith('\r') or text.startswith(' ') or text.startswith('\t')):
            text = text[1:].strip()

        # 去掉 Markdown 代码块标记
        text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^```', '', text)
        text = re.sub(r'```$', '', text)

        # 提取 JSON 主体 - 使用更宽松的正则表达式
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if not json_match:
            raise ValueError("文本中未找到 JSON 部分")
        json_text = json_match.group(0)

        # 修复全角引号和其他常见问题
        json_text = json_text.replace(""", '"').replace(""", '"').replace("'", "'").replace("'", "'")
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)  # 移除末尾多余的逗号

        return json_text

    def _get_fallback_response(self, input_text: str) -> Dict[str, Any]:
        """当API解析失败时使用的fallback响应"""
        logger.info(f"使用fallback响应解析: {input_text}")

        # 基于输入文本的简单规则解析
        system_type = self._identify_system_type(input_text) or '电解液'
        application_scenario = self._identify_application_scenario(input_text) or '动力电池'

        return {
            "basic_info": {
                "system_type": {
                    "key": "system_type",
                    "label": "体系类型",
                    "value": system_type,
                    "type": "select",
                    "required": True,
                    "options": ["正极", "负极", "电解液", "全电池"],
                    "description": "电池体系类型",
                    "confidence": 0.7,
                    "material_name": "",
                    "both_materials": {
                        "positive": "",
                        "negative": ""
                    }
                },
                "application_scenario": {
                    "key": "application_scenario",
                    "label": "应用场景",
                    "value": application_scenario,
                    "type": "select",
                    "required": True,
                    "options": ["3C", "动力电池", "储能"],
                    "description": "电池应用场景",
                    "confidence": 0.7
                }
            },
            "performance_params": self._get_default_performance_params(application_scenario),
            "metadata": {
                "original_input": input_text,
                "parsing_timestamp": json.dumps(
                    {'timestamp': __import__('datetime').datetime.now().isoformat()},
                    ensure_ascii=False
                ),
                "total_confidence": 0.7,
                "missing_required": [],
                "warnings": ["使用fallback解析，建议配置有效的API密钥以获得更准确的结果"],
                "consistency_issues": [],
                "suggestions": [],
                "post_processing_applied": False,
                "validation_result": {
                    "errors": [],
                    "is_valid": True,
                    "warnings": ["Fallback解析结果"]
                }
            }
        }

    def _get_default_performance_params(self, application_scenario: str) -> Dict[str, Any]:
        """获取默认性能参数"""
        baselines = {
            '3C': {
                'energy_density': {'value': 220, 'confidence': 0.6},
                'power_density': {'value': 1800, 'confidence': 0.6},
                'cycle_life': {'value': 1200, 'confidence': 0.6},
                'working_temperature': {'value': 15, 'confidence': 0.6},
                'safety': {'value': 3, 'confidence': 0.6}
            },
            '动力电池': {
                'energy_density': {'value': 280, 'confidence': 0.6},
                'power_density': {'value': 2500, 'confidence': 0.6},
                'cycle_life': {'value': 2000, 'confidence': 0.6},
                'working_temperature': {'value': -10, 'confidence': 0.6},
                'safety': {'value': 4, 'confidence': 0.6}
            },
            '储能': {
                'energy_density': {'value': 200, 'confidence': 0.6},
                'power_density': {'value': 800, 'confidence': 0.6},
                'cycle_life': {'value': 5000, 'confidence': 0.6},
                'working_temperature': {'value': 25, 'confidence': 0.6},
                'safety': {'value': 4, 'confidence': 0.6}
            }
        }

        default_params = baselines.get(application_scenario, baselines['动力电池'])

        return {
            "energy_density": {
                "key": "energy_density",
                "label": "能量密度",
                "value": default_params['energy_density']['value'],
                "type": "number",
                "required": True,
                "unit": "Wh/kg",
                "min": 100,
                "max": 500,
                "description": "电池能量密度要求",
                "confidence": default_params['energy_density']['confidence']
            },
            "power_density": {
                "key": "power_density",
                "label": "功率密度",
                "value": default_params['power_density']['value'],
                "type": "number",
                "required": True,
                "unit": "W/kg",
                "min": 100,
                "max": 5000,
                "description": "电池功率密度要求",
                "confidence": default_params['power_density']['confidence']
            },
            "cycle_life": {
                "key": "cycle_life",
                "label": "循环寿命",
                "value": default_params['cycle_life']['value'],
                "type": "number",
                "required": True,
                "unit": "cycles",
                "min": 100,
                "max": 10000,
                "description": "电池循环寿命要求",
                "confidence": default_params['cycle_life']['confidence']
            },
            "working_temperature": {
                "key": "working_temperature",
                "label": "工作温度",
                "value": default_params['working_temperature']['value'],
                "type": "number",
                "required": True,
                "unit": "°C",
                "min": -40,
                "max": 80,
                "description": "电池工作温度范围",
                "confidence": default_params['working_temperature']['confidence']
            },
            "safety": {
                "key": "safety",
                "label": "安全性",
                "value": default_params['safety']['value'],
                "type": "rating",
                "required": True,
                "unit": "level",
                "min": 1,
                "max": 5,
                "description": "电池安全等级要求",
                "confidence": default_params['safety']['confidence']
            }
        }

    def _preprocess_input(self, input_text: str) -> str:
        """预处理用户输入，标准化表达"""
        if not input_text:
            return input_text

        # 转换为小写以便匹配
        processed = input_text.lower()

        # 标准化同义词和缩写
        synonym_mappings = {
            # 体系类型相关
            '正极材料': '正极',
            '阴极': '正极',
            'cathode': '正极',
            '负极材料': '负极',
            '阳极': '负极',
            'anode': '负极',
            '石墨': '负极',
            '硅基': '负极',

            # 应用场景相关
            '储能电站': '蓄能',
            '电网储能': '蓄能',
            'energy storage': '蓄能',
            '电动汽车': '动力',
            '电动车': '动力',
            'ev': '动力',
            'vehicle': '动力',
            '汽车': '动力',
            '手机': '3c',
            '电脑': '3c',
            '消费电子': '3c',
            'mobile': '3c',
            'laptop': '3c',

            # 性能描述相关
            '能量': '能量密度',
            '比能量': '能量密度',
            'power': '功率密度',
            '比功率': '功率密度',
            '寿命': '循环寿命',
            '循环次数': '循环寿命',
            'cycle life': '循环寿命',
            'durability': '循环寿命',
            '温度': '工作温度',
            '温域': '工作温度',
            'thermal': '工作温度',
            '安全': '安全性',
            'stable': '安全性',
            'safety': '安全性',

            # 强度描述词
            '非常好': '优秀',
            '很棒': '优秀',
            '出色': '优秀',
            '挺好': '良好',
            '不错': '良好',
            '一般般': '一般',
            '普通': '一般',
            '比较差': '差',
            '不好': '差',
            '很低': '差'
        }

        # 应用同义词替换
        for old_term, new_term in synonym_mappings.items():
            processed = processed.replace(old_term, new_term)

        # 标准化单位和数值表达
        unit_patterns = [
            (r'(\d+)\s*wh/kg', r'\1 Wh/kg 能量密度'),
            (r'(\d+)\s*w/kg', r'\1 W/kg 功率密度'),
            (r'(\d+)\s*次循环', r'\1 cycles 循环寿命'),
            (r'(\d+)\s*次', r'\1 cycles 循环寿命'),
            (r'(\d+)\s*°c', r'\1 °C 工作温度'),
            (r'(\d+)\s*度', r'\1 °C 工作温度')
        ]

        for pattern, replacement in unit_patterns:
            processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

        return processed.strip()

    def _enhanced_rule_parsing(self, input_text: str) -> Dict[str, Any]:
        """增强的规则解析"""
        # 使用预处理后的输入
        processed_input = self._preprocess_input(input_text)

        # 调用原有的规则解析方法
        result = self._parse_with_rules(input_text)

        # 进一步优化解析结果
        self._enhance_parsing_result(result, processed_input)

        # 应用后处理优化
        result = self._post_process_optimization(result, input_text)

        return result

    def _enhance_parsing_result(self, result: Dict[str, Any], processed_input: str) -> None:
        """优化解析结果 - 改进版，优先处理双材料情况"""
        # 1. 优先检查是否同时提到了正负极材料
        positive_material, negative_material = self._extract_both_materials(processed_input)

        if positive_material and negative_material:
            # 如果同时识别到了正负极材料，创建全电池系统记录
            result['basic_info']['system_type']['both_materials'] = {
                'positive': positive_material,
                'negative': negative_material
            }
            result['basic_info']['system_type']['label'] = '全电池系统'
            result['basic_info']['system_type']['value'] = '全电池'
            result['basic_info']['system_type']['confidence'] = 0.98
        else:
            # 2. 如果没有同时识别到两种材料，检查体系类型
            system_type = result['basic_info']['system_type']['value']
            if system_type is None:
                system_type = self._extract_system_type_enhanced(processed_input)
                if system_type:
                    result['basic_info']['system_type']['value'] = system_type

            # 如果有体系类型，动态设置label并提取材料名称
            if system_type:
                # 动态设置label为"正极"或"负极"
                result['basic_info']['system_type']['label'] = system_type
                # 提取具体材料名称
                material_name = self._extract_material_name(processed_input, system_type)
                if material_name:
                    result['basic_info']['system_type']['material_name'] = material_name
                    # 如果原来没有设置置信度或者置信度较低，则提升置信度
                    if not result['basic_info']['system_type'].get('confidence') or result['basic_info']['system_type']['confidence'] < 0.85:
                        result['basic_info']['system_type']['confidence'] = 0.95

        # 改进应用场景判断
        if result['basic_info']['application_scenario']['value'] is None:
            scenario = self._extract_application_scenario_enhanced(processed_input)
            if scenario:
                result['basic_info']['application_scenario']['value'] = scenario
                result['basic_info']['application_scenario']['confidence'] = 0.8

        # 改进性能参数解析
        self._enhance_performance_parsing(result, processed_input)

    def _extract_system_type_enhanced(self, processed_input: str) -> str:
        """增强的体系类型提取"""
        # 更精确的关键词匹配
        positive_indicators = ['ncm', 'lfp', 'lco', 'nca', '正极', 'cathode']
        negative_indicators = ['石墨', '硅', '负极', 'anode']

        positive_score = sum(1 for indicator in positive_indicators if indicator in processed_input)
        negative_score = sum(1 for indicator in negative_indicators if indicator in processed_input)

        if positive_score > negative_score:
            return '正极'
        elif negative_score > positive_score:
            return '负极'

        return None

    def _extract_application_scenario_enhanced(self, processed_input: str) -> str:
        """增强的应用场景提取"""
        scenario_keywords = {
            '蓄能': ['蓄能', '储能', 'storage', '电站', '电网'],
            '动力': ['动力', '汽车', 'ev', 'vehicle', '电动车'],
            '3c': ['3c', '手机', '电脑', 'mobile', 'laptop', '消费电子']
        }

        for scenario, keywords in scenario_keywords.items():
            if any(keyword in processed_input for keyword in keywords):
                return scenario

        return None

    def _enhance_performance_parsing(self, result: Dict[str, Any], processed_input: str) -> None:
        """增强的性能参数解析"""
        # 改进的相对描述解析
        intensity_mapping = {
            '优秀': 1.3,
            '良好': 1.15,
            '高': 1.2,
            '一般': 1.0,
            '中': 1.0,
            '低': 0.8,
            '差': 0.7
        }

        # 检查强度描述词
        for intensity, multiplier in intensity_mapping.items():
            if intensity in processed_input:
                # 获取应用场景
                scenario = result['basic_info']['application_scenario']['value'] or '3C'
                baselines = self._get_baseline_values(scenario)

                # 参数键名映射（中文到英文）
                key_mapping = {
                    'energy_density': '能量密度',
                    'power_density': '功率密度',
                    'cycle_life': '循环寿命',
                    'working_temperature': '工作温度',
                    'safety': '安全性'
                }

                # 调整未设置的性能参数
                for eng_key, baseline_value in baselines.items():
                    chi_key = key_mapping.get(eng_key, eng_key)
                    if chi_key in result['performance_params']:
                        param = result['performance_params'][chi_key]
                        if param['value'] is None:
                            if eng_key == 'safety':
                                # 安全性特殊处理
                                safety_level = min(5, max(1, int(3 * multiplier)))
                                param['value'] = safety_level
                                param['confidence'] = 0.7
                            else:
                                param['value'] = baseline_value * multiplier
                                param['confidence'] = 0.75
                break

    def _post_process_optimization(self, result: Dict[str, Any], original_input: str) -> Dict[str, Any]:
        """后处理优化：参数验证、一致性检查和结果优化"""

        if not result:
            return result

        # 1. 参数范围验证和修正
        validation_result = self._validate_parameters(result)
        if not validation_result['is_valid']:
            logger.warning(f"参数验证失败: {validation_result['errors']}")

        # 2. 逻辑一致性检查
        consistency_issues = []

        # 检查体系类型和应用场景的匹配性
        system_type = result.get('basic_info', {}).get('system_type', {}).get('value')
        application = result.get('basic_info', {}).get('application_scenario', {}).get('value')

        if system_type and application:
            # 特定组合的一致性检查
            if system_type == '正极' and application == '3C':
                energy_density = result.get('performance_params', {}).get('energy_density', {}).get('value')
                if energy_density and energy_density < 150:
                    consistency_issues.append("3C应用的正极材料能量密度偏低，建议检查")

            if system_type == '负极' and application == '蓄能':
                cycle_life = result.get('performance_params', {}).get('cycle_life', {}).get('value')
                if cycle_life and cycle_life < 3000:
                    consistency_issues.append("蓄能应用的负极材料循环寿命偏低，建议检查")

        # 3. 置信度评估和调整
        total_confidence = 0.0
        param_count = 0

        # 基础信息置信度
        for key, param in result.get('basic_info', {}).items():
            if isinstance(param, dict) and 'confidence' in param:
                total_confidence += param['confidence']
                param_count += 1

        # 性能参数置信度
        for key, param in result.get('performance_params', {}).items():
            if isinstance(param, dict) and 'confidence' in param:
                # 根据参数合理性调整置信度
                value = param.get('value')
                if value is not None:
                    # 检查数值是否在合理范围内
                    if key in self.parameter_ranges:
                        min_val = self.parameter_ranges[key]['min']
                        max_val = self.parameter_ranges[key]['max']
                        if min_val <= value <= max_val:
                            param['confidence'] = min(1.0, param['confidence'] + 0.1)
                        else:
                            param['confidence'] = max(0.3, param['confidence'] - 0.2)
                            consistency_issues.append(f"参数{key}的数值{value}可能超出合理范围[{min_val}, {max_val}]")

                total_confidence += param['confidence']
                param_count += 1


        # 5. 更新元数据
        if 'metadata' not in result:
            result['metadata'] = {}

        result['metadata'].update({
            'validation_result': validation_result,
            'consistency_issues': consistency_issues,
            'post_processing_applied': True,
            'optimization_timestamp': __import__('datetime').datetime.now().isoformat()
        })

        # 计算总置信度
        if param_count > 0:
            avg_confidence = total_confidence / param_count
            result['metadata']['total_confidence'] = round(avg_confidence, 3)

        # 6. 智能建议生成
        suggestions = []

        if consistency_issues:
            suggestions.extend(consistency_issues)

        # 基于置信度给出建议
        avg_confidence = result['metadata'].get('total_confidence', 0)
        if avg_confidence < 0.7:
            suggestions.append("解析置信度较低，建议提供更具体的技术指标")

        # 基于参数组合给出优化建议
        if system_type == '正极' and application == '动力':
            energy_density = result.get('performance_params', {}).get('energy_density', {}).get('value')
            if energy_density and energy_density < 220:
                suggestions.append("动力电池正极材料建议提高能量密度至220Wh/kg以上")

        result['metadata']['suggestions'] = suggestions

        logger.info(f"后处理优化完成，置信度: {avg_confidence:.3f}, 建议: {len(suggestions)}条")
        return result

    def _parse_with_rules(self, natural_language_input: str) -> Dict[str, Any]:
        """使用规则解析需求（备选方案）"""
        # 转换为小写以便匹配
        input_lower = natural_language_input.lower()

        # 初始化结构化参数对象
        structured_params = {
            'basic_info': {
                'system_type': {
                    'key': 'system_type',
                    'label': '体系类型',
                    'value': None,
                    'type': 'select',
                    'required': True,
                    'options': ['正极', '负极'],
                    'description': '电池体系类型',
                    'confidence': 0.0
                },
                'application_scenario': {
                    'key': 'application_scenario',
                    'label': '应用场景',
                    'value': None,
                    'type': 'select',
                    'required': False,
                    'options': ['蓄能', '动力', '3C'],
                    'description': '电池应用场景',
                    'confidence': 0.0
                }
            },
            'performance_params': {},
            'metadata': {
                'original_input': natural_language_input,
                'parsing_timestamp': __import__('datetime').datetime.now().isoformat(),
                'total_confidence': 0.0,
                'missing_required': [],
                'warnings': []
            }
        }

        # 提取体系类型
        system_type = self._extract_system_type(natural_language_input)
        if system_type:
            structured_params['basic_info']['system_type']['value'] = system_type
            # 动态设置label为"正极"或"负极"
            structured_params['basic_info']['system_type']['label'] = system_type
            # 提取具体材料名称
            material_name = self._extract_material_name(natural_language_input, system_type)
            if material_name:
                structured_params['basic_info']['system_type']['material_name'] = material_name
                structured_params['basic_info']['system_type']['confidence'] = 0.95
            else:
                structured_params['basic_info']['system_type']['confidence'] = 0.9

        # 提取应用场景
        structured_params['basic_info']['application_scenario']['value'] = self._extract_application_scenario(natural_language_input)

        # 提取性能要求
        structured_params['performance_params'] = self._extract_performance_requirements(natural_language_input)

        return structured_params
