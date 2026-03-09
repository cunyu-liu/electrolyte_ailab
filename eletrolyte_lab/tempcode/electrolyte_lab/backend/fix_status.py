# -*- coding: utf-8 -*-
"""
修复数据库中的状态值为大写（Enum name）
"""
import os
import re

# Read .env file
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

# Get database config
database_url = os.getenv('DATABASE_URL', '')
match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
DB_USER = match.group(1)
DB_PASSWORD = match.group(2)
DB_HOST = match.group(3)
DB_PORT = int(match.group(4))
DB_NAME = match.group(5)

try:
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

    # Check current users
    cursor.execute("SELECT username, role, status FROM users")
    users = cursor.fetchall()

    print("Current users:")
    for user in users:
        print(f"  {user[0]}: role='{user[1]}', status='{user[2]}'")

    # Update status to uppercase (Enum names)
    print("\nUpdating status values to Enum names (uppercase)...")

    # active -> ACTIVE
    cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE status = 'active'")
    print(f"  Updated {cursor.rowcount} rows: 'active' -> 'ACTIVE'")

    # inactive -> INACTIVE
    cursor.execute("UPDATE users SET status = 'INACTIVE' WHERE status = 'inactive'")
    print(f"  Updated {cursor.rowcount} rows: 'inactive' -> 'INACTIVE'")

    # suspended -> SUSPENDED
    cursor.execute("UPDATE users SET status = 'SUSPENDED' WHERE status = 'suspended'")
    print(f"  Updated {cursor.rowcount} rows: 'suspended' -> 'SUSPENDED'")

    # pending_verification -> PENDING_VERIFICATION
    cursor.execute("UPDATE users SET status = 'PENDING_VERIFICATION' WHERE status = 'pending_verification'")
    print(f"  Updated {cursor.rowcount} rows: 'pending_verification' -> 'PENDING_VERIFICATION'")

    # Verify updates
    cursor.execute("SELECT username, role, status FROM users")
    users = cursor.fetchall()

    print("\nUpdated users:")
    for user in users:
        print(f"  {user[0]}: role='{user[1]}', status='{user[2]}'")

    print("\nStatus values have been updated to Enum names!")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
