#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建或更新数据库表结构
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models.user import User, PasswordReset, UserSession

# 尝试导入其他模型（可能不存在）
try:
    from models.experiment import Experiment
except ImportError:
    Experiment = None

try:
    from models.formula import Formula
except ImportError:
    Formula = None

try:
    from models.requirement import Requirement
except ImportError:
    Requirement = None

def init_database():
    """初始化数据库"""
    app = create_app()

    with app.app_context():
        print("开始初始化数据库...")

        try:
            # 删除所有表（警告：会丢失所有数据！）
            print("正在删除旧表...")
            db.drop_all()
            print("旧表已删除")

            # 创建所有表
            print("正在创建新表...")
            db.create_all()
            print("新表创建成功")

            # 创建默认管理员账户
            print("\n创建默认管理员账户...")
            admin = User(
                username='admin',
                email='admin@electrolyte.lab',
                full_name='系统管理员',
                role='admin',
                status='active',
                email_verified=True
            )
            admin.set_password('Admin123456')

            db.session.add(admin)
            db.session.commit()

            print("✅ 默认管理员账户创建成功！")
            print("   用户名: admin")
            print("   密码: Admin123456")
            print("   邮箱: admin@electrolyte.lab")

            # 显示所有创建的表
            print("\n已创建的表:")
            inspector = db.inspect(db.engine)
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                print(f"  - {table_name} ({len(columns)} 个字段)")

            print("\n✅ 数据库初始化完成！")
            return True

        except Exception as e:
            print(f"\n❌ 数据库初始化失败: {str(e)}")
            db.session.rollback()
            return False

def check_database():
    """检查数据库表结构"""
    app = create_app()

    with app.app_context():
        print("检查数据库表结构...")

        try:
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            print(f"\n数据库中的表 ({len(tables)} 个):")
            for table_name in tables:
                columns = inspector.get_columns(table_name)
                print(f"\n  {table_name}:")
                for column in columns:
                    print(f"    - {column['name']}: {column['type']}")

            # 检查 users 表的 password_hash 字段
            if 'users' in tables:
                columns = inspector.get_columns('users')
                column_names = [col['name'] for col in columns]

                print("\n检查 users 表关键字段:")
                required_fields = [
                    'id', 'username', 'email', 'password_hash',
                    'role', 'status', 'email_verified'
                ]

                for field in required_fields:
                    if field in column_names:
                        print(f"  ✅ {field}")
                    else:
                        print(f"  ❌ {field} - 缺失！")

        except Exception as e:
            print(f"❌ 检查数据库失败: {str(e)}")
            return False

        return True

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='数据库管理工具')
    parser.add_argument(
        '--check',
        action='store_true',
        help='检查数据库表结构'
    )
    parser.add_argument(
        '--init',
        action='store_true',
        help='初始化数据库（警告：会删除所有数据）'
    )

    args = parser.parse_args()

    if args.check:
        check_database()
    elif args.init:
        print("⚠️  警告：此操作将删除所有数据！")
        confirm = input("确定要继续吗？(yes/no): ")
        if confirm.lower() == 'yes':
            init_database()
        else:
            print("操作已取消")
    else:
        # 默认执行检查
        check_database()
        print("\n使用 --init 初始化数据库，使用 --check 检查数据库")
