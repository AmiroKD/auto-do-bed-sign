from cryptography.fernet import Fernet
from flask import current_app


def _get_fernet():
    """获取 Fernet 实例，密钥从配置读取"""
    key = current_app.config['FERNET_KEY']
    if not key:
        raise RuntimeError('FERNET_KEY 未配置，请在环境变量中设置')
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_password(plain_text: str) -> str:
    """加密密码，返回加密后的字符串"""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_password(encrypted_text: str) -> str:
    """解密密码，返回明文"""
    f = _get_fernet()
    return f.decrypt(encrypted_text.encode()).decode()
