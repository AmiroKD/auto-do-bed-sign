import os


class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # 数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///data/gotobed.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 管理员密码
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

    # Fernet 密码加密密钥
    FERNET_KEY = os.environ.get('FERNET_KEY', '')

    # SMTP 邮件配置
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.qq.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASS = os.environ.get('SMTP_PASS', '')

    # APScheduler
    SCHEDULER_API_ENABLED = False
