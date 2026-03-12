"""
重新创建 requirement_details 表，去掉外键约束
运行：python recreate_requirement_details.py
"""
from app import create_app
from extensions import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recreate_requirement_details_table():
    """重新创建 requirement_details 表"""
    app = create_app()

    with app.app_context():
        try:
            # 1. 备份现有数据（如果表存在）
            backup_data = []
            try:
                result = db.session.execute(db.text("SELECT * FROM requirement_details"))
                columns = result.keys()
                for row in result:
                    backup_data.append(dict(zip(columns, row)))
                logger.info(f"备份了 {len(backup_data)} 条现有记录")
            except Exception as e:
                logger.info(f"没有现有数据需要备份: {e}")

            # 2. 删除旧表
            try:
                db.session.execute(db.text("DROP TABLE IF EXISTS requirement_details"))
                db.session.commit()
                logger.info("删除旧表成功")
            except Exception as e:
                logger.error(f"删除旧表失败: {e}")
                db.session.rollback()

            # 3. 创建新表（使用新的模型定义）
            from models.requirement import RequirementDetail
            RequirementDetail.__table__.create(db.session.bind, checkfirst=False)
            db.session.commit()
            logger.info("创建新表成功")

            # 4. 恢复数据（如果需要）
            if backup_data:
                try:
                    for data in backup_data:
                        # 移除 id 字段，让数据库自动生成
                        data.pop('id', None)
                        db.session.execute(db.text("""
                            INSERT INTO requirement_details
                            (requirement_id, category, param_name, param_value, unit, range, confidence)
                            VALUES (:requirement_id, :category, :param_name, :param_value, :unit, :range, :confidence)
                        """), data)
                    db.session.commit()
                    logger.info(f"恢复了 {len(backup_data)} 条记录")
                except Exception as e:
                    logger.error(f"恢复数据失败: {e}")
                    db.session.rollback()

            # 5. 验证表结构
            result = db.session.execute(db.text("PRAGMA table_info(requirement_details)"))
            logger.info("\n新表结构:")
            for row in result:
                logger.info(f"  {row}")

            result = db.session.execute(db.text("PRAGMA foreign_key_list(requirement_details)"))
            fk_list = list(result)
            if not fk_list:
                logger.info("\n✓ 外键约束已成功移除")
            else:
                logger.warning(f"\n⚠ 仍存在外键约束: {fk_list}")

            logger.info("\n✓ requirement_details 表重建完成！")

        except Exception as e:
            logger.error(f"重建表失败: {e}")
            logger.error("错误详情: ", exc_info=True)
            db.session.rollback()

if __name__ == '__main__':
    recreate_requirement_details_table()
