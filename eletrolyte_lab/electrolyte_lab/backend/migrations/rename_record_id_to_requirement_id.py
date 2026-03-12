"""
数据库迁移脚本：将 requirement_details 表的 record_id 字段重命名为 requirement_id
"""

# SQL语句（在PostgreSQL中执行）：
sql_migration = """
-- 重命名列
ALTER TABLE requirement_details RENAME COLUMN record_id TO requirement_id;

-- 如果需要，添加外键约束（如果还没有的话）
ALTER TABLE requirement_details
ADD CONSTRAINT fk_requirement_details_requirement_id
FOREIGN KEY (requirement_id) REFERENCES requirement(requirement_id);
"""

print("请执行以下SQL语句来更新数据库表结构：")
print(sql_migration)

# 使用Flask应用上下文执行迁移
def migrate():
    from extensions import db
    from app_bk import create_app

    app = create_app()
    with app.app_context():
        try:
            # 检查字段是否存在
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('requirement_details')]
            print(f"当前 requirement_details 表的字段: {columns}")

            if 'record_id' in columns and 'requirement_id' not in columns:
                # 执行重命名
                db.session.execute(db.text("ALTER TABLE requirement_details RENAME COLUMN record_id TO requirement_id"))
                db.session.commit()
                print("✓ 成功将 record_id 重命名为 requirement_id")
            elif 'requirement_id' in columns:
                print("✓ requirement_id 字段已存在，无需迁移")
            else:
                print("✗ 警告: 既没有 record_id 也没有 requirement_id 字段")

        except Exception as e:
            db.session.rollback()
            print(f"✗ 迁移失败: {str(e)}")
            raise

if __name__ == "__main__":
    migrate()
