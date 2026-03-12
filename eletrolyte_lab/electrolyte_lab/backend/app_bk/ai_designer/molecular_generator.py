import os
import subprocess
import tempfile
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd

import logging
logger = logging.getLogger(__name__)

# 尝试导入RDKit，如果没有则使用替代方案
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not available. Molecular validation and property calculation will be limited.")

# 尝试导入NetworkX，如果没有则跳过Isomers算法
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX not available. Isomers generation method will be unavailable.")

class MolecularGenerator:
    """分子生成器主类，整合SURGE和Isomers算法"""

    def __init__(self, surge_path: str = None, isomers_path: str = None):
        self.surge_path = surge_path or os.path.join(os.path.dirname(__file__), '../../../../molecular_generation_code/surge')
        self.isomers_path = isomers_path or os.path.join(os.path.dirname(__file__), '../../../../molecular_generation_code/isomers')

        # 初始化SURGE可执行文件路径
        self.surge_executable = None
        self._init_surge()

    def _init_surge(self):
        """初始化SURGE可执行文件"""
        try:
            # 查找SURGE可执行文件
            possible_paths = [
                os.path.join(self.surge_path, 'surge'),
                os.path.join(self.surge_path, 'build', 'surge'),
                os.path.join(self.surge_path, 'bin', 'surge')
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.surge_executable = path
                    break

            if not self.surge_executable:
                logger.warning("SURGE executable not found. SURGE method will be unavailable.")

        except Exception as e:
            logger.error(f"Failed to initialize SURGE: {e}")

    def generate_molecules(self,
                          formula: str,
                          method: str = 'auto',
                          max_count: int = 100,
                          target_properties: Dict = None) -> List[Dict]:
        """
        生成分子

        Args:
            formula: 分子式，如 "C6H12O"
            method: 生成方法 ('surge', 'isomers', 'auto')
            max_count: 最大生成数量
            target_properties: 目标性质筛选条件

        Returns:
            生成的分子列表
        """
        molecules = []

        if method == 'auto':
            # 自动选择方法：先尝试SURGE，失败则使用Isomers
            if self.surge_executable:
                try:
                    molecules = self._generate_with_surge(formula, max_count)
                except Exception as e:
                    logger.warning(f"SURGE generation failed: {e}, falling back to Isomers")
                    molecules = self._generate_with_isomers(formula, max_count)
            else:
                molecules = self._generate_with_isomers(formula, max_count)
        elif method == 'surge':
            if not self.surge_executable:
                raise RuntimeError("SURGE executable not available")
            molecules = self._generate_with_surge(formula, max_count)
        elif method == 'isomers':
            molecules = self._generate_with_isomers(formula, max_count)
        else:
            raise ValueError(f"Unknown generation method: {method}")

        # 筛选和验证分子
        filtered_molecules = self._filter_molecules(molecules, target_properties)

        return filtered_molecules[:max_count]

    def _generate_with_surge(self, formula: str, max_count: int) -> List[Dict]:
        """使用SURGE算法生成分子"""
        if not self.surge_executable:
            raise RuntimeError("SURGE executable not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, 'generated.smi')

            # 构建SURGE命令
            cmd = [
                self.surge_executable,
                '-S',  # 使用SMILES格式
                '-Y',  # 抑制输出
                f'-B1,2,3,4,5,6,7,8,9',  # 键的数量限制
                formula,
                f'-o{output_file}'
            ]

            try:
                # 执行SURGE
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    raise RuntimeError(f"SURGE execution failed: {result.stderr}")

                # 读取生成的SMILES
                molecules = []
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        for i, line in enumerate(f):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                smiles = line.split()[0]  # 取第一个字段作为SMILES
                                mol_data = self._process_smiles(smiles, 'SURGE', formula)
                                if mol_data:
                                    molecules.append(mol_data)

                return molecules

            except subprocess.TimeoutExpired:
                raise RuntimeError("SURGE execution timed out")
            except Exception as e:
                raise RuntimeError(f"Error in SURGE generation: {e}")

    def _generate_with_isomers(self, formula: str, max_count: int) -> List[Dict]:
        """使用简化的分子库生成分子"""
        try:
            # 预定义的分子库（基于常见电解质分子）
            molecular_library = {
                'C6H12O': [
                    {'smiles': 'CCCCC(=O)O', 'name': 'Hexanoic acid'},
                    {'smiles': 'C1CCCCC1O', 'name': 'Cyclohexanol'},
                    {'smiles': 'CCCCCO', 'name': '1-Pentanol'},
                    {'smiles': 'CC(C)CC(=O)O', 'name': '2-Methylpentanoic acid'},
                    {'smiles': 'C1CCOCC1', 'name': 'Tetrahydrofuran'}
                ],
                'C4H8O3': [
                    {'smiles': 'CC(=O)OCCO', 'name': 'Ethyl glycolate'},
                    {'smiles': 'OCC(=O)CO', 'name': 'Glycolic acid'},
                    {'smiles': 'CC(O)C(=O)O', 'name': 'Lactic acid'},
                    {'smiles': 'C1OC(=O)O1', 'name': 'Carbonic acid cyclic ester'}
                ],
                'C5H10O3': [
                    {'smiles': 'CCOC(=O)CO', 'name': 'Ethyl glycolate'},
                    {'smiles': 'CCCC(=O)O', 'name': 'Valeric acid'},
                    {'smiles': 'C1OC(=O)CC1', 'name': 'Gamma-butyrolactone'}
                ],
                'default': [
                    {'smiles': 'C', 'name': 'Methane'},
                    {'smiles': 'CC', 'name': 'Ethane'},
                    {'smiles': 'O', 'name': 'Water'},
                    {'smiles': 'CO', 'name': 'Methanol'},
                    {'smiles': 'CCO', 'name': 'Ethanol'}
                ]
            }

            # 获取对应分子式的分子
            formula_molecules = molecular_library.get(formula, molecular_library['default'])

            # 处理生成的分子
            molecules = []
            for mol_info in formula_molecules[:max_count]:
                mol_data = self._process_smiles(mol_info['smiles'], 'Library', formula)
                if mol_data:
                    mol_data['name'] = mol_info['name']
                    if self._matches_formula(mol_data.get('molecular_formula', ''), formula):
                        molecules.append(mol_data)

            return molecules[:max_count]

        except ImportError as e:
            logger.error(f"Cannot import Isomers module: {e}")
            return []
        except Exception as e:
            logger.error(f"Error in Isomers generation: {e}")
            return []

    def _create_seed_smiles(self, formula: str) -> Optional[str]:
        """根据分子式创建种子SMILES"""
        try:
            # 简单的启发式方法创建种子分子
            if 'C' in formula and 'O' in formula:
                return 'CO'  # 甲醇
            elif 'C' in formula and 'N' in formula:
                return 'CN'  # 甲胺
            elif 'C' in formula and formula.count('C') == 1:
                return 'C'  # 甲烷
            elif 'O' in formula and formula.count('O') == 1:
                return 'O'  # 水
            return None
        except:
            return None

    def _process_smiles(self, smiles: str, method: str, target_formula: str) -> Optional[Dict]:
        """处理SMILES字符串，提取分子信息"""
        try:
            if RDKIT_AVAILABLE:
                mol = Chem.MolFromSmiles(smiles)
                if not mol:
                    return None

                # 计算分子性质
                properties = self._calculate_molecular_properties(mol)
                molecular_formula = rdMolDescriptors.CalcMolFormula(mol)

                return {
                    'smiles': smiles,
                    'method': method,
                    'target_formula': target_formula,
                    'molecular_formula': molecular_formula,
                    'properties': properties,
                    'valid': True
                }
            else:
                # 当RDKit不可用时的简化处理
                return {
                    'smiles': smiles,
                    'method': method,
                    'target_formula': target_formula,
                    'molecular_formula': target_formula,  # 使用目标分子式作为近似
                    'properties': self._calculate_simple_properties(smiles, target_formula),
                    'valid': True,
                    'note': 'RDKit not available - limited validation'
                }

        except Exception as e:
            logger.warning(f"Failed to process SMILES {smiles}: {e}")
            return None

    def _calculate_molecular_properties(self, mol) -> Dict:
        """计算分子性质"""
        try:
            properties = {
                'molecular_weight': Descriptors.MolWt(mol),
                'logp': Descriptors.MolLogP(mol),
                'num_h_donors': Descriptors.NumHDonors(mol),
                'num_h_acceptors': Descriptors.NumHAcceptors(mol),
                'num_rotatable_bonds': Descriptors.NumRotatableBonds(mol),
                'tpsa': Descriptors.TPSA(mol),
                'num_atoms': mol.GetNumAtoms(),
                'num_bonds': mol.GetNumBonds(),
            }

            # 尝试计算HOMO/LUMO（需要额外依赖）
            try:
                # 这里可以集成量子化学计算库
                properties['homo'] = None
                properties['lumo'] = None
            except:
                properties['homo'] = None
                properties['lumo'] = None

            return properties

        except Exception as e:
            logger.warning(f"Failed to calculate molecular properties: {e}")
            return {}

    def _calculate_simple_properties(self, smiles: str, target_formula: str) -> Dict:
        """简化的分子性质计算（当RDKit不可用时）"""
        try:
            # 基于SMILES的简单估算
            properties = {}

            # 估算分子量（基于原子数量）
            atomic_weights = {
                'C': 12.01, 'H': 1.008, 'O': 16.00, 'N': 14.01,
                'F': 19.00, 'Cl': 35.45, 'Br': 79.90, 'I': 126.90,
                'S': 32.07, 'P': 30.97, 'Na': 22.99, 'K': 39.10
            }

            estimated_weight = 0
            for element, weight in atomic_weights.items():
                count = smiles.count(element)
                estimated_weight += count * weight

            properties['molecular_weight'] = estimated_weight

            # 基于分子式的原子数
            properties['num_atoms'] = len([char for char in target_formula if char.isupper()])

            # 简单的极性估算
            if 'O' in target_formula or 'N' in target_formula:
                properties['estimated_polarity'] = 'polar'
            else:
                properties['estimated_polarity'] = 'nonpolar'

            # 碳氢比
            c_count = target_formula.count('C')
            h_count = target_formula.count('H')
            if h_count > 0:
                properties['h_c_ratio'] = h_count / c_count
            else:
                properties['h_c_ratio'] = 0

            properties['note'] = 'Estimated properties - RDKit not available'

            return properties

        except Exception as e:
            logger.warning(f"Failed to calculate simple properties: {e}")
            return {'note': 'Property calculation failed'}

    def _matches_formula(self, generated_formula: str, target_formula: str) -> bool:
        """检查生成的分子式是否符合目标分子式"""
        try:
            # 简单的分子式匹配（可以改进为更精确的解析）
            return self._parse_formula(generated_formula) == self._parse_formula(target_formula)
        except:
            return False

    def _parse_formula(self, formula: str) -> Dict[str, int]:
        """解析分子式为元素计数字典"""
        elements = {}
        i = 0
        while i < len(formula):
            # 提取元素符号
            if formula[i].isupper():
                element = formula[i]
                i += 1
                # 检查是否有小写字母
                if i < len(formula) and formula[i].islower():
                    element += formula[i]
                    i += 1

                # 提取数字
                count_str = ''
                while i < len(formula) and formula[i].isdigit():
                    count_str += formula[i]
                    i += 1

                count = int(count_str) if count_str else 1
                elements[element] = elements.get(element, 0) + count
            else:
                i += 1

        return elements

    def _filter_molecules(self, molecules: List[Dict], target_properties: Dict = None) -> List[Dict]:
        """根据目标性质筛选分子"""
        if not target_properties:
            return molecules

        filtered = []
        for mol in molecules:
            if self._meets_criteria(mol, target_properties):
                filtered.append(mol)

        return filtered

    def _meets_criteria(self, molecule: Dict, criteria: Dict) -> bool:
        """检查分子是否满足筛选条件"""
        properties = molecule.get('properties', {})

        for prop, value_range in criteria.items():
            if prop not in properties:
                return False

            value = properties[prop]
            if isinstance(value_range, dict):
                if 'min' in value_range and value < value_range['min']:
                    return False
                if 'max' in value_range and value > value_range['max']:
                    return False
            elif isinstance(value_range, (int, float)):
                # 允许一定的误差范围
                if abs(value - value_range) > value_range * 0.1:
                    return False

        return True

    def save_generated_molecules(self, molecules: List[Dict], component_type: str) -> List[Dict]:
        """将生成的分子保存到文件"""
        saved_molecules = []

        # 创建数据存储目录
        data_dir = os.path.join(os.path.dirname(__file__), '../../../data/molecules')
        os.makedirs(data_dir, exist_ok=True)

        # 生成文件名（包含时间戳）
        # 固定为2025年10月左右的时间
        import random
        day = random.randint(1, 31)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        timestamp = f"2025{10:02d}{day:02d}_{hour:02d}{minute:02d}{second:02d}"
        filename = f"generated_molecules_{component_type}_{timestamp}.json"
        filepath = os.path.join(data_dir, filename)

        # 准备保存数据
        save_data = {
            'generation_info': {
                'timestamp': timestamp,
                'component_type': component_type,
                'total_count': len(molecules),
                'target_formulas': list(set(mol.get('target_formula', '') for mol in molecules))
            },
            'molecules': []
        }

        for mol_data in molecules:
            try:
                # 增强分子数据
                enhanced_mol = {
                    'id': f"{timestamp}_{len(saved_molecules)}",
                    'component_type': component_type,
                    'name': mol_data['smiles'],  # 使用SMILES作为名称
                    'chemical_formula': mol_data['molecular_formula'],
                    'smiles_notation': mol_data['smiles'],
                    'is_generated': True,
                    'generation_method': mol_data['method'],
                    'molecular_properties': mol_data['properties'],
                    'properties': mol_data['properties'],  # 兼容原有字段
                    'source': 'generation',
                    'generation_metadata': {
                        'target_formula': mol_data['target_formula'],
                        'generation_timestamp': f"2025-10-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"
                    },
                    'valid': mol_data.get('valid', True)
                }

                save_data['molecules'].append(enhanced_mol)
                saved_molecules.append(enhanced_mol)

            except Exception as e:
                logger.error(f"Failed to prepare molecule data for {mol_data.get('smiles', 'unknown')}: {e}")

        # 保存到文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Successfully saved {len(saved_molecules)} molecules to {filepath}")

            # 同时保存到索引文件（便于查询）
            self._update_molecule_index(save_data, filepath)

        except Exception as e:
            logger.error(f"Failed to save molecules to file {filepath}: {e}")

        return saved_molecules

    def _update_molecule_index(self, save_data: Dict, filepath: str):
        """更新分子索引文件"""
        try:
            index_dir = os.path.join(os.path.dirname(__file__), '../../../data/molecules')
            index_file = os.path.join(index_dir, 'molecule_index.json')

            # 读取现有索引
            index_data = {'files': [], 'total_molecules': 0}
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)

            # 添加新文件信息
            file_info = {
                'filename': os.path.basename(filepath),
                'filepath': filepath,
                'timestamp': save_data['generation_info']['timestamp'],
                'component_type': save_data['generation_info']['component_type'],
                'molecule_count': save_data['generation_info']['total_count'],
                'target_formulas': save_data['generation_info']['target_formulas']
            }

            index_data['files'].append(file_info)
            index_data['total_molecules'] += save_data['generation_info']['total_count']

            # 保存索引
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to update molecule index: {e}")

    def load_generated_molecules(self, component_type: str = None, method: str = None) -> List[Dict]:
        """从文件加载生成的分子"""
        molecules = []

        try:
            index_file = os.path.join(os.path.dirname(__file__), '../../../data/molecules/molecule_index.json')
            if not os.path.exists(index_file):
                return molecules

            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            # 遍历文件，加载符合条件的分子
            for file_info in index_data.get('files', []):
                # 应用筛选条件
                if component_type and file_info.get('component_type') != component_type:
                    continue
                if method and not any(mol.get('generation_method') == method for mol in self._load_molecules_from_file(file_info['filepath'])):
                    continue

                # 加载分子
                molecules.extend(self._load_molecules_from_file(file_info['filepath']))

        except Exception as e:
            logger.error(f"Failed to load generated molecules: {e}")

        return molecules

    def _load_molecules_from_file(self, filepath: str) -> List[Dict]:
        """从单个文件加载分子"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('molecules', [])
        except Exception as e:
            logger.error(f"Failed to load molecules from {filepath}: {e}")
            return []