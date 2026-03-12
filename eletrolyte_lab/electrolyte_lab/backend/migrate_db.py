#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
添加缺失的字段到现有表
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def migrate_database():
    """迁移数据库，添加缺失的字段"""
    app = create_app()

    with app.app_context():
        print("开始数据库迁移...")

        try:
            inspector = db.inspect(db.engine)

            # 检查 users 表
            if 'users' in inspector.get_table_names():
                columns = inspector.get_columns('users')
                column_names = [col['name'] for col in columns]

                print("\n当前 users 表字段:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")

                # 需要添加的字段
                missing_fields = []

                # password_hash
                if 'password_hash' not in column_names:
                    missing_fields.append(('password_hash', 'VARCHAR(255)'))

                # first_name
                if 'first_name' not in column_names:
                    missing_fields.append(('first_name', 'VARCHAR(50)'))

                # last_name
                if 'last_name' not in column_names:
                    missing_fields.append(('last_name', 'VARCHAR(50)'))

                # phone
                if 'phone' not in column_names:
                    missing_fields.append(('phone', 'VARCHAR(20)'))

                # role (enum)
                if 'role' not in column_names:
                    missing_fields.append(('role', "VARCHAR(20) DEFAULT 'user'"))

                # status (enum)
                if 'status' not in column_names:
                    missing_fields.append(('status', "VARCHAR(50) DEFAULT 'pending_verification'"))

                # email_verified
                if 'email_verified' not in column_names:
                    missing_fields.append(('email_verified', 'BOOLEAN DEFAULT FALSE'))

                # email_verification_token
                if 'email_verification_token' not in column_names:
                    missing_fields.append(('email_verification_token', 'VARCHAR(255)'))

                # email_verification_expires
                if 'email_verification_expires' not in column_names:
                    missing_fields.append(('email_verification_expires', 'TIMESTAMP'))

                # last_login
                if 'last_login' not in column_names:
                    missing_fields.append(('last_login', 'TIMESTAMP'))

                # last_activity
                if 'last_activity' not in column_names:
                    missing_fields.append(('last_activity', 'TIMESTAMP'))

                # created_at
                if 'created_at' not in column_names:
                    missing_fields.append(('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))

                # updated_at
                if 'updated_at' not in column_names:
                    missing_fields.append(('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))

                if missing_fields:
                    print(f"\n需要添加 {len(missing_fields)} 个字段:")
                    for field, type_def in missing_fields:
                        print(f"  - {field}: {type_def}")

                    # 执行 ALTER TABLE 添加字段
                    with db.engine.connect() as conn:
                        for field_name, field_type in missing_fields:
                            try:
                                sql = f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"
                                conn.execute(db.text(sql))
                                conn.commit()
                                print(f"✅ 已添加字段: {field_name}")
                            except Exception as e:
                                print(f"❌ 添加字段 {field_name} 失败: {str(e)}")

                    print("\n✅ 迁移完成！")
                else:
                    print("\n✅ 所有字段都已存在，无需迁移")

            else:
                print("❌ users 表不存在，请先运行 init_db.py 创建表")

        except Exception as e:
            print(f"\n❌ 迁移失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

        return True

if __name__ == '__main__':
    print("=" * 60)
    print("数据库迁移工具")
    print("=" * 60)
    print("\n此脚本将为现有的 users 表添加缺失的字段")
    print("不会删除任何现有数据\n")

    response = input("是否继续？(yes/no): ")
    if response.lower() == 'yes':
        migrate_database()
    else:
        print("操作已取消")
