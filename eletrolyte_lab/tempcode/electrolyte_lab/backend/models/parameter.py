from datetime import datetime
from extensions import db
from sqlalchemy import JSON

class SystemParameter(db.Model):
    __tablename__ = 'system_parameters'

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=True)
    parameter_category = db.Column(db.String(50), nullable=False)  # system, performance, safety, etc.
    parameter_name = db.Column(db.String(100), nullable=False)
    parameter_value = db.Column(db.String(200))
    parameter_unit = db.Column(db.String(50))
    parameter_range = db.Column(JSON)  # 允许的范围
    is_required = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'parameter_category': self.parameter_category,
            'parameter_name': self.parameter_name,
            'parameter_value': self.parameter_value,
            'parameter_unit': self.parameter_unit,
            'parameter_range': self.parameter_range,
            'is_required': self.is_required,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }