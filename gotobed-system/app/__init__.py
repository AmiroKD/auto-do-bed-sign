import os
from flask import Flask
from flask_login import LoginManager

from .models import db

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # 数据目录
    data_dir = os.path.join(app.root_path, 'data')
    os.makedirs(data_dir, exist_ok=True)

    # 加载配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///' + os.path.join(data_dir, 'gotobed.db')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin123')
    app.config['FERNET_KEY'] = os.environ.get('FERNET_KEY', '')
    app.config['SMTP_HOST'] = os.environ.get('SMTP_HOST', 'smtp.qq.com')
    app.config['SMTP_PORT'] = int(os.environ.get('SMTP_PORT', '465'))
    app.config['SMTP_USER'] = os.environ.get('SMTP_USER', '')
    app.config['SMTP_PASS'] = os.environ.get('SMTP_PASS', '')

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # 注册蓝图
    from .routes import register_blueprints
    register_blueprints(app)

    # 初始化调度器
    from .scheduler import init_scheduler
    init_scheduler(app)

    # 创建数据库表
    with app.app_context():
        db.create_all()

    return app
