"""
Sample Python module for CodeRAG-Agent testing
用户认证和会话管理模块
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class User:
    """用户数据类"""
    user_id: str
    username: str
    email: str
    password_hash: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    roles: List[str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = ["user"]


class AuthManager:
    """
    认证管理器
    负责用户注册、登录、登出、令牌管理
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_hex(32)
        self.users: Dict[str, User] = {}
        self.tokens: Dict[str, str] = {}
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = self.secret_key[:16]
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self.hash_password(password) == password_hash
    
    def register(self, username: str, email: str, password: str) -> Optional[User]:
        """注册新用户"""
        if any(u.username == username for u in self.users.values()):
            return None
        
        user_id = secrets.token_urlsafe(16)
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=self.hash_password(password),
            created_at=datetime.now(),
        )
        self.users[user_id] = user
        return user
    
    def login(self, username: str, password: str) -> Optional[str]:
        """用户登录"""
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break
        
        if not user or not self.verify_password(password, user.password_hash):
            return None
        
        token = secrets.token_urlsafe(32)
        self.tokens[token] = user.user_id
        user.last_login = datetime.now()
        return token
    
    def verify_token(self, token: str) -> Optional[User]:
        """验证令牌"""
        if token not in self.tokens:
            return None
        return self.users.get(self.tokens[token])


if __name__ == "__main__":
    auth = AuthManager()
    user = auth.register("alice", "alice@example.com", "password123")
    print(f"注册用户: {user.username}")
    token = auth.login("alice", "password123")
    print(f"登录令牌: {token}")
