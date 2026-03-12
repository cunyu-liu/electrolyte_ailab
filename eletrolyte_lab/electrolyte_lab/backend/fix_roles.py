# -*- coding: utf-8 -*-
"""
修复数据库中的角色值为大写
"""
import os
import sys
import re

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
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if match:
        DB_USER = match.group(1)
        DB_PASSWORD = match.group(2)
        DB_HOST = match.group(3)
        DB_PORT = int(match.group(4))
        DB_NAME = match.group(5)
    else:
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

    # 查看当前所有用户及其角色
    cursor.execute("SELECT id, username, email, role FROM users ORDER BY id")
    users = cursor.fetchall()

    print("Current users and their roles:")
    for user in users:
        print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Role: '{user[3]}'")

    # 更新角色值为大写
    print("\nUpdating role values to uppercase...")

    # 更新 admin -> ADMIN
    cursor.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'admin'")
    print(f"  Updated {cursor.rowcount} rows: 'admin' -> 'ADMIN'")

    # 更新 user -> USER
    cursor.execute("UPDATE users SET role = 'USER' WHERE role = 'user'")
    print(f"  Updated {cursor.rowcount} rows: 'user' -> 'USER'")

    # 更新 researcher -> RESEARCHER
    cursor.execute("UPDATE users SET role = 'RESEARCHER' WHERE role = 'researcher'")
    print(f"  Updated {cursor.rowcount} rows: 'researcher' -> 'RESEARCHER'")

    # 验证更新
    cursor.execute("SELECT id, username, email, role FROM users ORDER BY id")
    users = cursor.fetchall()

    print("\nUpdated users and their roles:")
    for user in users:
        print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Role: '{user[3]}'")

    print("\n✅ Role values have been updated to uppercase!")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
