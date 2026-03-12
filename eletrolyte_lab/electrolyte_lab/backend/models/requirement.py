from datetime import datetime
from extensions import db

class Requirement(db.Model):
    __tablename__ = 'requirement'

    id = db.Column(db.BigInteger, primary_key=True)
    requirement_id = db.Column(db.BigInteger, nullable=True)
    user_id = db.Column(db.String, nullable=True)
    create_time = db.Column(db.Date, nullable=True)

    # 关联明细表
    details = db.relationship('RequirementDetail', backref='requirement', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'user_id': self.user_id,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }

class RequirementDetail(db.Model):
    __tablename__ = 'requirement_details'

    id = db.Column(db.BigInteger, primary_key=True)
    # 去掉外键约束，只保留字段引用（避免非主键外键约束问题）
    requirement_id = db.Column(db.BigInteger, nullable=True)
    category = db.Column(db.String, nullable=True)
    param_name = db.Column(db.String, nullable=True)
    param_value = db.Column(db.String, nullable=True)
    unit = db.Column(db.String, nullable=True)
    range = db.Column(db.String, nullable=True)
    confidence = db.Column(db.Numeric, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'category': self.category,
            'param_name': self.param_name,
            'param_value': self.param_value,
            'unit': self.unit,
            'range': self.range,
            'confidence': float(self.confidence) if self.confidence is not None else None
        }
