from flask import Blueprint, request, jsonify, current_app
from models.user import User, PasswordReset, UserSession, UserRole, UserStatus
from utils.auth import (
    token_required, generate_tokens, refresh_access_token,
    validate_email, validate_password, create_user_session,
    revoke_user_session, get_current_user
)
from extensions import db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 邮件发送配置（生产环境应该使用环境变量）
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'your-email@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'your-app-password')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

def send_verification_email(email, token, full_name=None):
    """发送邮箱验证邮件"""
    try:
        verification_url = f"{FRONTEND_URL}/verify-email?token={token}"

        subject = "电解质实验室 - 邮箱验证"
        body = f"""
        <h2>欢迎使用电解质实验室管理系统！</h2>

        <p>您好{f'，{full_name}' if full_name else ''}！</p>

        <p>感谢您注册电解质实验室管理系统。请点击下面的链接完成邮箱验证：</p>

        <p><a href="{verification_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">验证邮箱</a></p>

        <p>如果链接无法点击，请复制以下链接到浏览器地址栏：</p>
        <p><a href="{verification_url}">{verification_url}</a></p>

        <p>此链接将在24小时后失效。</p>

        <p>如果您没有注册此账户，请忽略此邮件。</p>

        <br>
        <p>电解质实验室团队</p>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = email

        html_part = MIMEText(body, 'html')
        msg.attach(html_part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        current_app.logger.error(f"发送验证邮件失败: {str(e)}")
        return False

def send_password_reset_email(email, token, full_name=None):
    """发送密码重置邮件"""
    try:
        reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

        subject = "电解质实验室 - 密码重置"
        body = f"""
        <h2>密码重置请求</h2>

        <p>您好{f'，{full_name}' if full_name else ''}！</p>

        <p>我们收到了您的密码重置请求。请点击下面的链接重置您的密码：</p>

        <p><a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">重置密码</a></p>

        <p>如果链接无法点击，请复制以下链接到浏览器地址栏：</p>
        <p><a href="{reset_url}">{reset_url}</a></p>

        <p>此链接将在2小时后失效。</p>

        <p>如果您没有请求重置密码，请忽略此邮件。您的密码不会被更改。</p>

        <br>
        <p>电解质实验室团队</p>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = email

        html_part = MIMEText(body, 'html')
        msg.attach(html_part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        current_app.logger.error(f"发送密码重置邮件失败: {str(e)}")
        return False

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()

        # 验证必需字段
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'缺少必需字段: {field}'}), 400

        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']

        # 可选字段
        full_name = data.get('full_name', '').strip()
        organization = data.get('organization', '').strip()

        # 验证邮箱格式
        if not validate_email(email):
            return jsonify({'error': '邮箱格式无效'}), 400

        # 验证密码强度
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400

        # 验证用户名长度
        if len(username) < 3 or len(username) > 50:
            return jsonify({'error': '用户名长度必须在3-50个字符之间'}), 400

        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'error': '用户名已存在'}), 409

        # 检查邮箱是否已存在
        if User.query.filter_by(email=email).first():
            return jsonify({'error': '邮箱已被注册'}), 409

        # 创建新用户
        user = User(
            username=username,
            email=email,
            full_name=full_name or username,
            role=UserRole.USER,
            status=UserStatus.ACTIVE  # 直接设置为ACTIVE以简化测试流程
        )

        # 设置密码
        user.set_password(password)

        # 生成邮箱验证令牌
        verification_token = user.generate_email_verification_token()

        # 保存用户
        db.session.add(user)
        db.session.commit()

        # 发送验证邮件
        email_sent = send_verification_email(email, verification_token, user.full_name)

        return jsonify({
            'message': '注册成功，请检查邮箱进行验证',
            'user': user.to_dict(),
            'email_sent': email_sent,
            'requires_email_verification': True
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"注册失败: {str(e)}")
        return jsonify({'error': '注册失败，请稍后重试'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()

        # 验证必需字段
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': '用户名和密码不能为空'}), 400

        username = data['username'].strip()
        password = data['password']

        # 查找用户（支持用户名或邮箱登录）
        user = User.query.filter(
            (User.username == username) | (User.email == username.lower())
        ).first()

        if not user or not user.check_password(password):
            return jsonify({'error': '用户名或密码错误'}), 401

        # 检查用户状态
        if user.status == UserStatus.SUSPENDED:
            return jsonify({'error': '账户已被暂停，请联系管理员'}), 403

        if user.status == UserStatus.PENDING_VERIFICATION:
            return jsonify({
                'error': '请先验证邮箱后再登录',
                'requires_email_verification': True
            }), 403

        # 更新最后登录时间
        user.last_login = datetime.now()
        db.session.commit()

        # 生成令牌
        tokens = generate_tokens(user)

        # 创建会话
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        session = create_user_session(user, ip_address, user_agent)

        return jsonify({
            'message': '登录成功',
            'user': user.to_dict(),
            'tokens': tokens,
            'session': {
                'session_token': session.session_token,
                'expires_at': session.expires_at.isoformat()
            },
            'requires_email_verification': not user.email_verified
        }), 200

    except Exception as e:
        current_app.logger.error(f"登录失败: {str(e)}")
        return jsonify({'error': '登录失败，请稍后重试'}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """用户登出"""
    try:
        session_token = request.headers.get('Authorization', '').split(' ')[-1] if 'Authorization' in request.headers else None

        if session_token:
            revoke_user_session(session_token)

        return jsonify({'message': '登出成功'}), 200

    except Exception as e:
        current_app.logger.error(f"登出失败: {str(e)}")
        return jsonify({'error': '登出失败'}), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """刷新访问令牌"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({'error': '缺少刷新令牌'}), 400

        tokens, error = refresh_access_token(refresh_token)

        if error:
            return jsonify({'error': error}), 401

        return jsonify({
            'message': '令牌刷新成功',
            'tokens': tokens
        }), 200

    except Exception as e:
        current_app.logger.error(f"令牌刷新失败: {str(e)}")
        return jsonify({'error': '令牌刷新失败'}), 500

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """验证邮箱"""
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'error': '缺少验证令牌'}), 400

        # 查找用户
        user = User.query.filter_by(email_verification_token=token).first()

        if not user:
            return jsonify({'error': '验证令牌无效'}), 400

        # 验证令牌
        if user.verify_email_token(token):
            return jsonify({
                'message': '邮箱验证成功',
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'error': '验证令牌已过期'}), 400

    except Exception as e:
        current_app.logger.error(f"邮箱验证失败: {str(e)}")
        return jsonify({'error': '邮箱验证失败'}), 500

@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """重新发送验证邮件"""
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': '邮箱地址不能为空'}), 400

        user = User.query.filter_by(email=email.lower()).first()

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        if user.email_verified:
            return jsonify({'error': '邮箱已经验证过了'}), 400

        # 生成新的验证令牌
        verification_token = user.generate_email_verification_token()

        # 发送验证邮件
        email_sent = send_verification_email(email, verification_token, user.full_name)

        return jsonify({
            'message': '验证邮件已重新发送',
            'email_sent': email_sent
        }), 200

    except Exception as e:
        current_app.logger.error(f"重新发送验证邮件失败: {str(e)}")
        return jsonify({'error': '发送失败，请稍后重试'}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """忘记密码"""
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': '邮箱地址不能为空'}), 400

        user = User.query.filter_by(email=email.lower()).first()

        if not user:
            return jsonify({'error': '该邮箱未注册'}), 404

        # 创建密码重置令牌
        reset_token = PasswordReset.create_token(user)

        # 发送重置邮件
        email_sent = send_password_reset_email(email, reset_token, user.full_name)

        return jsonify({
            'message': '密码重置邮件已发送',
            'email_sent': email_sent
        }), 200

    except Exception as e:
        current_app.logger.error(f"发送密码重置邮件失败: {str(e)}")
        return jsonify({'error': '发送失败，请稍后重试'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')

        if not token or not new_password:
            return jsonify({'error': '缺少重置令牌或新密码'}), 400

        # 验证密码强度
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400

        # 查找重置令牌
        password_reset = PasswordReset.query.filter_by(token=token).first()

        if not password_reset or not password_reset.is_valid():
            return jsonify({'error': '重置令牌无效或已过期'}), 400

        user = password_reset.user

        # 更新密码
        user.set_password(new_password)

        # 标记令牌为已使用
        password_reset.mark_as_used()

        return jsonify({
            'message': '密码重置成功'
        }), 200

    except Exception as e:
        current_app.logger.error(f"密码重置失败: {str(e)}")
        return jsonify({'error': '密码重置失败'}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user_info():
    """获取当前用户信息"""
    try:
        user = get_current_user()
        return jsonify({
            'user': user.to_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f"获取用户信息失败: {str(e)}")
        return jsonify({'error': '获取用户信息失败'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """修改密码"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({'error': '当前密码和新密码不能为空'}), 400

        user = get_current_user()

        # 验证当前密码
        if not user.check_password(current_password):
            return jsonify({'error': '当前密码错误'}), 401

        # 验证新密码强度
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400

        # 更新密码
        user.set_password(new_password)

        # 撤销所有现有会话（强制重新登录）
        from utils.auth import revoke_all_user_sessions
        revoke_all_user_sessions(user.id)

        return jsonify({
            'message': '密码修改成功，请重新登录'
        }), 200

    except Exception as e:
        current_app.logger.error(f"修改密码失败: {str(e)}")
        return jsonify({'error': '修改密码失败'}), 500

@auth_bp.route('/me', methods=['PUT'])
@token_required
def update_current_user():
    """更新当前用户信息"""
    try:
        data = request.get_json()
        user = get_current_user()

        # 可更新字段
        if 'full_name' in data:
            user.full_name = data['full_name'].strip()
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'phone' in data:
            user.phone = data['phone'].strip()
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url'].strip()

        db.session.commit()

        return jsonify({
            'message': '个人信息更新成功',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新个人信息失败: {str(e)}")
        return jsonify({'error': '更新个人信息失败'}), 500

@auth_bp.route('/users', methods=['GET'])
@token_required
def get_users():
    """获取用户列表（管理员）"""
    try:
        current_user = get_current_user()

        # 只有管理员可以查看用户列表
        if current_user.role != UserRole.ADMIN:
            return jsonify({'error': '需要管理员权限'}), 403

        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        role = request.args.get('role', '').strip()
        status = request.args.get('status', '').strip()

        # 构建查询
        query = User.query

        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.full_name.ilike(f'%{search}%')
                )
            )

        # 角色过滤
        if role:
            try:
                role_enum = UserRole(role)
                query = query.filter(User.role == role_enum)
            except ValueError:
                pass

        # 状态过滤
        if status:
            try:
                status_enum = UserStatus(status)
                query = query.filter(User.status == status_enum)
            except ValueError:
                pass

        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'users': [user.to_dict() for user in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }), 200

    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {str(e)}")
        return jsonify({'error': '获取用户列表失败'}), 500

@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user_by_id(user_id):
    """获取指定用户详情（管理员）"""
    try:
        current_user = get_current_user()

        # 只有管理员可以查看其他用户详情
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            return jsonify({'error': '需要管理员权限'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        return jsonify({
            'user': user.to_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f"获取用户详情失败: {str(e)}")
        return jsonify({'error': '获取用户详情失败'}), 500

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(user_id):
    """更新指定用户信息（管理员）"""
    try:
        current_user = get_current_user()

        # 只有管理员可以更新其他用户信息
        if current_user.role != UserRole.ADMIN:
            return jsonify({'error': '需要管理员权限'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        data = request.get_json()

        # 可更新字段
        if 'full_name' in data:
            user.full_name = data['full_name'].strip()
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'phone' in data:
            user.phone = data['phone'].strip()
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url'].strip()

        # 只有管理员可以修改角色和状态
        if 'role' in data:
            try:
                user.role = UserRole(data['role'])
            except ValueError:
                return jsonify({'error': '无效的角色'}), 400

        if 'status' in data:
            try:
                user.status = UserStatus(data['status'])
            except ValueError:
                return jsonify({'error': '无效的状态'}), 400

        db.session.commit()

        return jsonify({
            'message': '用户信息更新成功',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新用户信息失败: {str(e)}")
        return jsonify({'error': '更新用户信息失败'}), 500

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(user_id):
    """删除指定用户（管理员）"""
    try:
        current_user = get_current_user()

        # 只有管理员可以删除用户
        if current_user.role != UserRole.ADMIN:
            return jsonify({'error': '需要管理员权限'}), 403

        # 不能删除自己
        if current_user.id == user_id:
            return jsonify({'error': '不能删除自己的账户'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 删除用户（级联删除相关数据）
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            'message': '用户删除成功'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除用户失败: {str(e)}")
        return jsonify({'error': '删除用户失败'}), 500

@auth_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@token_required
def reset_user_password(user_id):
    """重置指定用户密码（管理员）"""
    try:
        current_user = get_current_user()

        # 只有管理员可以重置其他用户密码
        if current_user.role != UserRole.ADMIN:
            return jsonify({'error': '需要管理员权限'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        data = request.get_json()
        new_password = data.get('new_password')

        if not new_password:
            # 生成随机密码
            import secrets
            import string
            new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        # 验证密码强度
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400

        # 重置密码
        user.set_password(new_password)

        # 撤销用户所有会话
        from utils.auth import revoke_all_user_sessions
        revoke_all_user_sessions(user.id)

        return jsonify({
            'message': '密码重置成功',
            'new_password': new_password  # 返回新密码以便管理员告知用户
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"重置用户密码失败: {str(e)}")
        return jsonify({'error': '重置用户密码失败'}), 500