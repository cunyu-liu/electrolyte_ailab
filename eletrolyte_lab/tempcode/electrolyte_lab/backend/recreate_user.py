#!/usr/bin/env python3

from app_bk import create_app
from models.user import User, UserRole, UserStatus
from extensions import db

def recreate_user():
    app = create_app()

    with app.app_context():
        # 删除现有的测试用户
        existing_user = User.query.filter_by(username='testuser').first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
            print("删除了现有测试用户")

        # 创建新的测试用户
        test_user = User(
            username='testuser',
            email='test@example.com',
            full_name='测试用户',
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        test_user.set_password('Test123456')

        try:
            db.session.add(test_user)
            db.session.commit()
            print("新测试用户创建成功！")
            print("用户名: testuser")
            print("邮箱: test@example.com")
            print("密码: Test123456")

            # 验证用户创建
            created_user = User.query.filter_by(username='testuser').first()
            if created_user and created_user.check_password('Test123456'):
                print("密码验证成功！")
            else:
                print("密码验证失败！")

        except Exception as e:
            print(f"创建用户失败: {e}")
            db.session.rollback()

if __name__ == '__main__':
    recreate_user()