#!/usr/bin/env python3
"""
创建测试用户脚本
"""

# 直接导入和使用Flask应用
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import enum
import secrets
import jwt
from datetime import datetime, timedelta

# 创建数据库实例
db = SQLAlchemy()

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    RESEARCHER = "researcher"

class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

# 定义用户模型
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def set_password(self, password):
        """设置密码（自动加密）"""
        self.password_hash = generate_password_hash(password)

def create_test_user():
    # 创建Flask应用
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///battery_lab.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev-secret-key'

    # 初始化数据库
    db.init_app(app)

    with app.app_context():
        # 创建表
        db.create_all()

        # 检查是否已存在测试用户
        existing_user = User.query.filter_by(username='testuser').first()
        if existing_user:
            print("测试用户已存在")
            print(f"用户名: testuser")
            print(f"邮箱: {existing_user.email}")
            return

        # 创建测试用户
        test_user = User(
            username='testuser',
            email='test@example.com',
            full_name='测试用户',
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        test_user.set_password('Test123456')

        try:
            db.session.add(test_user)
            db.session.commit()
            print("测试用户创建成功！")
            print("用户名: testuser")
            print("邮箱: test@example.com")
            print("密码: Test123456")
        except Exception as e:
            print(f"创建用户失败: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_test_user()