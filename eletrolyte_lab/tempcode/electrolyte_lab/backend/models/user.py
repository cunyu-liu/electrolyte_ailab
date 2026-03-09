from datetime import datetime, timedelta
from extensions import db
from sqlalchemy import JSON
import enum
import hashlib
import secrets
import jwt
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    RESEARCHER = "researcher"

class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # 基本信息
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    # organization = db.Column(db.String(100))  # 临时注释掉
    avatar_url = db.Column(db.String(255))

    # 角色和状态
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)

    # 邮箱验证
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(255))
    email_verification_expires = db.Column(db.DateTime)

    # 最后活动时间
    last_login = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关联关系
    experiments = db.relationship('Experiment', backref='user', lazy=True)
    password_resets = db.relationship('PasswordReset', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """设置密码（自动加密）"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def generate_email_verification_token(self):
        """生成邮箱验证令牌"""
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_expires = datetime.now() + timedelta(hours=24)
        db.session.commit()
        return self.email_verification_token

    def verify_email_token(self, token):
        """验证邮箱令牌"""
        if (self.email_verification_token != token or
            self.email_verification_expires < datetime.now()):
            return False

        self.email_verified = True
        self.status = UserStatus.ACTIVE
        self.email_verification_token = None
        self.email_verification_expires = None
        db.session.commit()
        return True

    def generate_auth_token(self, expires_in=3600):
        """生成JWT认证令牌"""
        payload = {
            'user_id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_auth_token(token):
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload.get('user_id')
            if user_id:
                return User.query.get(user_id)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        return None

    def update_last_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()
        db.session.commit()

    def to_dict(self, include_sensitive=False):
        """转换为字典"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'organization': getattr(self, 'organization', None),  # 临时处理
            'avatar_url': self.avatar_url,
            'role': self.role.value if self.role else None,
            'status': self.status.value if self.status else None,
            'email_verified': self.email_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sensitive:
            data.update({
                'email_verification_token': self.email_verification_token,
                'email_verification_expires': self.email_verification_expires.isoformat() if self.email_verification_expires else None,
            })

        return data

class PasswordReset(db.Model):
    __tablename__ = 'password_resets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    @staticmethod
    def create_token(user):
        """创建密码重置令牌"""
        token = secrets.token_urlsafe(32)
        password_reset = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=datetime.now() + timedelta(hours=2)
        )
        db.session.add(password_reset)
        db.session.commit()
        return token

    def is_valid(self):
        """检查令牌是否有效"""
        return not self.used and self.expires_at > datetime.now()

    def mark_as_used(self):
        """标记令牌为已使用"""
        self.used = True
        db.session.commit()

class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    refresh_token = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='sessions')

    @staticmethod
    def create_session(user, ip_address=None, user_agent=None):
        """创建用户会话"""
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        session = UserSession(
            user_id=user.id,
            session_token=session_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now() + timedelta(days=7)
        )

        db.session.add(session)
        db.session.commit()
        return session

    def is_valid(self):
        """检查会话是否有效"""
        return self.expires_at > datetime.now()

    def extend_session(self, days=7):
        """延长会话"""
        self.expires_at = datetime.now() + timedelta(days=days)
        self.last_activity = datetime.now()
        db.session.commit()

    def revoke(self):
        """撤销会话"""
        db.session.delete(self)
        db.session.commit()