from datetime import datetime
from extensions import db
from sqlalchemy import JSON

# 实验和配方映射关系常量
MAX_FORMULAS_PER_EXPERIMENT = 64  # 一次实验最多64个配方
COMPONENTS_PER_FORMULA = 10       # 每个配方固定10个组分

class Formula(db.Model):
    __tablename__ = 'formulas'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    system_type = db.Column(db.String(50), nullable=False)  # 正极/负极
    application_scenario = db.Column(db.String(100))  # 蓄能、动力、3C等
    predicted_properties = db.Column(JSON)  # 预测的性质
    generation_method = db.Column(db.String(100))  # 生成方法：initial_design, bayesian_opt, redesign
    source_data = db.Column(JSON)  # 来源数据
    created_at = db.Column(db.DateTime, default=lambda: datetime(2025, 10, 15, 10, 25, 0))
  
    # 关联关系
    components = db.relationship('Component', backref='formula', lazy=True, cascade='all, delete-orphan')

    def validate_components(self):
        """验证配方是否满足10个组分的规则"""
        component_count = len(self.components)

        validation_result = {
            'expected_count': COMPONENTS_PER_FORMULA,
            'actual_count': component_count,
            'is_valid': component_count == COMPONENTS_PER_FORMULA,
            'missing_components': [] if component_count >= COMPONENTS_PER_FORMULA else [f"缺少{COMPONENTS_PER_FORMULA - component_count}个组分"],
            'extra_components': [] if component_count <= COMPONENTS_PER_FORMULA else [f"多余{component_count - COMPONENTS_PER_FORMULA}个组分"]
        }

        return validation_result

    def to_dict(self):
        """转换为字典，包含组件验证信息"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'system_type': self.system_type,
            'application_scenario': self.application_scenario,
            'predicted_properties': self.predicted_properties,
            'generation_method': self.generation_method,
            'source_data': self.source_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
              'components': [comp.to_dict() for comp in self.components],
            'component_validation': self.validate_components()
        }
        return result

class Component(db.Model):
    __tablename__ = 'components'

    id = db.Column(db.Integer, primary_key=True)
    formula_id = db.Column(db.Integer, db.ForeignKey('formulas.id'), nullable=False)
    component_type = db.Column(db.String(50), nullable=False)  # solvent, salt, additive
    name = db.Column(db.String(200), nullable=False)
    chemical_formula = db.Column(db.String(100))
    concentration = db.Column(db.Float)  # 浓度或比例
    unit = db.Column(db.String(20))  # 单位
    properties = db.Column(JSON)  # 分子性质
    source = db.Column(db.String(100))  # 来源：literature, generation, database

    # 分子生成相关字段
    smiles_notation = db.Column(db.Text)  # SMILES 分子结构表示
    is_generated = db.Column(db.Boolean, default=False)  # 是否为生成分子
    generation_method = db.Column(db.String(50))  # 生成方法：SURGE, Isomers, Manual
    molecular_properties = db.Column(JSON)  # 详细分子性质
    generation_metadata = db.Column(JSON)  # 生成元数据

    created_at = db.Column(db.DateTime, default=lambda: datetime(2025, 10, 15, 10, 28, 0))

    def to_dict(self):
        return {
            'id': self.id,
            'formula_id': self.formula_id,
            'component_type': self.component_type,
            'name': self.name,
            'chemical_formula': self.chemical_formula,
            'concentration': self.concentration,
            'unit': self.unit,
            'properties': self.properties,
            'source': self.source,
            'smiles_notation': self.smiles_notation,
            'is_generated': self.is_generated,
            'generation_method': self.generation_method,
            'molecular_properties': self.molecular_properties,
            'generation_metadata': self.generation_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }