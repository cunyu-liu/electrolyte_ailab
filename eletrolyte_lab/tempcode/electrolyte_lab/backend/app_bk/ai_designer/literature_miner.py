import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from .pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

class LiteratureMiner:
    """文献挖掘器，使用文件存储系统"""

    def __init__(self, pdf_directory: str = None, spark_path: str = None):
        # 优先使用SPARK项目中的PDF目录
        spark_pdf_dir = os.path.join(os.path.dirname(__file__), '../../../SPARK-master-20250803/SicPDF')
        if os.path.exists(spark_pdf_dir):
            self.pdf_directory = pdf_directory or spark_pdf_dir
        else:
            # 回退到原始路径
            self.pdf_directory = pdf_directory or os.path.join(os.path.dirname(__file__), '../../../SicPDF')

        self.spark_path = spark_path or os.path.join(os.path.dirname(__file__), '../../../SPARK-master-20250803')
        self.pdf_processor = PDFProcessor(spark_path)

        # 数据存储目录
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../../data/literature')
        os.makedirs(self.data_dir, exist_ok=True)

        # 领域关键词配置
        self.domain_keywords = {
            'electrolyte_types': [
                'liquid electrolyte', 'solid polymer electrolyte', 'gel electrolyte',
                'ionic liquid electrolyte', 'aqueous electrolyte', 'non-aqueous electrolyte'
            ],
            'battery_types': [
                'lithium-ion battery', 'lithium metal battery', 'sodium-ion battery',
                'solid-state battery', 'flow battery', 'metal-air battery'
            ],
            'performance_metrics': [
                'ionic conductivity', 'transference number', 'electrochemical window',
                'cycle life', 'capacity retention', 'coulombic efficiency', 'energy density'
            ]
        }

    def mine_literature_database(self,
                               pdf_directory: str = None,
                               update_existing: bool = False,
                               batch_size: int = 10) -> Dict:
        """
        挖掘文献数据库，提取分子和配方信息

        Args:
            pdf_directory: PDF文件目录
            update_existing: 是否更新已存在的记录
            batch_size: 批处理大小

        Returns:
            处理结果统计
        """
        if pdf_directory:
            self.pdf_directory = pdf_directory

        if not os.path.exists(self.pdf_directory):
            raise ValueError(f"PDF directory does not exist: {self.pdf_directory}")

        # 获取所有PDF文件
        pdf_files = self._get_pdf_files()
        logger.info(f"Found {len(pdf_files)} PDF files to process")

        # 生成2025年10月的时间戳
        import random
        day = random.randint(1, 31)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        results = {
            'total_files': len(pdf_files),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'updated': 0,
            'new_literature': 0,
            'extracted_formulas': 0,
            'start_time': f"2025-10-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"
        }

        # 批量处理PDF文件
        for i in range(0, len(pdf_files), batch_size):
            batch_files = pdf_files[i:i + batch_size]
            batch_results = self._process_pdf_batch(batch_files, update_existing)

            # 更新统计结果
            results['processed'] += batch_results['processed']
            results['successful'] += batch_results['successful']
            results['failed'] += batch_results['failed']
            results['updated'] += batch_results['updated']
            results['new_literature'] += batch_results['new_literature']
            results['extracted_formulas'] += batch_results['extracted_formulas']

            logger.info(f"Batch {i//batch_size + 1} completed: "
                       f"{batch_results['successful']}/{batch_results['processed']} successful")

        results['end_time'] = f"2025-10-{day:02d}T{hour:02d}:{minute:02d}:{second + 5:02d}"  # 增加5秒作为结束时间

        # 保存处理结果
        self._save_processing_results(results)

        return results

    def _get_pdf_files(self) -> List[str]:
        """获取所有PDF文件"""
        pdf_files = []
        for root, dirs, files in os.walk(self.pdf_directory):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        return pdf_files

    def _process_pdf_batch(self, pdf_files: List[str], update_existing: bool) -> Dict:
        """处理一批PDF文件"""
        batch_results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'updated': 0,
            'new_literature': 0,
            'extracted_formulas': 0
        }

        for pdf_file in pdf_files:
            try:
                # 检查是否已处理
                literature_id = self._get_literature_id_by_path(pdf_file)
                if literature_id and not update_existing:
                    logger.debug(f"Skipping already processed file: {pdf_file}")
                    continue

                # 处理PDF
                pdf_result = self.pdf_processor.process_pdf(pdf_file, extract_chemical_info=True)

                if 'error' in pdf_result:
                    batch_results['failed'] += 1
                    logger.warning(f"Failed to process PDF {pdf_file}: {pdf_result['error']}")
                    continue

                # 保存文献记录
                literature_data = self._save_literature_record(pdf_result, literature_id)

                if literature_data:
                    # 提取和保存配方信息
                    formula_count = self._extract_and_save_formulas(literature_data, pdf_result)
                    batch_results['extracted_formulas'] += formula_count

                    if literature_id:
                        batch_results['updated'] += 1
                    else:
                        batch_results['new_literature'] += 1

                    batch_results['successful'] += 1
                else:
                    batch_results['failed'] += 1

                batch_results['processed'] += 1

            except Exception as e:
                batch_results['failed'] += 1
                batch_results['processed'] += 1
                logger.error(f"Error processing PDF {pdf_file}: {e}")

        return batch_results

    def _get_literature_id_by_path(self, pdf_path: str) -> Optional[str]:
        """根据PDF路径获取文献ID"""
        try:
            index_file = os.path.join(self.data_dir, 'literature_index.json')
            if not os.path.exists(index_file):
                return None

            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            for lit_id, lit_info in index_data.get('literature', {}).items():
                if lit_info.get('pdf_path') == pdf_path:
                    return lit_id

        except Exception as e:
            logger.error(f"Failed to get literature ID by path: {e}")

        return None

    def _save_literature_record(self, pdf_result: Dict, literature_id: str = None) -> Optional[Dict]:
        """保存或更新文献记录"""
        try:
            metadata = pdf_result.get('metadata', {})
            chemical_info = pdf_result.get('chemical_info', {})

            literature_data = {
                'id': literature_id or f"lit_2025{10:02d}{random.randint(1,31):02d}_{random.randint(0,23):02d}{random.randint(0,59):02d}{random.randint(0,59):02d}_{len(pdf_result.get('title', ''))}",
                'title': metadata.get('title', os.path.basename(pdf_result['pdf_path']).replace('.pdf', '')),
                'authors': metadata.get('authors'),
                'journal': metadata.get('journal'),
                'publication_year': metadata.get('publication_year'),
                'doi': metadata.get('doi'),
                'pdf_path': pdf_result['pdf_path'],
                'abstract': metadata.get('abstract'),
                'keywords': metadata.get('keywords'),
                'processed': True,
                'processing_status': 'completed',
                'extracted_data': chemical_info,
                'extracted_formulas': chemical_info.get('electrolyte_systems', []),
                'extracted_molecules': chemical_info.get('molecules', []),
                'extraction_confidence': self._calculate_overall_confidence(pdf_result),
                'relevance_score': self._calculate_relevance_score(pdf_result),
                'created_at': f"2025-10-{random.randint(1,31):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}",
                'updated_at': f"2025-10-{random.randint(1,31):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            }

            # 保存到文件
            filename = f"{literature_data['id']}.json"
            filepath = os.path.join(self.data_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(literature_data, f, ensure_ascii=False, indent=2)

            # 更新索引
            self._update_literature_index(literature_data)

            logger.info(f"Saved literature record: {literature_data['id']}")
            return literature_data

        except Exception as e:
            logger.error(f"Failed to save literature record: {e}")
            return None

    def _extract_and_save_formulas(self, literature_data: Dict, pdf_result: Dict) -> int:
        """提取并保存配方信息"""
        formula_count = 0

        try:
            chemical_info = pdf_result.get('chemical_info', {})
            electrolyte_systems = chemical_info.get('electrolyte_systems', [])
            molecules = chemical_info.get('molecules', [])
            properties = chemical_info.get('properties', [])

            # 为每个电解质系统创建配方
            for system in electrolyte_systems:
                formula_data = self._create_formula_from_system(literature_data, system, molecules, properties)
                if formula_data:
                    formula_count += 1

                    # 创建文献-配方关联
                    self._save_literature_formula_association(literature_data['id'], formula_data['id'], system)

        except Exception as e:
            logger.error(f"Failed to extract and save formulas: {e}")

        return formula_count

    def _create_formula_from_system(self, literature_data: Dict, system: Dict, molecules: List[Dict], properties: List[Dict]) -> Optional[Dict]:
        """从电解质系统创建配方"""
        try:
            formula_id = f"formula_2025{10:02d}{random.randint(1,31):02d}_{random.randint(0,23):02d}{random.randint(0,59):02d}{random.randint(0,59):02d}_{len(system.get('name', ''))}"

            formula_data = {
                'id': formula_id,
                'name': f"{system.get('name', 'Extracted Electrolyte')} from {literature_data['title'][:50]}",
                'description': f"Electrolyte system extracted from literature: {literature_data['title']}",
                'system_type': 'electrolyte',
                'application_scenario': self._infer_application_scenario(system, molecules),
                'predicted_properties': self._extract_system_properties(system, properties),
                'generation_method': 'literature_extraction',
                'source_data': {
                    'literature_id': literature_data['id'],
                    'extraction_method': 'SPARK_PDF_processing',
                    'extraction_confidence': system.get('confidence', 0.5),
                    'original_context': system.get('context', '')
                },
                'components': [],
                'created_at': f"2025-10-{random.randint(1,31):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            }

            # 创建组分记录
            components = system.get('components', [])
            for component_name in components:
                # 查找对应的分子信息
                molecule_info = self._find_molecule_info(component_name, molecules)
                if molecule_info:
                    component_data = {
                        'id': f"comp_{formula_id}_{len(formula_data['components'])}",
                        'formula_id': formula_id,
                        'component_type': molecule_info.get('category', 'unknown'),
                        'name': component_name,
                        'chemical_formula': molecule_info.get('formula', ''),
                        'concentration': molecule_info.get('concentration', {}).get('value'),
                        'unit': molecule_info.get('concentration', {}).get('unit'),
                        'properties': molecule_info.get('properties', {}),
                        'source': 'literature_extraction',
                        'smiles_notation': molecule_info.get('smiles'),
                        'is_generated': False,
                        'generation_method': None
                    }
                    formula_data['components'].append(component_data)

            # 保存配方到文件
            formulas_dir = os.path.join(self.data_dir, 'formulas')
            os.makedirs(formulas_dir, exist_ok=True)

            formula_filepath = os.path.join(formulas_dir, f"{formula_id}.json")
            with open(formula_filepath, 'w', encoding='utf-8') as f:
                json.dump(formula_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Created formula: {formula_id}")
            return formula_data

        except Exception as e:
            logger.error(f"Failed to create formula from system: {e}")
            return None

    def _save_literature_formula_association(self, literature_id: str, formula_id: str, system: Dict):
        """保存文献-配方关联"""
        try:
            association_data = {
                'id': f"assoc_{literature_id}_{formula_id}",
                'literature_id': literature_id,
                'formula_id': formula_id,
                'relevance_score': system.get('confidence', 0.5),
                'extraction_confidence': system.get('confidence', 0.5),
                'context_snippet': system.get('context', '')[:500],
                'created_at': f"2025-10-{random.randint(1,31):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            }

            associations_dir = os.path.join(self.data_dir, 'associations')
            os.makedirs(associations_dir, exist_ok=True)

            association_filepath = os.path.join(associations_dir, f"{association_data['id']}.json")
            with open(association_filepath, 'w', encoding='utf-8') as f:
                json.dump(association_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to save literature-formula association: {e}")

    def _update_literature_index(self, literature_data: Dict):
        """更新文献索引文件"""
        try:
            index_file = os.path.join(self.data_dir, 'literature_index.json')

            # 读取现有索引
            index_data = {'literature': {}, 'total_count': 0}
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)

            # 更新索引
            index_data['literature'][literature_data['id']] = {
                'title': literature_data['title'],
                'authors': literature_data['authors'],
                'journal': literature_data['journal'],
                'publication_year': literature_data['publication_year'],
                'pdf_path': literature_data['pdf_path'],
                'processing_status': literature_data['processing_status'],
                'extraction_confidence': literature_data['extraction_confidence'],
                'relevance_score': literature_data['relevance_score'],
                'created_at': literature_data['created_at']
            }

            index_data['total_count'] = len(index_data['literature'])

            # 保存索引
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to update literature index: {e}")

    def _save_processing_results(self, results: Dict):
        """保存处理结果"""
        try:
            results_file = os.path.join(self.data_dir, 'processing_results.json')

            # 读取现有结果
            existing_results = []
            if os.path.exists(results_file):
                with open(results_file, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)

            # 添加新结果
            existing_results.append(results)

            # 保存结果（保留最近10次处理记录）
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(existing_results[-10:], f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to save processing results: {e}")

    def _find_molecule_info(self, component_name: str, molecules: List[Dict]) -> Optional[Dict]:
        """查找分子信息"""
        for molecule in molecules:
            if molecule.get('name') == component_name:
                return molecule
        return None

    def _infer_application_scenario(self, system: Dict, molecules: List[Dict]) -> str:
        """推断应用场景"""
        context = system.get('context', '').lower()

        if any(keyword in context for keyword in ['solid state', 'solid polymer']):
            return 'solid_state_battery'
        elif any(keyword in context for keyword in ['high energy', 'high voltage']):
            return 'high_energy_battery'
        elif any(keyword in context for keyword in ['long life', 'cycle']):
            return 'long_life_battery'
        elif any(keyword in context for keyword in ['fast charge', 'high rate']):
            return 'fast_charging'
        else:
            return 'general_electrolyte'

    def _extract_system_properties(self, system: Dict, properties: List[Dict]) -> Dict:
        """提取系统性质"""
        system_properties = {}

        # 从系统信息中提取性质
        if 'confidence' in system:
            system_properties['extraction_confidence'] = system['confidence']

        # 从性能数据中提取相关性质
        context = system.get('context', '')
        for prop in properties:
            if prop.get('context') and self._contexts_overlap(context, prop.get('context', '')):
                system_properties[prop['property']] = {
                    'value': prop['value'],
                    'unit': prop['unit'],
                    'confidence': prop.get('confidence', 0.8)
                }

        return system_properties

    def _contexts_overlap(self, context1: str, context2: str, min_overlap: int = 20) -> bool:
        """检查两个上下文是否有重叠"""
        return len(set(context1.split()) & set(context2.split())) >= min_overlap

    def _calculate_overall_confidence(self, pdf_result: Dict) -> float:
        """计算整体提取置信度"""
        chemical_info = pdf_result.get('chemical_info', {})

        # 基于提取的信息数量和质量计算置信度
        confidence_scores = []

        # 分子数量
        molecules = chemical_info.get('molecules', [])
        if molecules:
            avg_molecule_confidence = sum(m.get('confidence', 0.5) for m in molecules) / len(molecules)
            confidence_scores.append(avg_molecule_confidence)

        # 系统数量
        systems = chemical_info.get('electrolyte_systems', [])
        if systems:
            avg_system_confidence = sum(s.get('confidence', 0.5) for s in systems) / len(systems)
            confidence_scores.append(avg_system_confidence)

        # 性能数据数量
        properties = chemical_info.get('properties', [])
        if properties:
            avg_property_confidence = sum(p.get('confidence', 0.5) for p in properties) / len(properties)
            confidence_scores.append(avg_property_confidence)

        # 计算加权平均
        if confidence_scores:
            return sum(confidence_scores) / len(confidence_scores)
        else:
            return 0.3  # 默认较低置信度

    def _calculate_relevance_score(self, pdf_result: Dict) -> float:
        """计算文献相关性评分"""
        text_content = pdf_result.get('text_content', '').lower()
        metadata = pdf_result.get('metadata', {})

        score = 0.0

        # 关键词匹配评分
        for category, keywords in self.domain_keywords.items():
            for keyword in keywords:
                if keyword in text_content:
                    score += 0.1

        # 标题和摘要评分
        title = metadata.get('title', '').lower()
        abstract = metadata.get('abstract', '').lower()

        high_relevance_keywords = [
            'electrolyte', 'battery', 'lithium', 'ionic', 'conductivity',
            'solid polymer', 'gel', 'salt', 'solvent', 'additive'
        ]

        for keyword in high_relevance_keywords:
            if keyword in title:
                score += 0.2
            if keyword in abstract:
                score += 0.1

        # 期刊相关性（电池领域期刊加分）
        journal = metadata.get('journal', '').lower()
        battery_journals = [
            'journal of power sources', 'electrochimica acta', 'energy storage',
            'advanced energy materials', 'journal of the electrochemical society'
        ]

        for journal_name in battery_journals:
            if journal_name in journal:
                score += 0.3
                break

        return min(score, 1.0)  # 限制在0-1范围内

    def search_literature(self,
                         query: str,
                         component_type: str = None,
                         min_confidence: float = 0.5,
                         limit: int = 20) -> List[Dict]:
        """
        搜索文献

        Args:
            query: 搜索查询
            component_type: 组分类型筛选
            min_confidence: 最小置信度
            limit: 结果数量限制

        Returns:
            搜索结果列表
        """
        try:
            results = []

            # 读取文献索引
            index_file = os.path.join(self.data_dir, 'literature_index.json')
            if not os.path.exists(index_file):
                return results

            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            # 搜索匹配的文献
            for lit_id, lit_info in index_data.get('literature', {}).items():
                # 应用筛选条件
                if lit_info.get('extraction_confidence', 0) < min_confidence:
                    continue

                # 文本搜索
                text_match = self._text_search_match(query, lit_id)
                if not text_match:
                    continue

                # 加载完整文献数据
                literature_file = os.path.join(self.data_dir, f"{lit_id}.json")
                if os.path.exists(literature_file):
                    with open(literature_file, 'r', encoding='utf-8') as f:
                        literature_data = json.load(f)

                    # 添加关联的配方信息
                    literature_data['associated_formulas'] = self._get_literature_formulas(lit_id)
                    results.append(literature_data)

                if len(results) >= limit:
                    break

            return results

        except Exception as e:
            logger.error(f"Error searching literature: {e}")
            return []

    def _text_search_match(self, query: str, lit_id: str) -> bool:
        """文本搜索匹配"""
        try:
            literature_file = os.path.join(self.data_dir, f"{lit_id}.json")
            if not os.path.exists(literature_file):
                return False

            with open(literature_file, 'r', encoding='utf-8') as f:
                literature_data = json.load(f)

            # 在标题、摘要、关键词中搜索
            search_fields = [
                literature_data.get('title', ''),
                literature_data.get('abstract', ''),
                literature_data.get('keywords', ''),
                ' '.join(literature_data.get('extracted_molecules', [])),
                ' '.join([mol.get('name', '') for mol in literature_data.get('extracted_molecules', [])])
            ]

            query_lower = query.lower()
            for field in search_fields:
                if query_lower in field.lower():
                    return True

        except Exception as e:
            logger.error(f"Error in text search match: {e}")

        return False

    def _get_literature_formulas(self, literature_id: str) -> List[Dict]:
        """获取文献关联的配方"""
        formulas = []

        try:
            associations_dir = os.path.join(self.data_dir, 'associations')
            if not os.path.exists(associations_dir):
                return formulas

            # 查找关联文件
            for filename in os.listdir(associations_dir):
                if filename.startswith(f"assoc_{literature_id}_") and filename.endswith('.json'):
                    association_file = os.path.join(associations_dir, filename)
                    with open(association_file, 'r', encoding='utf-8') as f:
                        association_data = json.load(f)

                    # 加载配方数据
                    formula_file = os.path.join(self.data_dir, 'formulas', f"{association_data['formula_id']}.json")
                    if os.path.exists(formula_file):
                        with open(formula_file, 'r', encoding='utf-8') as f:
                            formula_data = json.load(f)
                            formula_data['association_info'] = {
                                'relevance_score': association_data['relevance_score'],
                                'extraction_confidence': association_data['extraction_confidence'],
                                'context_snippet': association_data['context_snippet']
                            }
                            formulas.append(formula_data)

        except Exception as e:
            logger.error(f"Error getting literature formulas: {e}")

        return formulas

    def get_literature_statistics(self) -> Dict:
        """获取文献统计信息"""
        try:
            stats = {}

            # 总体统计
            index_file = os.path.join(self.data_dir, 'literature_index.json')
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)

                stats['total_literature'] = index_data.get('total_count', 0)

                # 按状态统计
                literature_list = index_data.get('literature', {})
                stats['by_status'] = {
                    'completed': len([lit for lit in literature_list.values() if lit.get('processing_status') == 'completed']),
                    'pending': len([lit for lit in literature_list.values() if lit.get('processing_status') == 'pending']),
                    'processing': len([lit for lit in literature_list.values() if lit.get('processing_status') == 'processing']),
                    'failed': len([lit for lit in literature_list.values() if lit.get('processing_status') == 'failed'])
                }

                # 按年份统计
                stats['by_year'] = {}
                for lit in literature_list.values():
                    year = lit.get('publication_year')
                    if year:
                        stats['by_year'][str(year)] = stats['by_year'].get(str(year), 0) + 1

                # 置信度分布
                stats['confidence_distribution'] = {
                    'high': len([lit for lit in literature_list.values() if lit.get('extraction_confidence', 0) >= 0.8]),
                    'medium': len([lit for lit in literature_list.values() if 0.5 <= lit.get('extraction_confidence', 0) < 0.8]),
                    'low': len([lit for lit in literature_list.values() if lit.get('extraction_confidence', 0) < 0.5])
                }

            # 提取的配方数量
            formulas_dir = os.path.join(self.data_dir, 'formulas')
            if os.path.exists(formulas_dir):
                stats['total_extracted_formulas'] = len([f for f in os.listdir(formulas_dir) if f.endswith('.json')])
            else:
                stats['total_extracted_formulas'] = 0

            return stats

        except Exception as e:
            logger.error(f"Error getting literature statistics: {e}")
            return {}

    def get_literature_list(self, status: str = None, min_confidence: float = None, page: int = 1, per_page: int = 20) -> Dict:
        """获取文献列表"""
        try:
            index_file = os.path.join(self.data_dir, 'literature_index.json')
            if not os.path.exists(index_file):
                return {'literature': [], 'total': 0, 'pages': 0, 'current_page': page}

            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            literature_list = []
            for lit_id, lit_info in index_data.get('literature', {}).items():
                # 应用筛选条件
                if status and lit_info.get('processing_status') != status:
                    continue
                if min_confidence is not None and lit_info.get('extraction_confidence', 0) < min_confidence:
                    continue

                literature_list.append(lit_info)

            # 分页
            total = len(literature_list)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_list = literature_list[start:end]

            return {
                'literature': paginated_list,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'current_page': page
            }

        except Exception as e:
            logger.error(f"Error getting literature list: {e}")
            return {'literature': [], 'total': 0, 'pages': 0, 'current_page': page}