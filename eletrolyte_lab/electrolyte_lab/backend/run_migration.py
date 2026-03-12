# -*- coding: utf-8 -*-
"""
数据库迁移执行脚本
"""
import os
import sys

# 读取环境变量
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 获取数据库配置
database_url = os.getenv('DATABASE_URL', '')
if database_url:
    # 解析 DATABASE_URL: postgresql://user:password@host:port/database
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if match:
        DB_USER = match.group(1)
        DB_PASSWORD = match.group(2)
        DB_HOST = match.group(3)
        DB_PORT = int(match.group(4))
        DB_NAME = match.group(5)
    else:
        # fallback
        DB_HOST = 'localhost'
        DB_PORT = 5432
        DB_NAME = 'postgres'
        DB_USER = 'postgres'
        DB_PASSWORD = '123456'
else:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'electrolyte_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

print("Database Configuration:")
print(f"  Host: {DB_HOST}")
print(f"  Port: {DB_PORT}")
print(f"  Database: {DB_NAME}")
print(f"  User: {DB_USER}")
print()

try:
    # 连接数据库
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    print("Successfully connected to database!\n")

    # 读取并执行 SQL 文件
    sql_file = os.path.join(os.path.dirname(__file__), 'add_user_fields.sql')
    if os.path.exists(sql_file):
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        print("Executing migration script...\n")
        cursor.execute(sql)
        conn.commit()

        print("Migration completed successfully!\n")

        # 显示当前 users 表的结构
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)

        columns = cursor.fetchall()
        print("Current users table structure:")
        for col in columns:
            print(f"  {col[0]}: {col[1]}")

        # 创建默认管理员（使用 werkzeug 的密码哈希）
        try:
            from werkzeug.security import generate_password_hash

            # 检查 admin 是否已存在
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                password_hash = generate_password_hash('Admin123456')
                cursor.execute("""
                    INSERT INTO users (username, email, password, password_hash, full_name, role, status, email_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, ('admin', 'admin@electrolyte.lab', password_hash, password_hash, 'System Admin', 'admin', 'active', True))

                print("\nDefault admin account created:")
                print("  Username: admin")
                print("  Password: Admin123456")
                print("  Email: admin@electrolyte.lab")
            else:
                print("\nAdmin account already exists")
        except ImportError:
            print("\nNote: werkzeug not installed, skipping admin account creation")
            print("Please install it with: pip install werkzeug")

    else:
        print(f"SQL file not found: {sql_file}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
