from datetime import datetime
from extensions import db
from sqlalchemy import JSON
import enum

# 实验和配方映射关系常量
MAX_FORMULAS_PER_EXPERIMENT = 64  # 一次实验最多64个配方
COMPONENTS_PER_FORMULA = 10       # 每个配方固定10个组分

class ExperimentStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Experiment(db.Model):
    __tablename__ = 'experiments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(ExperimentStatus), default=ExperimentStatus.PENDING)
    experiment_type = db.Column(db.String(50), default='screening')  # screening, optimization, validation
    experiment_id = db.Column(db.String(100), unique=True)  # 实验唯一标识

    # 配方映射关系 - 兼容单一配方和多配方场景
    formula_id = db.Column(db.Integer, db.ForeignKey('formulas.id'), nullable=False)  # 单一配方ID（兼容性）
    formula_count = db.Column(db.Integer, default=1)  # 该实验包含的配方数量，最多64个

    # 用户关联
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 创建实验的用户ID

    user_requirements = db.Column(JSON)  # 用户需求参数
    created_at = db.Column(db.DateTime, default=lambda: datetime(2025, 10, 15, 10, 30, 0))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # 关联关系
    formula = db.relationship('Formula', backref='experiments')
    results = db.relationship('ExperimentResult', backref='experiment', lazy=True, cascade='all, delete-orphan')

    def calculate_formula_stats(self):
        """计算配方映射统计信息"""
        # 计算总配方数（不超过64个）
        total_formulas = min(self.formula_count or 1, MAX_FORMULAS_PER_EXPERIMENT)

        # 计算总组分数（每个配方10个组分）
        total_components = total_formulas * COMPONENTS_PER_FORMULA

        # 检查组分数违规情况
        component_violations = []
        if self.formula and hasattr(self.formula, 'validate_components'):
            validation = self.formula.validate_components()
            if not validation['is_valid']:
                component_violations.append({
                    'formula_id': self.formula_id,
                    'component_count': validation['actual_count'],
                    'formula_name': self.formula.name
                })

        return {
            'total_formulas': total_formulas,
            'total_components': total_components,
            'component_violations': component_violations
        }

    def to_dict(self):
        """转换为字典，包含配方映射统计信息"""
        formula_stats = self.calculate_formula_stats()

        return {
            'id': self.id,
            'experiment_id': getattr(self, 'experiment_id', f'EXP-{self.id:06d}'),
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'experiment_type': getattr(self, 'experiment_type', 'screening'),
            'formula_id': self.formula_id,
            'formula_count': self.formula_count or 1,
            'user_requirements': self.user_requirements,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'formula': self.formula.to_dict() if self.formula else None,
            'formula_stats': formula_stats
        }

class ExperimentResult(db.Model):
    __tablename__ = 'experiment_results'

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)
    result_type = db.Column(db.String(50), nullable=False)  # performance_curves, monitoring_data, etc.
    data = db.Column(JSON, nullable=False)  # 实际的实验数据
    meta_data = db.Column(JSON)  # 元数据信息
    created_at = db.Column(db.DateTime, default=lambda: datetime(2025, 10, 15, 10, 35, 0))

    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'result_type': self.result_type,
            'data': self.data,
            'metadata': self.meta_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }