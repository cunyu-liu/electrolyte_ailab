#!/usr/bin/env python3
"""
创建默认管理员用户脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_bk import create_app
from models.user import User, UserRole, UserStatus
from extensions import db
from werkzeug.security import generate_password_hash

def create_admin_user():
    """创建默认管理员用户"""
    app = create_app()

    with app.app_context():
        # 检查是否已存在admin用户
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("管理员用户已存在，跳过创建")
            print(f"用户名: {existing_admin.username}")
            print(f"邮箱: {existing_admin.email}")
            return

        # 创建管理员用户
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('Admin123!'),
            full_name='系统管理员',
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True  # 管理员用户默认邮箱已验证
        )

        db.session.add(admin_user)
        db.session.commit()

        print("✅ 默认管理员用户创建成功！")
        print("📋 登录信息:")
        print("   用户名: admin")
        print("   密码: Admin123!")
        print("   邮箱: admin@example.com")
        print("   角色: 管理员")
        print("   状态: 已激活")

if __name__ == '__main__':
    try:
        create_admin_user()
        print("\n🎉 初始化完成！")
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        sys.exit(1)