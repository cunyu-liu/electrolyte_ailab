from datetime import datetime
from extensions import db
import enum


class ProjectStatus(enum.Enum):
    """项目状态枚举"""
    PENDING = 0  # 待开始
    RUNNING = 1  # 进行中
    COMPLETED = 2  # 已完成
    FAILED = 3  # 失败
    ARCHIVED = 4  # 已归档


class Project(db.Model):
    __tablename__ = 'project'

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.SmallInteger, default=ProjectStatus.PENDING.value, nullable=False)

    # 外键关联
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    requirement_id = db.Column(db.BigInteger, db.ForeignKey('requirement.requirement_id'), nullable=True)
    main_id = db.Column(db.BigInteger, nullable=True)

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # 关联关系
    user = db.relationship('User', backref='projects', lazy=True)
    requirement = db.relationship('Requirement', backref='projects', lazy=True)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'user_id': self.user_id,
            'requirement_id': self.requirement_id,
            'main_id': self.main_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status_display': ProjectStatus(self.status).name if self.status is not None else None
        }

    def __repr__(self):
        return f'<Project {self.id}: {self.name}>'
