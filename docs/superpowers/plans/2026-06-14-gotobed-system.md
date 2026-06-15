# 查寝管理系统 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个自托管的查寝管理系统，提供 Web 管理界面和定时任务调度，替代 GitHub Actions 方案。

**Architecture:** Flask 单体应用，APScheduler 进程内调度，SQLite 存储用户和日志，Docker 单容器部署。核心查寝逻辑从原 `goToBed.py` 重构为函数调用。

**Tech Stack:** Python 3.11, Flask, Flask-Login, Flask-SQLAlchemy, APScheduler, SQLite, cryptography (Fernet), Bootstrap 5, Docker, Gunicorn

**设计文档:** `docs/superpowers/specs/2026-06-14-gotobed-system-design.md`

---

## 文件结构总览

```
gotobed-system/
├── app/
│   ├── __init__.py          # Flask app 工厂 + 扩展初始化
│   ├── models.py            # SQLAlchemy 模型 (User, Log)
│   ├── crypto.py            # Fernet 密码加密工具
│   ├── email_sender.py      # 邮件发送（重构自 emailSender.py）
│   ├── routes/
│   │   ├── __init__.py      # 注册所有蓝图
│   │   ├── auth.py          # 登录/登出路由
│   │   ├── users.py         # 用户 CRUD 路由
│   │   └── logs.py          # 日志查看路由
│   ├── scheduler.py         # APScheduler 集成 + 查寝调度
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── gotobed.py       # 查寝执行（重构自原脚本）
│   ├── templates/
│   │   ├── base.html        # 基础布局
│   │   ├── login.html       # 登录页
│   │   ├── users/
│   │   │   ├── list.html    # 用户列表
│   │   │   └── form.html    # 用户新增/编辑表单
│   │   └── logs/
│   │       └── list.html    # 日志列表
│   └── static/
│       └── style.css        # 自定义样式
├── config.py                # 配置类
├── run.py                   # 入口
├── requirements.txt         # 依赖
├── Dockerfile               # Docker 构建
├── docker-compose.yml       # Docker 编排
└── .env.example             # 环境变量模板
```

---

### Task 1: 项目脚手架 — 目录结构与配置

**Files:**
- Create: `gotobed-system/requirements.txt`
- Create: `gotobed-system/config.py`
- Create: `gotobed-system/.env.example`

- [ ] **Step 1: 创建目录结构**

```bash
cd D:/Code/Python/Tools/auto-do-bed-sign
mkdir -p gotobed-system/app/routes
mkdir -p gotobed-system/app/tasks
mkdir -p gotobed-system/app/templates/users
mkdir -p gotobed-system/app/templates/logs
mkdir -p gotobed-system/app/static
```

- [ ] **Step 2: 创建 requirements.txt**

写入 `gotobed-system/requirements.txt`：

```
flask>=3.0
flask-login>=0.6
flask-sqlalchemy>=3.1
apscheduler>=3.10
requests>=2.31
PyExecJS>=1.5
ddddocr>=1.4
dnspython>=2.4
pytz>=2024
cryptography>=42.0
gunicorn>=22.0
```

- [ ] **Step 3: 创建 config.py**

写入 `gotobed-system/config.py`：

```python
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
```

- [ ] **Step 4: 创建 .env.example**

写入 `gotobed-system/.env.example`：

```env
# 管理员密码（必填）
ADMIN_PASSWORD=your-admin-password

# Flask session 密钥（必填，随机生成）
SECRET_KEY=your-flask-secret-key

# Fernet 密码加密密钥（必填，用 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 生成）
FERNET_KEY=your-fernet-key

# SMTP 邮件配置（选填，不配置则不发邮件）
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-email@qq.com
SMTP_PASS=your-email-auth-code
```

- [ ] **Step 5: 创建空的 __init__.py 占位文件**

```bash
touch gotobed-system/app/__init__.py
touch gotobed-system/app/routes/__init__.py
touch gotobed-system/app/tasks/__init__.py
```

- [ ] **Step 6: 提交**

```bash
cd D:/Code/Python/Tools/auto-do-bed-sign
git add gotobed-system/
git commit -m "feat: 初始化项目脚手架 — 目录结构、配置、依赖"
```

---

### Task 2: 数据模型

**Files:**
- Create: `gotobed-system/app/models.py`

- [ ] **Step 1: 创建 models.py**

写入 `gotobed-system/app/models.py`：

```python
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    principal = db.Column(db.Text, nullable=True)
    credential = db.Column(db.Text, nullable=True)
    email = db.Column(db.Text, nullable=True)
    cron_expr = db.Column(db.Text, nullable=False, default='10 12 * * *')
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    logs = db.relationship('Log', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'


class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Text, nullable=False)  # 'success' / 'failure'
    message = db.Column(db.Text, nullable=False)
    executed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Log {self.id} {self.status}>'
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/models.py
git commit -m "feat: 添加 User 和 Log 数据模型"
```

---

### Task 3: 密码加密工具

**Files:**
- Create: `gotobed-system/app/crypto.py`

- [ ] **Step 1: 创建 crypto.py**

写入 `gotobed-system/app/crypto.py`：

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/crypto.py
git commit -m "feat: 添加 Fernet 密码加密/解密工具"
```

---

### Task 4: Flask App 工厂

**Files:**
- Modify: `gotobed-system/app/__init__.py`

- [ ] **Step 1: 实现 app 工厂**

写入 `gotobed-system/app/__init__.py`：

```python
import os
from flask import Flask
from flask_login import LoginManager

from .models import db

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # 加载配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///data/gotobed.db'
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
        os.makedirs(os.path.join(os.path.dirname(app.root_path), 'data'), exist_ok=True)
        db.create_all()

    return app
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/__init__.py
git commit -m "feat: 实现 Flask app 工厂"
```

---

### Task 5: 管理员认证

**Files:**
- Create: `gotobed-system/app/routes/auth.py`

- [ ] **Step 1: 实现管理员用户类和登录路由**

写入 `gotobed-system/app/routes/auth.py`：

```python
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask import current_app

auth_bp = Blueprint('auth', __name__)


class AdminUser(UserMixin):
    """管理员虚拟用户，仅用密码认证"""
    id = 1

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    if user_id == '1':
        return AdminUser()
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == current_app.config['ADMIN_PASSWORD']:
            login_user(AdminUser())
            next_page = request.args.get('next')
            return redirect(next_page or url_for('users.user_list'))
        flash('密码错误', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/routes/auth.py
git commit -m "feat: 实现管理员认证 — 登录/登出"
```

---

### Task 6: 路由注册

**Files:**
- Modify: `gotobed-system/app/routes/__init__.py`

- [ ] **Step 1: 实现蓝图注册**

写入 `gotobed-system/app/routes/__init__.py`：

```python
from .auth import auth_bp
from .users import users_bp
from .logs import logs_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(logs_bp)
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/routes/__init__.py
git commit -m "feat: 实现路由蓝图注册"
```

---

### Task 7: 用户 CRUD 路由

**Files:**
- Create: `gotobed-system/app/routes/users.py`

- [ ] **Step 1: 实现用户 CRUD**

写入 `gotobed-system/app/routes/users.py`：

```python
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required

from ..models import db, User
from ..crypto import encrypt_password
from ..scheduler import add_user_job, remove_user_job, update_user_job

users_bp = Blueprint('users', __name__)

CRON_PRESETS = {
    '10 12 * * *': '每天 20:10（北京时间）',
    '0 14 * * *': '每天 22:00（北京时间）',
    '30 13 * * *': '每天 21:30（北京时间）',
    '0 13 * * *': '每天 21:00（北京时间）',
}


@users_bp.route('/')
@login_required
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users/list.html', users=users)


@users_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def user_new():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('账号和密码为必填项', 'danger')
            return render_template('users/form.html', presets=CRON_PRESETS, user=None)

        user = User(
            username=username,
            password_encrypted=encrypt_password(password),
            principal=request.form.get('principal', '').strip() or None,
            credential=request.form.get('credential', '').strip() or None,
            email=request.form.get('email', '').strip() or None,
            cron_expr=request.form.get('cron_expr', '10 12 * * *').strip(),
            enabled='enabled' in request.form,
        )
        db.session.add(user)
        db.session.commit()

        if user.enabled:
            add_user_job(user)

        flash(f'用户 {username} 添加成功', 'success')
        return redirect(url_for('users.user_list'))

    return render_template('users/form.html', presets=CRON_PRESETS, user=None)


@users_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username:
            flash('账号为必填项', 'danger')
            return render_template('users/form.html', presets=CRON_PRESETS, user=user)

        user.username = username
        if password:
            user.password_encrypted = encrypt_password(password)
        user.principal = request.form.get('principal', '').strip() or None
        user.credential = request.form.get('credential', '').strip() or None
        user.email = request.form.get('email', '').strip() or None
        user.cron_expr = request.form.get('cron_expr', '10 12 * * *').strip()
        user.enabled = 'enabled' in request.form
        db.session.commit()

        update_user_job(user)

        flash(f'用户 {username} 更新成功', 'success')
        return redirect(url_for('users.user_list'))

    return render_template('users/form.html', presets=CRON_PRESETS, user=user)


@users_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    username = user.username
    remove_user_job(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'用户 {username} 已删除', 'success')
    return redirect(url_for('users.user_list'))


@users_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def user_toggle(user_id):
    user = User.query.get_or_404(user_id)
    user.enabled = not user.enabled
    db.session.commit()

    update_user_job(user)

    status = '启用' if user.enabled else '禁用'
    flash(f'用户 {user.username} 已{status}', 'success')
    return redirect(url_for('users.user_list'))
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/routes/users.py
git commit -m "feat: 实现用户 CRUD 路由"
```

---

### Task 8: 日志查看路由

**Files:**
- Create: `gotobed-system/app/routes/logs.py`

- [ ] **Step 1: 实现日志路由**

写入 `gotobed-system/app/routes/logs.py`：

```python
from flask import Blueprint, render_template, request
from flask_login import login_required

from ..models import db, Log, User

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/logs')
@login_required
def log_list():
    page = request.args.get('page', 1, type=int)
    user_id = request.args.get('user_id', type=int)
    per_page = 20

    query = Log.query.order_by(Log.executed_at.desc())
    if user_id:
        query = query.filter_by(user_id=user_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = User.query.order_by(User.username).all()

    return render_template('logs/list.html',
                           logs=pagination.items,
                           pagination=pagination,
                           users=users,
                           selected_user_id=user_id)
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/routes/logs.py
git commit -m "feat: 实现日志查看路由"
```

---

### Task 9: 邮件发送模块

**Files:**
- Create: `gotobed-system/app/email_sender.py`

- [ ] **Step 1: 重构邮件发送**

从原 `emailSender.py` 重构，去除硬编码，改为从 Flask 配置读取。

写入 `gotobed-system/app/email_sender.py`：

```python
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import pytz
from flask import current_app


def get_beijing_time():
    beijing_zone = pytz.timezone('Asia/Shanghai')
    beijing_time = datetime.now(beijing_zone)
    return beijing_time.strftime('%Y-%m-%d %A %H:%M')


def send_email(subject: str, content: str, to_address: str):
    """发送邮件通知，配置从 Flask app config 读取"""
    if not to_address:
        print(f'未配置邮箱，跳过邮件发送。结果：{content}')
        return

    smtp_host = current_app.config.get('SMTP_HOST', '')
    smtp_port = current_app.config.get('SMTP_PORT', 465)
    smtp_user = current_app.config.get('SMTP_USER', '')
    smtp_pass = current_app.config.get('SMTP_PASS', '')

    if not smtp_user or not smtp_pass:
        print(f'SMTP 未配置，跳过邮件发送。结果：{content}')
        return

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = smtp_user
    msg['To'] = to_address
    msg['Subject'] = subject

    try:
        smtp = smtplib.SMTP_SSL(smtp_host, smtp_port)
        smtp.login(smtp_user, smtp_pass)
        smtp.sendmail(smtp_user, to_address, msg.as_string())
        smtp.quit()
        print(f'邮件发送成功 -> {to_address}')
    except Exception as e:
        print(f'邮件发送失败: {e}')


def send_gotobed_result(content: str, to_address: str):
    """发送查寝结果通知"""
    formatted_date = get_beijing_time()
    result_status = '✅成功' if '成功' in content else '❌失败'
    subject = f'查寝 {result_status} {formatted_date}'
    body = f'签到结果：{content}'
    send_email(subject, body, to_address)
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/email_sender.py
git commit -m "feat: 重构邮件发送模块 — 从环境变量读取 SMTP 配置"
```

---

### Task 10: 查寝执行器

**Files:**
- Create: `gotobed-system/app/tasks/gotobed.py`

- [ ] **Step 1: 重构查寝逻辑为函数调用**

从原 `goToBed.py` 重构，去除 `os.getenv()`，改为参数传入。保留核心逻辑：DNS 修正、验证码 OCR、登录、二次验证、查寝签到、重试。

写入 `gotobed-system/app/tasks/gotobed.py`：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import re
import json
import socket
import time
import random

import execjs
import requests
import ddddocr
import dns.resolver

# ---- 国内 DNS 解析配置 ----
TARGET_DOMAINS = {'ids.gzist.edu.cn', 'xsfw.gzist.edu.cn'}
CHINA_DNS_SERVERS = ['223.5.5.5', '119.29.29.29']
_dns_cache = {}
_original_getaddrinfo = socket.getaddrinfo


def _resolve_with_china_dns(hostname):
    """使用国内 DNS 服务器解析域名，带缓存"""
    if hostname in _dns_cache:
        return _dns_cache[hostname]
    for dns_server in CHINA_DNS_SERVERS:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            resolver.lifetime = 5
            answers = resolver.resolve(hostname, 'A')
            ip = str(answers[0])
            _dns_cache[hostname] = ip
            print(f'DNS 解析: {hostname} -> {ip} (via {dns_server})')
            return ip
        except Exception as e:
            print(f'DNS 解析 {hostname} 失败 (via {dns_server}): {e}')
            continue
    raise RuntimeError(f'所有国内 DNS 服务器均无法解析 {hostname}')


def _custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """自定义 getaddrinfo，对目标域名使用国内 DNS 解析"""
    if host in TARGET_DOMAINS:
        ip = _resolve_with_china_dns(host)
        return _original_getaddrinfo(ip, port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)


# 替换系统的 DNS 解析函数
socket.getaddrinfo = _custom_getaddrinfo

# 加载 JS 加密脚本
import os

_js_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'gzlg助手', 'g5116.js')
_js_path = os.path.normpath(_js_path)
with open(_js_path, 'r', encoding='utf-8') as f:
    _js_code = f.read()
_ctx = execjs.compile(_js_code)


def _init_session():
    session = requests.Session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/91.0.4472.124 Safari/537.36"
    }
    return session


def _get_code(image_base64):
    """验证码 OCR 识别"""
    ocr = ddddocr.DdddOcr(show_ad=False)
    image_bytes = base64.b64decode(image_base64)
    result = ocr.classification(image_bytes)
    result = result.replace('o', '0').replace('l', '1').replace('O', '0').replace('十', '+').replace('三', '')
    print('验证码识别结果：' + result[:-1])
    ans = eval(result[:-1])
    print('计算结果：', ans)
    return ans


def _login(session, username, password, principal=None, credential=None):
    """登录学工平台，返回 ticket"""
    params = {'uid': ''}
    yzm_url = 'https://ids.gzist.edu.cn/lyuapServer/kaptcha'
    response = session.get(yzm_url, params=params)
    uid = response.json()['uid']

    yzm = None
    if 'content' in response.json() and response.json()['content']:
        yzm_match = re.search('base64,(.*)', response.json()['content'])
        if yzm_match:
            yzm_base64 = yzm_match.group(1)
            yzm = _get_code(yzm_base64)
            print('验证码：', yzm)

    psw = _ctx.call('G5116', username, password, '')
    data = {
        'username': username,
        'password': str(psw),
        'service': 'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        'loginType': '',
        'id': uid,
    }

    if yzm is not None:
        data['code'] = str(yzm)

    response = session.post('https://ids.gzist.edu.cn/lyuapServer/v1/tickets', data=data)
    login_response = response.json()

    if 'NOUSER' in login_response:
        raise RuntimeError('账号不存在')
    elif 'PASSERROR' in login_response:
        raise RuntimeError('密码错误')
    elif 'CODEFALSE' in login_response:
        raise RuntimeError('验证码错误')

    print("登录响应：", login_response)

    # 二次验证
    if 'data' in response.json() and response.json()['data']['code'] == 'TWOVERIFY':
        if not principal or not credential:
            raise RuntimeError('需要二次验证，但未配置密保问题/答案')

        vcodes = response.json()['data']['uid']
        session.headers['vcodes'] = vcodes
        json_data = {
            'userName': username,
            'principal': principal,
            'credential': credential,
            'type': '2',
            'service': 'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
            'loginType': '',
            'isCommonIP': '',
        }
        session.post('https://ids.gzist.edu.cn/lyuapServer/login/twoVertify',
                     headers=session.headers, json=json_data)
        response = session.post('https://ids.gzist.edu.cn/lyuapServer/v1/tickets', data=data)
        return response.json()['ticket']

    return response.json()['ticket']


def _update_cookie(session, ticket):
    """使用 ticket 获取 cookie"""
    params = {'ticket': ticket}
    response = session.get(
        'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        params=params)
    session.cookies = response.cookies


def _do_gotobed(session, username):
    """执行查寝签到"""
    data = {
        'data': '{"APPID":"5405362541914944","APPNAME":"swmzncqapp"}'
    }
    response = session.post(
        'https://xsfw.gzist.edu.cn/xsfw/sys/swpubapp/MobileCommon/getSelRoleConfig.do',
        cookies=session.cookies,
        data=data,
    )
    _WEU = response.cookies.get('_WEU')
    cookies = {'_WEU': _WEU}

    data_by = {
        'data': '{"SFFWN":"1","DDDM":"134D3343A40D51AFE0630717000A7549",'
                '"DDMC":"广州理工学院白云区","QDJD":113.46617498988796,'
                '"QDWD":23.263957044502487,"RWBH":"16FC8C91BCDDEC67E0630717000A97E1",'
                '"QDPL":"2"}',
    }
    data_hz = {
        'data': '{"SFFWN":"1","DDDM":"b2c1441606da4efbb9fe5b2b89226396",'
                '"DDMC":"广州理工学院(博罗校区)","QDJD":114.08675193786623,'
                '"QDWD":23.186742693715477,"RWBH":"16FC8C91BCDDEC67E0630717000A97E1",'
                '"QDPL":"2"}',
    }

    from datetime import datetime
    if int(username[:4]) >= datetime.now().year:
        print('定位hz')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/modules/studentCheckController/uniFormSignUp.do',
            cookies=cookies, data=data_hz)
    else:
        print('定位by')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/modules/studentCheckController/uniFormSignUp.do',
            cookies=cookies, data=data_by)

    try:
        result = response.json()['msg']
        print('签到结果: ' + result)
        return result
    except json.JSONDecodeError:
        print(f'签到异常: JSON解析错误，响应: {response.text}')
        return '查寝失败'
    except Exception as e:
        print(f'签到异常: {e}')
        return '查寝失败'


def run_gotobed(username: str, password: str,
                principal: str = None, credential: str = None,
                email: str = None) -> dict:
    """
    执行查寝任务，带重试。

    返回: {'status': 'success'|'failure', 'message': str}
    """
    from ..email_sender import send_gotobed_result

    max_attempts = 5
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            session = _init_session()
            ticket = _login(session, username, password, principal, credential)
            _update_cookie(session, ticket)
            result = _do_gotobed(session, username)

            if email:
                send_gotobed_result(result, email)

            return {'status': 'success', 'message': result}

        except Exception as e:
            last_error = str(e)
            print(f"尝试 {attempt} 次失败，错误信息：{e}")
            if attempt < max_attempts:
                wait = min(5 * (2 ** (attempt - 1)), 60) + random.uniform(0, 3)
                print(f"等待 {wait:.1f} 秒后重试...")
                time.sleep(wait)

    error_msg = f'连续{max_attempts}次执行失败: {last_error}'
    if email:
        send_gotobed_result(error_msg, email)
    return {'status': 'failure', 'message': error_msg}
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/tasks/gotobed.py
git commit -m "feat: 重构查寝执行器 — 函数化，参数传入凭据"
```

---

### Task 11: APScheduler 调度集成

**Files:**
- Create: `gotobed-system/app/scheduler.py`

- [ ] **Step 1: 实现调度器**

写入 `gotobed-system/app/scheduler.py`：

```python
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
_jobs = {}  # user_id -> job_id


def _execute_gotobed(user_id: int):
    """调度任务回调：执行指定用户的查寝"""
    from .models import db, User, Log
    from .tasks.gotobed import run_gotobed
    from . import create_app

    app = create_app()
    with app.app_context():
        user = db.session.get(User, user_id)
        if not user or not user.enabled:
            logger.warning(f'用户 {user_id} 不存在或已禁用，跳过')
            return

        from .crypto import decrypt_password
        password = decrypt_password(user.password_encrypted)

        result = run_gotobed(
            username=user.username,
            password=password,
            principal=user.principal,
            credential=user.credential,
            email=user.email,
        )

        log = Log(
            user_id=user.id,
            status=result['status'],
            message=result['message'],
        )
        db.session.add(log)
        db.session.commit()
        logger.info(f'用户 {user.username} 查寝完成: {result["status"]}')


def add_user_job(user):
    """为用户添加调度任务"""
    job_id = f'gotobed_{user.id}'
    try:
        trigger = CronTrigger.from_crontab(user.cron_expr, timezone='Asia/Shanghai')
        scheduler.add_job(
            _execute_gotobed,
            trigger=trigger,
            args=[user.id],
            id=job_id,
            replace_existing=True,
            max_instances=1,
        )
        _jobs[user.id] = job_id
        logger.info(f'已添加调度: 用户 {user.username}, cron={user.cron_expr}')
    except Exception as e:
        logger.error(f'添加调度失败: 用户 {user.username}, 错误: {e}')


def remove_user_job(user_id: int):
    """移除用户的调度任务"""
    job_id = _jobs.pop(user_id, None)
    if job_id:
        try:
            scheduler.remove_job(job_id)
            logger.info(f'已移除调度: 用户ID {user_id}')
        except Exception:
            pass


def update_user_job(user):
    """更新用户的调度任务（删除旧的，添加新的）"""
    remove_user_job(user.id)
    if user.enabled:
        add_user_job(user)


def init_scheduler(app):
    """初始化调度器，加载所有启用的用户"""
    with app.app_context():
        from .models import User
        users = User.query.filter_by(enabled=True).all()
        for user in users:
            add_user_job(user)

    scheduler.start()
    logger.info(f'调度器已启动，共加载 {len(users)} 个用户任务')
```

- [ ] **Step 2: 修复 _execute_gotobed 中的 app 创建问题**

上面的 `_execute_gotobed` 每次都创建新 app 实例效率低且可能死循环。改为接收 app 对象：

写入修改后的 `gotobed-system/app/scheduler.py`：

```python
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
_jobs = {}  # user_id -> job_id
_app = None  # 保存 app 引用


def _execute_gotobed(user_id: int):
    """调度任务回调：执行指定用户的查寝"""
    from .models import db, User, Log
    from .tasks.gotobed import run_gotobed
    from .crypto import decrypt_password

    if _app is None:
        logger.error('Flask app 未初始化')
        return

    with _app.app_context():
        user = db.session.get(User, user_id)
        if not user or not user.enabled:
            logger.warning(f'用户 {user_id} 不存在或已禁用，跳过')
            return

        password = decrypt_password(user.password_encrypted)

        result = run_gotobed(
            username=user.username,
            password=password,
            principal=user.principal,
            credential=user.credential,
            email=user.email,
        )

        log = Log(
            user_id=user.id,
            status=result['status'],
            message=result['message'],
        )
        db.session.add(log)
        db.session.commit()
        logger.info(f'用户 {user.username} 查寝完成: {result["status"]}')


def add_user_job(user):
    """为用户添加调度任务"""
    job_id = f'gotobed_{user.id}'
    try:
        trigger = CronTrigger.from_crontab(user.cron_expr, timezone='Asia/Shanghai')
        scheduler.add_job(
            _execute_gotobed,
            trigger=trigger,
            args=[user.id],
            id=job_id,
            replace_existing=True,
            max_instances=1,
        )
        _jobs[user.id] = job_id
        logger.info(f'已添加调度: 用户 {user.username}, cron={user.cron_expr}')
    except Exception as e:
        logger.error(f'添加调度失败: 用户 {user.username}, 错误: {e}')


def remove_user_job(user_id: int):
    """移除用户的调度任务"""
    job_id = _jobs.pop(user_id, None)
    if job_id:
        try:
            scheduler.remove_job(job_id)
            logger.info(f'已移除调度: 用户ID {user_id}')
        except Exception:
            pass


def update_user_job(user):
    """更新用户的调度任务（删除旧的，添加新的）"""
    remove_user_job(user.id)
    if user.enabled:
        add_user_job(user)


def init_scheduler(app):
    """初始化调度器，加载所有启用的用户"""
    global _app
    _app = app

    with app.app_context():
        from .models import User
        users = User.query.filter_by(enabled=True).all()
        for user in users:
            add_user_job(user)

    scheduler.start()
    logger.info(f'调度器已启动，共加载 {len(users)} 个用户任务')
```

- [ ] **Step 3: 提交**

```bash
git add gotobed-system/app/scheduler.py
git commit -m "feat: 实现 APScheduler 调度集成"
```

---

### Task 12: 模板 — 基础布局

**Files:**
- Create: `gotobed-system/app/templates/base.html`

- [ ] **Step 1: 写入基础布局模板**

写入 `gotobed-system/app/templates/base.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}查寝管理系统{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet"
          integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB"
          crossorigin="anonymous">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">查寝管理系统</a>
            {% if current_user.is_authenticated %}
            <div class="navbar-nav">
                <a class="nav-link" href="{{ url_for('users.user_list') }}">用户管理</a>
                <a class="nav-link" href="{{ url_for('logs.log_list') }}">执行日志</a>
                <a class="nav-link" href="{{ url_for('auth.logout') }}">退出</a>
            </div>
            {% endif %}
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        {% for category, message in messages %}
        <div class="alert alert-{{ category }} alert-dismissible fade show">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        {% endfor %}
        {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
            integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI"
            crossorigin="anonymous"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/templates/base.html
git commit -m "feat: 添加基础布局模板 (Bootstrap 5)"
```

---

### Task 13: 模板 — 登录页

**Files:**
- Create: `gotobed-system/app/templates/login.html`

- [ ] **Step 1: 写入登录页模板**

写入 `gotobed-system/app/templates/login.html`：

```html
{% extends "base.html" %}
{% block title %}登录 - 查寝管理系统{% endblock %}

{% block content %}
<div class="row justify-content-center mt-5">
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h4 class="card-title text-center mb-4">查寝管理系统</h4>
                <form method="POST">
                    <div class="mb-3">
                        <label for="password" class="form-label">管理员密码</label>
                        <input type="password" class="form-control" id="password" name="password"
                               required autofocus>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">登录</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/templates/login.html
git commit -m "feat: 添加登录页模板"
```

---

### Task 14: 模板 — 用户列表

**Files:**
- Create: `gotobed-system/app/templates/users/list.html`

- [ ] **Step 1: 写入用户列表模板**

写入 `gotobed-system/app/templates/users/list.html`：

```html
{% extends "base.html" %}
{% block title %}用户管理 - 查寝管理系统{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h4>用户管理</h4>
    <a href="{{ url_for('users.user_new') }}" class="btn btn-primary">+ 新增用户</a>
</div>

{% if users %}
<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>账号</th>
                <th>邮箱</th>
                <th>Cron 表达式</th>
                <th>状态</th>
                <th>最近日志</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for user in users %}
            <tr>
                <td>{{ user.username }}</td>
                <td>{{ user.email or '-' }}</td>
                <td><code>{{ user.cron_expr }}</code></td>
                <td>
                    {% if user.enabled %}
                    <span class="badge bg-success">启用</span>
                    {% else %}
                    <span class="badge bg-secondary">禁用</span>
                    {% endif %}
                </td>
                <td>
                    {% set last_log = user.logs.order_by('-executed_at').first() %}
                    {% if last_log %}
                        {% if last_log.status == 'success' %}
                        <span class="text-success">✅ {{ last_log.message[:20] }}</span>
                        {% else %}
                        <span class="text-danger">❌ {{ last_log.message[:20] }}</span>
                        {% endif %}
                    {% else %}
                    <span class="text-muted">-</span>
                    {% endif %}
                </td>
                <td>
                    <a href="{{ url_for('users.user_edit', user_id=user.id) }}"
                       class="btn btn-sm btn-outline-primary">编辑</a>
                    <form method="POST" action="{{ url_for('users.user_toggle', user_id=user.id) }}"
                          style="display:inline">
                        {% if user.enabled %}
                        <button class="btn btn-sm btn-outline-warning">禁用</button>
                        {% else %}
                        <button class="btn btn-sm btn-outline-success">启用</button>
                        {% endif %}
                    </form>
                    <form method="POST" action="{{ url_for('users.user_delete', user_id=user.id) }}"
                          style="display:inline"
                          onsubmit="return confirm('确定删除用户 {{ user.username }}？')">
                        <button class="btn btn-sm btn-outline-danger">删除</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% else %}
<div class="text-center text-muted py-5">
    <p>暂无用户，点击上方按钮新增</p>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/templates/users/list.html
git commit -m "feat: 添加用户列表模板"
```

---

### Task 15: 模板 — 用户表单

**Files:**
- Create: `gotobed-system/app/templates/users/form.html`

- [ ] **Step 1: 写入用户表单模板**

写入 `gotobed-system/app/templates/users/form.html`：

```html
{% extends "base.html" %}
{% block title %}{{ '编辑' if user else '新增' }}用户 - 查寝管理系统{% endblock %}

{% block content %}
<h4>{{ '编辑' if user else '新增' }}用户</h4>

<div class="card mt-3">
    <div class="card-body">
        <form method="POST">
            <div class="mb-3">
                <label for="username" class="form-label">账号 <span class="text-danger">*</span></label>
                <input type="text" class="form-control" id="username" name="username"
                       value="{{ user.username if user else '' }}" required>
                <div class="form-text">学工平台用户名</div>
            </div>

            <div class="mb-3">
                <label for="password" class="form-label">
                    密码 {% if not user %}<span class="text-danger">*</span>{% endif %}
                </label>
                <input type="password" class="form-control" id="password" name="password"
                       {{ 'required' if not user else '' }}>
                {% if user %}
                <div class="form-text">留空表示不修改</div>
                {% endif %}
            </div>

            <div class="mb-3">
                <label for="principal" class="form-label">密保问题 <span class="text-muted">(选填)</span></label>
                <input type="text" class="form-control" id="principal" name="principal"
                       value="{{ user.principal if user and user.principal else '' }}">
                <div class="form-text">二次验证用，不触发二次验证时无需填写</div>
            </div>

            <div class="mb-3">
                <label for="credential" class="form-label">密保答案 <span class="text-muted">(选填)</span></label>
                <input type="text" class="form-control" id="credential" name="credential"
                       value="{{ user.credential if user and user.credential else '' }}">
            </div>

            <div class="mb-3">
                <label for="email" class="form-label">通知邮箱 <span class="text-muted">(选填)</span></label>
                <input type="email" class="form-control" id="email" name="email"
                       value="{{ user.email if user and user.email else '' }}">
                <div class="form-text">查寝结果会发送到此邮箱</div>
            </div>

            <div class="mb-3">
                <label for="cron_expr" class="form-label">Cron 表达式 <span class="text-danger">*</span></label>
                <select class="form-select mb-2" id="cron_preset" onchange="applyPreset()">
                    <option value="">-- 选择预设 --</option>
                    {% for expr, desc in presets.items() %}
                    <option value="{{ expr }}"
                        {% if user and user.cron_expr == expr %}selected{% endif %}>
                        {{ desc }} ({{ expr }})
                    </option>
                    {% endfor %}
                    <option value="custom">自定义</option>
                </select>
                <input type="text" class="form-control" id="cron_expr" name="cron_expr"
                       value="{{ user.cron_expr if user else '10 12 * * *' }}" required
                       placeholder="分 时 日 月 周">
                <div class="form-text">格式：分 时 日 月 周（北京时间，如 10 12 * * * = 每天20:10）</div>
            </div>

            <div class="mb-3 form-check">
                <input type="checkbox" class="form-check-input" id="enabled" name="enabled"
                       {{ 'checked' if not user or user.enabled else '' }}>
                <label class="form-check-label" for="enabled">启用</label>
            </div>

            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-primary">保存</button>
                <a href="{{ url_for('users.user_list') }}" class="btn btn-secondary">取消</a>
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function applyPreset() {
    const select = document.getElementById('cron_preset');
    const input = document.getElementById('cron_expr');
    if (select.value && select.value !== 'custom') {
        input.value = select.value;
    }
}
</script>
{% endblock %}
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/templates/users/form.html
git commit -m "feat: 添加用户表单模板（含 cron 预设选择）"
```

---

### Task 16: 模板 — 日志列表

**Files:**
- Create: `gotobed-system/app/templates/logs/list.html`

- [ ] **Step 1: 写入日志列表模板**

写入 `gotobed-system/app/templates/logs/list.html`：

```html
{% extends "base.html" %}
{% block title %}执行日志 - 查寝管理系统{% endblock %}

{% block content %}
<h4>执行日志</h4>

<form method="GET" class="mb-3">
    <div class="row g-2 align-items-end">
        <div class="col-auto">
            <label for="user_id" class="form-label">筛选用户</label>
            <select class="form-select" id="user_id" name="user_id" onchange="this.form.submit()">
                <option value="">全部用户</option>
                {% for u in users %}
                <option value="{{ u.id }}"
                    {% if selected_user_id == u.id %}selected{% endif %}>
                    {{ u.username }}
                </option>
                {% endfor %}
            </select>
        </div>
    </div>
</form>

{% if logs %}
<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>用户</th>
                <th>状态</th>
                <th>结果</th>
                <th>执行时间</th>
            </tr>
        </thead>
        <tbody>
            {% for log in logs %}
            <tr>
                <td>{{ log.user.username }}</td>
                <td>
                    {% if log.status == 'success' %}
                    <span class="badge bg-success">成功</span>
                    {% else %}
                    <span class="badge bg-danger">失败</span>
                    {% endif %}
                </td>
                <td>{{ log.message }}</td>
                <td>{{ log.executed_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- 分页 -->
{% if pagination.pages > 1 %}
<nav>
    <ul class="pagination">
        {% if pagination.has_prev %}
        <li class="page-item">
            <a class="page-link" href="?page={{ pagination.prev_num }}{% if selected_user_id %}&user_id={{ selected_user_id }}{% endif %}">上一页</a>
        </li>
        {% endif %}
        {% for p in pagination.iter_pages() %}
        {% if p %}
        <li class="page-item {{ 'active' if p == pagination.page else '' }}">
            <a class="page-link" href="?page={{ p }}{% if selected_user_id %}&user_id={{ selected_user_id }}{% endif %}">{{ p }}</a>
        </li>
        {% else %}
        <li class="page-item disabled"><span class="page-link">…</span></li>
        {% endif %}
        {% endfor %}
        {% if pagination.has_next %}
        <li class="page-item">
            <a class="page-link" href="?page={{ pagination.next_num }}{% if selected_user_id %}&user_id={{ selected_user_id }}{% endif %}">下一页</a>
        </li>
        {% endif %}
    </ul>
</nav>
{% endif %}

{% else %}
<div class="text-center text-muted py-5">
    <p>暂无执行日志</p>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/templates/logs/list.html
git commit -m "feat: 添加日志列表模板（含筛选和分页）"
```

---

### Task 17: 自定义样式

**Files:**
- Create: `gotobed-system/app/static/style.css`

- [ ] **Step 1: 写入自定义样式**

写入 `gotobed-system/app/static/style.css`：

```css
body {
    background-color: #f8f9fa;
}

.navbar-brand {
    font-weight: 600;
}

.table th {
    white-space: nowrap;
}

.badge {
    font-size: 0.85em;
}
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/app/static/style.css
git commit -m "feat: 添加自定义 CSS 样式"
```

---

### Task 18: 应用入口

**Files:**
- Create: `gotobed-system/run.py`

- [ ] **Step 1: 创建入口文件**

写入 `gotobed-system/run.py`：

```python
import logging
from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

- [ ] **Step 2: 提交**

```bash
git add gotobed-system/run.py
git commit -m "feat: 添加应用入口 run.py"
```

---

### Task 19: Docker 部署文件

**Files:**
- Create: `gotobed-system/Dockerfile`
- Create: `gotobed-system/docker-compose.yml`

- [ ] **Step 1: 创建 Dockerfile**

写入 `gotobed-system/Dockerfile`：

```dockerfile
FROM python:3.11-slim

# 安装 Node.js（PyExecJS 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件并安装
COPY gotobed-system/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制管理系统代码
COPY gotobed-system/ .

# 复制原脚本的 JS 文件（密码加密依赖）
COPY "gzlg助手/g5116.js" ./gzlg助手/g5116.js

# 创建数据目录
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "run:app"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

写入 `gotobed-system/docker-compose.yml`：

```yaml
version: '3.8'
services:
  gotobed:
    build:
      context: ..
      dockerfile: gotobed-system/Dockerfile
    container_name: gotobed-system
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    environment:
      - TZ=Asia/Shanghai
```

- [ ] **Step 3: 提交**

```bash
git add gotobed-system/Dockerfile gotobed-system/docker-compose.yml
git commit -m "feat: 添加 Docker 部署文件"
```

---

### Task 20: 本地测试验证

- [ ] **Step 1: 安装依赖**

```bash
cd D:/Code/Python/Tools/auto-do-bed-sign/gotobed-system
pip install -r requirements.txt
```

- [ ] **Step 2: 设置环境变量并启动**

```bash
# Windows PowerShell
$env:ADMIN_PASSWORD = "test123"
$env:SECRET_KEY = "dev-secret-key"
$env:FERNET_KEY = "gAAAAABh..."  # 用 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 生成
python run.py
```

- [ ] **Step 3: 浏览器访问 http://localhost:5000**

验证：
- 能否用 `test123` 登录
- 能否新增用户
- 能否编辑/删除用户
- 日志页面是否正常

- [ ] **Step 4: 提交最终状态**

```bash
cd D:/Code/Python/Tools/auto-do-bed-sign
git add gotobed-system/
git commit -m "feat: 查寝管理系统 v1.0 完成"
```
