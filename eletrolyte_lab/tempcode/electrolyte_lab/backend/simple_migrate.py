#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的数据库迁移脚本
直接连接数据库，不依赖 Flask app
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def get_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'electrolyte_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password')
    )

def check_and_migrate():
    """检查并迁移数据库"""
    conn = get_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        # 检查 users 表是否存在
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'users';
        """)

        if not cursor.fetchone():
            print("❌ users 表不存在")
            print("\n请先创建数据库表。运行以下 SQL：\n")
            print("-- 创建 users 表的 SQL")
            print("CREATE TABLE users (")
            print("    id SERIAL PRIMARY KEY,")
            print("    username VARCHAR(80) UNIQUE NOT NULL,")
            print("    email VARCHAR(120) UNIQUE NOT NULL,")
            print("    password_hash VARCHAR(255) NOT NULL,")
            print("    first_name VARCHAR(50),")
            print("    last_name VARCHAR(50),")
            print("    full_name VARCHAR(100),")
            print("    phone VARCHAR(20),")
            print("    avatar_url VARCHAR(255),")
            print("    role VARCHAR(20) DEFAULT 'user',")
            print("    status VARCHAR(50) DEFAULT 'pending_verification',")
            print("    email_verified BOOLEAN DEFAULT FALSE,")
            print("    email_verification_token VARCHAR(255),")
            print("    email_verification_expires TIMESTAMP,")
            print("    last_login TIMESTAMP,")
            print("    last_activity TIMESTAMP,")
            print("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,")
            print("    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print(");")
            return

        # 获取当前表结构
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]

        print("\n当前 users 表字段:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}{'(' + str(col[2]) + ')' if col[2] else ''}")

        # 需要添加的字段
        missing_fields = []

        # 定义所有需要的字段
        required_fields = {
            'password_hash': 'VARCHAR(255)',
            'first_name': 'VARCHAR(50)',
            'last_name': 'VARCHAR(50)',
            'full_name': 'VARCHAR(100)',
            'phone': 'VARCHAR(20)',
            'avatar_url': 'VARCHAR(255)',
            'role': "VARCHAR(20) DEFAULT 'user'",
            'status': "VARCHAR(50) DEFAULT 'pending_verification'",
            'email_verified': 'BOOLEAN DEFAULT FALSE',
            'email_verification_token': 'VARCHAR(255)',
            'email_verification_expires': 'TIMESTAMP',
            'last_login': 'TIMESTAMP',
            'last_activity': 'TIMESTAMP',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }

        for field_name, field_type in required_fields.items():
            if field_name not in column_names:
                missing_fields.append((field_name, field_type))

        if missing_fields:
            print(f"\n需要添加 {len(missing_fields)} 个字段:")
            for field, type_def in missing_fields:
                print(f"  - {field}: {type_def}")

            print("\n开始添加字段...")

            for field_name, field_type in missing_fields:
                try:
                    sql = f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"
                    cursor.execute(sql)
                    print(f"✅ 已添加字段: {field_name}")
                except Exception as e:
                    print(f"❌ 添加字段 {field_name} 失败: {str(e)}")

            print("\n✅ 迁移完成！")

            # 创建默认管理员账户
            print("\n是否创建默认管理员账户？")
            print("  用户名: admin")
            print("  密码: Admin123456")
            print("  邮箱: admin@electrolyte.lab")

            # 生成密码哈希（简单版本）
            import hashlib
            password_hash = hashlib.sha256('Admin123456'.encode()).hexdigest()

            # 检查是否已存在 admin 用户
            cursor.execute("SELECT id FROM users WHERE username = 'admin' OR email = 'admin@electrolyte.lab'")
            if cursor.fetchone():
                print("\n⚠️  admin 用户已存在，跳过创建")
            else:
                try:
                    cursor.execute("""
                        INSERT INTO users (
                            username, email, password_hash, full_name,
                            role, status, email_verified
                        ) VALUES (
                            'admin', 'admin@electrolyte.lab', %s, '系统管理员',
                            'admin', 'active', TRUE
                        )
                    """, (password_hash,))
                    print("\n✅ 默认管理员账户创建成功！")
                    print("   用户名: admin")
                    print("   密码: Admin123456 (使用简单哈希，请在登录后修改)")
                except Exception as e:
                    print(f"\n❌ 创建管理员账户失败: {str(e)}")

        else:
            print("\n✅ 所有字段都已存在，无需迁移")

        # 显示所有用户
        cursor.execute("SELECT id, username, email, role, status FROM users ORDER BY id")
        users = cursor.fetchall()

        if users:
            print(f"\n当前用户 ({len(users)} 个):")
            for user in users:
                print(f"  ID: {user[0]}, 用户名: {user[1]}, 邮箱: {user[2]}, 角色: {user[3]}, 状态: {user[4]}")
        else:
            print("\n当前没有用户")

    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()

    return True

if __name__ == '__main__':
    print("=" * 60)
    print("数据库迁移工具")
    print("=" * 60)
    print("\n此脚本将为现有的 users 表添加缺失的字段")

    try:
        check_and_migrate()
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        print("\n请检查数据库连接配置:")
        print("  - DB_HOST")
        print("  - DB_PORT")
        print("  - DB_NAME")
        print("  - DB_USER")
        print("  - DB_PASSWORD")
