import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("数据库连接检查")
print("=" * 60)

print(f"\n环境变量 DATABASE_URL: {os.getenv('DATABASE_URL')}")

# 直接创建Flask应用
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    print(f"\nFlask配置的 SQLALCHEMY_DATABASE_URI:")
    print(f"  {app.config.get('SQLALCHEMY_DATABASE_URI')}")

    print(f"\n数据库引擎:")
    print(f"  {db.engine.url}")

    # 检查表是否存在
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()

    print(f"\n数据库中的所有表:")
    for table in sorted(tables):
        print(f"  - {table}")

    # 检查 requirement_details 表结构
    if 'requirement_details' in tables:
        print(f"\nrequirement_details 表结构:")
        columns = inspector.get_columns('requirement_details')
        for col in columns:
            print(f"  - {col['name']}: {col['type']} (nullable: {col['nullable']})")

        # 检查外键
        foreign_keys = inspector.get_foreign_keys('requirement_details')
        if foreign_keys:
            print(f"\nrequirement_details 外键:")
            for fk in foreign_keys:
                print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
    else:
        print(f"\n⚠️  requirement_details 表不存在！")

print("\n" + "=" * 60)
