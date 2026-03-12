import os
import re
import json
import logging
import tempfile
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

# 尝试导入PyMuPDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. PDF processing will be limited.")

# 尝试导入其他PDF处理库作为备选
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

class PDFProcessor:
    """PDF文档处理器，整合SPARK的PDF处理能力"""

    def __init__(self, spark_path: str = None):
        self.spark_path = spark_path or os.path.join(os.path.dirname(__file__), '../../../../SPARK-master-20250803')
        self.processed_count = 0

        # 电解质相关关键词
        self.electrolyte_keywords = {
            'salts': ['LiTFSI', 'LiFSI', 'LiPF6', 'LiBF4', 'LiClO4', 'LiBOB', 'LiDFOB'],
            'solvents': ['EC', 'DMC', 'DEC', 'EMC', 'PC', 'DME', 'THF', 'ACN', 'FEC', 'VC'],
            'additives': ['FEC', 'VC', 'VEC', 'ES', 'DTD', 'LiNO3', 'LiPO2F2'],
            'polymers': ['PEO', 'PVDF', 'PVDF-HFP', 'PAN', 'PMMA', 'PEO', 'PPO'],
            'properties': ['ionic conductivity', 'viscosity', 'dielectric constant', 'LUMO', 'HOMO',
                          'melting point', 'boiling point', 'flash point', 'electrochemical window'],
            'performance': ['energy density', 'coulombic efficiency', 'capacity retention', 'cycle life']
        }

    def process_pdf(self, pdf_path: str, extract_chemical_info: bool = True) -> Dict:
        """
        处理PDF文件，提取文本和化学信息

        Args:
            pdf_path: PDF文件路径
            extract_chemical_info: 是否提取化学信息

        Returns:
            处理结果字典
        """
        try:
            # 基本文本提取
            text_content = self._extract_text_from_pdf(pdf_path)
            if not text_content:
                raise ValueError("无法从PDF中提取文本内容")

            # 清理文本
            cleaned_text = self._clean_text(text_content)

            # 提取元数据
            metadata = self._extract_metadata(pdf_path, cleaned_text)

            result = {
                'pdf_path': pdf_path,
                'text_content': cleaned_text,
                'metadata': metadata,
                'processed_at': datetime.now().isoformat(),
                'text_length': len(cleaned_text)
            }

            if extract_chemical_info:
                # 提取化学信息
                chemical_info = self._extract_chemical_information(cleaned_text)
                result.update(chemical_info)

            self.processed_count += 1
            logger.info(f"Successfully processed PDF: {pdf_path}")

            return result

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'processed_at': datetime.now().isoformat(),
                'status': 'failed'
            }

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF提取文本"""
        try:
            if PYMUPDF_AVAILABLE:
                return self._extract_text_with_pymupdf(pdf_path)
            elif PYPDF2_AVAILABLE:
                return self._extract_text_with_pypdf2(pdf_path)
            else:
                logger.error("No PDF processing library available")
                return ""

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def _extract_text_with_pymupdf(self, pdf_path: str) -> str:
        """使用PyMuPDF提取文本"""
        try:
            doc = fitz.open(pdf_path)
            text_content = ""

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                text_content += text + "\n"

            doc.close()
            return text_content

        except Exception as e:
            logger.error(f"Error extracting text with PyMuPDF: {e}")
            return ""

    def _extract_text_with_pypdf2(self, pdf_path: str) -> str:
        """使用PyPDF2提取文本（备选方案）"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            text_content = ""

            for page in reader.pages:
                text_content += page.extract_text() + "\n"

            return text_content

        except Exception as e:
            logger.error(f"Error extracting text with PyPDF2: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """清理提取的文本"""
        try:
            # 移除页眉页脚
            text = re.sub(r'\n\s*\d+\s*\n', '\n', text)  # 页码
            text = re.sub(r'\n.*?Page \d+.*?\n', '\n', text)  # 页码标记

            # 移除参考文献部分
            text = re.sub(r'\nReferences.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'\nBibliography.*$', '', text, flags=re.IGNORECASE | re.DOTALL)

            # 清理多余的空白字符
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n', text)

            # 移除特殊字符
            text = re.sub(r'[^\w\s\-\.,;:()\/\[\]%\&\+\=\#]', '', text)

            return text.strip()

        except Exception as e:
            logger.warning(f"Error cleaning text: {e}")
            return text

    def _extract_metadata(self, pdf_path: str, text: str) -> Dict:
        """提取文档元数据"""
        metadata = {}

        try:
            # 从文本中提取标题（通常是第一行或几行）
            lines = text.split('\n')
            if lines:
                # 简单启发式：第一行非空文本作为标题
                for line in lines[:5]:
                    line = line.strip()
                    if len(line) > 10 and len(line) < 200:
                        metadata['title'] = line
                        break

            # 提取作者信息
            author_patterns = [
                r'([A-Z][a-z]+ [A-Z][a-z]+)',  # 姓名模式
                r'([A-Z]\. [A-Z][a-z]+)',      # 缩写名模式
            ]

            authors = []
            for pattern in author_patterns:
                matches = re.findall(pattern, text[:1000])  # 只在前1000字符中查找
                authors.extend(matches)

            if authors:
                metadata['authors'] = ', '.join(authors[:5])  # 最多取5个作者

            # 提取发表年份
            year_pattern = r'\b(19|20)\d{2}\b'
            years = re.findall(year_pattern, text[:2000])
            if years:
                metadata['publication_year'] = int(years[0])

            # 提取期刊信息
            journal_patterns = [
                r'Journal of [\w\s]+',
                r'[\w\s]+ Journal',
                r'Nature',
                r'Science',
                r'Advanced Materials',
                r'Energy & Environmental Science',
                r'Journal of Power Sources',
                r'Electrochimica Acta'
            ]

            for pattern in journal_patterns:
                match = re.search(pattern, text[:3000], re.IGNORECASE)
                if match:
                    metadata['journal'] = match.group()
                    break

            # 提取DOI
            doi_pattern = r'(?:doi:|DOI:)?\s*(10\.\d+/[^\s]+)'
            doi_match = re.search(doi_pattern, text, re.IGNORECASE)
            if doi_match:
                metadata['doi'] = doi_match.group(1)

            # 提取关键词
            keywords = self._extract_keywords(text)
            if keywords:
                metadata['keywords'] = keywords

            # 提取摘要
            abstract = self._extract_abstract(text)
            if abstract:
                metadata['abstract'] = abstract

        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")

        return metadata

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []

        # 常见的关键词模式
        keyword_patterns = [
            r'Keywords?:\s*([^\n]+)',
            r'Key words?:\s*([^\n]+)',
            r'Index terms?:\s*([^\n]+)'
        ]

        for pattern in keyword_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                keyword_text = match.group(1)
                # 分割关键词
                kw_list = [kw.strip().strip(';,') for kw in keyword_text.split(',')]
                keywords.extend(kw_list)
                break

        # 如果没有找到关键词标记，尝试从开头部分提取
        if not keywords:
            first_part = text[:2000]
            # 查找大写字母开头的专业术语
            technical_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', first_part)
            # 过滤掉常见的非关键词
            exclude_terms = {'The', 'This', 'These', 'Those', 'However', 'Therefore', 'Moreover'}
            technical_terms = [term for term in technical_terms if term not in exclude_terms and len(term) > 3]
            keywords.extend(technical_terms[:5])

        return keywords[:10]  # 最多返回10个关键词

    def _extract_abstract(self, text: str) -> Optional[str]:
        """提取摘要"""
        abstract_patterns = [
            r'Abstract[:\s]*\n?(.*?)(?:\n\s*\n|\nKeywords?|\n1\. |\nI\. )',
            r'ABSTRACT[:\s]*\n?(.*?)(?:\n\s*\n|\nKEYWORDS?|\n1\. |\nI\. )',
        ]

        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # 清理摘要
                abstract = re.sub(r'\s+', ' ', abstract)
                if len(abstract) > 50 and len(abstract) < 2000:  # 合理的摘要长度
                    return abstract

        return None

    def _extract_chemical_information(self, text: str) -> Dict:
        """提取化学信息"""
        chemical_info = {
            'formulas': [],
            'molecules': [],
            'properties': [],
            'electrolyte_systems': []
        }

        try:
            # 提取分子式
            chemical_formulas = self._extract_chemical_formulas(text)
            chemical_info['formulas'] = chemical_formulas

            # 提取电解质组分
            electrolyte_components = self._extract_electrolyte_components(text)
            chemical_info['molecules'] = electrolyte_components

            # 提取性能数据
            performance_data = self._extract_performance_data(text)
            chemical_info['properties'] = performance_data

            # 提取电解质系统
            electrolyte_systems = self._extract_electrolyte_systems(text)
            chemical_info['electrolyte_systems'] = electrolyte_systems

        except Exception as e:
            logger.warning(f"Error extracting chemical information: {e}")

        return chemical_info

    def _extract_chemical_formulas(self, text: str) -> List[Dict]:
        """提取化学式"""
        formulas = []

        # 化学式模式：元素+数字
        formula_pattern = r'\b[A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?\d+)*\b'

        # 更精确的化学式模式
        complex_formula_pattern = r'\b(?:[A-Z][a-z]?\d*)+(?:\([A-Za-z\d]+\)\d*)?\b'

        # 常见电解质分子式
        known_formulas = {
            'LiTFSI': 'C2F6NO4S2Li',
            'LiFSI': 'F6NO2S2Li',
            'LiPF6': 'F6PLi',
            'EC': 'C3H4O3',
            'DMC': 'C3H6O3',
            'DEC': 'C5H10O3',
            'EMC': 'C4H8O3',
            'PC': 'C4H6O3'
        }

        # 查找已知分子式
        for name, formula in known_formulas.items():
            if name in text:
                formulas.append({
                    'name': name,
                    'formula': formula,
                    'type': 'known_compound',
                    'context': self._get_context(text, name)
                })

        # 查找一般化学式
        matches = re.findall(complex_formula_pattern, text)
        for match in matches:
            if self._is_valid_chemical_formula(match):
                formulas.append({
                    'formula': match,
                    'type': 'extracted_formula',
                    'context': self._get_context(text, match)
                })

        return formulas

    def _extract_electrolyte_components(self, text: str) -> List[Dict]:
        """提取电解质组分"""
        components = []

        # 检查各类电解质组分
        for category, compounds in self.electrolyte_keywords.items():
            for compound in compounds:
                if compound in text:
                    # 提取包含该化合物的句子或段落
                    context = self._get_context(text, compound)

                    # 尝试提取浓度信息
                    concentration = self._extract_concentration(context, compound)

                    components.append({
                        'name': compound,
                        'category': category.rstrip('s'),  # 移除复数形式
                        'concentration': concentration,
                        'context': context,
                        'confidence': self._calculate_confidence(compound, context)
                    })

        return components

    def _extract_performance_data(self, text: str) -> List[Dict]:
        """提取性能数据"""
        performance_data = []

        # 性能指标模式
        performance_patterns = {
            'ionic_conductivity': r'ionic conductivity[:\s]*([0-9.]+)\s*([a-zA-Z/]+)',
            'viscosity': r'viscosity[:\s]*([0-9.]+)\s*([a-zA-Z/]+)',
            'dielectric_constant': r'dielectric constant[:\s]*([0-9.]+)',
            'energy_density': r'energy density[:\s]*([0-9.]+)\s*([a-zA-Z/]+)',
            'coulombic_efficiency': r'coulombic efficiency[:\s]*([0-9.]+)%?',
            'capacity_retention': r'capacity retention[:\s]*([0-9.]+)%?',
            'cycle_life': r'cycle life[:\s]*([0-9.]+)',
        }

        for property_name, pattern in performance_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                unit = match.group(2) if len(match.groups()) > 1 else ''

                # 安全的float转换
                try:
                    numeric_value = float(value)
                except ValueError:
                    logger.warning(f"Could not convert value '{value}' to float for property {property_name}")
                    continue

                performance_data.append({
                    'property': property_name,
                    'value': numeric_value,
                    'unit': unit,
                    'context': self._get_context(text, match.group(0)),
                    'confidence': 0.8  # 默认置信度
                })

        return performance_data

    def _extract_electrolyte_systems(self, text: str) -> List[Dict]:
        """提取电解质系统"""
        systems = []

        # 电解质系统模式
        system_patterns = [
            r'(\w+\s+electrolyte)',
            r'(\w+\s+based\s+electrolyte)',
            r'(high\s+concentration\s+electrolyte)',
            r'(localized\s+high\s+concentration\s+electrolyte)',
            r'(\w+\s+solvent\s+electrolyte)',
        ]

        for pattern in system_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                system_name = match.group(1)
                context = self._get_context(text, match.group(0))

                # 尝试提取系统组分
                components = self._extract_system_components(context)

                systems.append({
                    'name': system_name,
                    'type': 'electrolyte_system',
                    'components': components,
                    'context': context,
                    'confidence': self._calculate_system_confidence(system_name, context)
                })

        return systems

    def _get_context(self, text: str, keyword: str, window: int = 100) -> str:
        """获取关键词的上下文"""
        index = text.find(keyword)
        if index == -1:
            return ""

        start = max(0, index - window)
        end = min(len(text), index + len(keyword) + window)

        return text[start:end].strip()

    def _extract_concentration(self, context: str, compound: str) -> Optional[Dict]:
        """提取浓度信息"""
        concentration_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:wt%|wt\.%|weight\s*%)',
            r'(\d+(?:\.\d+)?)\s*(?:vol%|vol\.%|volume\s*%)',
            r'(\d+(?:\.\d+)?)\s*M',
            r'(\d+(?:\.\d+)?)\s*mol\s*L?[-1]',
            r'(\d+(?:\.\d+)?)\s*:[\s]*(\d+(?:\.\d+)?)',  # 比例
        ]

        for pattern in concentration_patterns:
            match = re.search(pattern, context)
            if match:
                value = float(match.group(1))
                if 'wt%' in pattern:
                    return {'value': value, 'unit': 'wt%', 'type': 'weight_percentage'}
                elif 'vol%' in pattern:
                    return {'value': value, 'unit': 'vol%', 'type': 'volume_percentage'}
                elif 'M' in pattern:
                    return {'value': value, 'unit': 'M', 'type': 'molarity'}
                elif len(match.groups()) > 1:  # 比例
                    return {'value': f"{value}:{match.group(2)}", 'unit': 'ratio', 'type': 'ratio'}
                else:
                    return {'value': value, 'unit': 'unknown', 'type': 'unknown'}

        return None

    def _is_valid_chemical_formula(self, formula: str) -> bool:
        """验证是否为有效的化学式"""
        # 简单的验证规则
        if len(formula) < 2 or len(formula) > 20:
            return False

        # 必须包含至少一个大写字母（元素符号）
        if not re.search(r'[A-Z]', formula):
            return False

        # 不能是常见的英文单词
        common_words = {'AND', 'THE', 'FOR', 'WITH', 'FROM', 'THIS', 'THAT', 'THESE', 'THOSE'}
        if formula.upper() in common_words:
            return False

        return True

    def _calculate_confidence(self, compound: str, context: str) -> float:
        """计算提取置信度"""
        confidence = 0.5  # 基础置信度

        # 如果上下文包含相关关键词，提高置信度
        context_keywords = ['electrolyte', 'solvent', 'salt', 'additive', 'concentration', 'solution']
        for keyword in context_keywords:
            if keyword in context.lower():
                confidence += 0.1

        # 如果化合物名称精确匹配，提高置信度
        if compound in context and len(compound) > 3:
            confidence += 0.2

        return min(confidence, 1.0)

    def _calculate_system_confidence(self, system_name: str, context: str) -> float:
        """计算系统识别置信度"""
        confidence = 0.6  # 基础置信度

        # 如果上下文包含多个组分，提高置信度
        component_count = 0
        for compounds in self.electrolyte_keywords.values():
            for compound in compounds:
                if compound in context:
                    component_count += 1

        if component_count >= 2:
            confidence += 0.2
        elif component_count >= 3:
            confidence += 0.2

        return min(confidence, 1.0)

    def _extract_system_components(self, context: str) -> List[str]:
        """从上下文中提取系统组分"""
        components = []

        for category, compounds in self.electrolyte_keywords.items():
            for compound in compounds:
                if compound in context:
                    components.append(compound)

        return list(set(components))  # 去重

    def batch_process_pdfs(self, pdf_directory: str, output_file: str = None) -> Dict:
        """批量处理PDF文件"""
        if not os.path.exists(pdf_directory):
            raise ValueError(f"PDF directory does not exist: {pdf_directory}")

        pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
        if not pdf_files:
            return {'processed_files': [], 'results': {}, 'message': 'No PDF files found'}

        results = {}
        processed_files = []

        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_directory, pdf_file)
            try:
                result = self.process_pdf(pdf_path)
                results[pdf_file] = result
                processed_files.append(pdf_file)
                logger.info(f"Processed {pdf_file} ({len(processed_files)}/{len(pdf_files)})")
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
                results[pdf_file] = {'error': str(e), 'status': 'failed'}

        # 保存结果到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        return {
            'processed_files': processed_files,
            'results': results,
            'total_files': len(pdf_files),
            'successful_count': len(processed_files),
            'failed_count': len(pdf_files) - len(processed_files)
        }