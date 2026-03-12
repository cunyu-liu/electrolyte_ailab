from functools import wraps
from flask import request, jsonify, current_app
from models.user import User, UserSession
import jwt

def token_required(f):
    """JWT令牌认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # 从请求头获取令牌
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': '令牌格式错误'}), 401

        if not token:
            return jsonify({'error': '缺少认证令牌'}), 401

        try:
            # 验证令牌
            current_user = User.verify_auth_token(token)
            if not current_user:
                return jsonify({'error': '令牌无效或已过期'}), 401

            # 检查用户状态
            if current_user.status.value != 'active':
                return jsonify({'error': '用户账户已被禁用'}), 401

            # 更新最后活动时间
            current_user.update_last_activity()

        except Exception as e:
            return jsonify({'error': f'令牌验证失败: {str(e)}'}), 401

        # 将当前用户添加到请求上下文
        request.current_user = current_user
        return f(*args, **kwargs)

    return decorated_function

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 首先检查令牌
        token_result = token_required(lambda: None)()
        if isinstance(token_result, tuple):  # 如果返回错误响应
            return token_result

        # 检查是否为管理员
        if not request.current_user or request.current_user.role.value != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403

        return f(*args, **kwargs)

    return decorated_function

def role_required(*allowed_roles):
    """角色权限装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 首先检查令牌
            token_result = token_required(lambda: None)()
            if isinstance(token_result, tuple):  # 如果返回错误响应
                return token_result

            # 检查用户角色
            user_role = request.current_user.role.value
            if user_role not in allowed_roles:
                return jsonify({'error': f'需要以下权限之一: {", ".join(allowed_roles)}'}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator

def get_current_user():
    """获取当前用户"""
    if hasattr(request, 'current_user'):
        return request.current_user
    return None

def validate_email(email):
    """验证邮箱格式"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """验证密码强度"""
    if len(password) < 8:
        return False, "密码长度至少8位"

    if len(password) > 128:
        return False, "密码长度不能超过128位"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper and has_lower and has_digit):
        return False, "密码必须包含大小写字母和数字"

    return True, "密码格式正确"

def generate_tokens(user):
    """生成访问令牌和刷新令牌"""
    access_token = user.generate_auth_token(expires_in=3600)  # 1小时
    refresh_token = user.generate_auth_token(expires_in=86400 * 7)  # 7天

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 3600
    }

def refresh_access_token(refresh_token):
    """刷新访问令牌"""
    try:
        user = User.verify_auth_token(refresh_token)
        if not user:
            return None, "刷新令牌无效"

        # 生成新的访问令牌
        new_access_token = user.generate_auth_token(expires_in=3600)

        return {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': 3600
        }, None

    except Exception as e:
        return None, f"令牌刷新失败: {str(e)}"

def create_user_session(user, ip_address=None, user_agent=None):
    """创建用户会话"""
    session = UserSession.create_session(user, ip_address, user_agent)
    return session

def revoke_user_session(session_token):
    """撤销用户会话"""
    session = UserSession.query.filter_by(session_token=session_token).first()
    if session:
        session.revoke()
        return True
    return False

def revoke_all_user_sessions(user_id):
    """撤销用户所有会话"""
    sessions = UserSession.query.filter_by(user_id=user_id).all()
    for session in sessions:
        session.revoke()
    return len(sessions)

def cleanup_expired_sessions():
    """清理过期会话"""
    from models.user import UserSession, datetime
    expired_sessions = UserSession.query.filter(
        UserSession.expires_at < datetime.now()
    ).all()

    for session in expired_sessions:
        db.session.delete(session)

    db.session.commit()
    return len(expired_sessions)