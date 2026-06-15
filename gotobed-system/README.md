# 查寝管理系统 — 部署文档

自托管的查寝管理 Web 系统，替代 GitHub Actions 方案，支持多用户管理和定时任务调度。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [环境要求](#环境要求)
- [部署方式](#部署方式)
  - [Docker 部署（推荐）](#docker-部署推荐)
  - [本地开发运行](#本地开发运行)
- [配置说明](#配置说明)
- [使用说明](#使用说明)
- [目录结构](#目录结构)
- [常见问题](#常见问题)

---

## 功能特性

- **多用户管理**：Web 后台增删改查查寝用户
- **多时间选择**：每个用户可选择多个打卡时间（9:10 / 9:30 / 10:10 / 10:30）
- **二次验证支持**：密保问题/答案为选填，有需要时自动触发
- **失败重试**：最多 5 次重试，指数退避
- **邮件通知**：查寝结果自动发送到用户邮箱
- **执行日志**：查看每次查寝的执行状态和结果
- **密码加密**：用户密码使用 Fernet 对称加密存储
- **Docker 部署**：单容器一键启动

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Flask 3.x |
| 定时调度 | APScheduler 3.10 |
| 数据库 | SQLite |
| ORM | Flask-SQLAlchemy |
| 认证 | Flask-Login |
| 密码加密 | cryptography (Fernet) |
| 前端 | Bootstrap 5 |
| 容器化 | Docker + docker-compose |
| WSGI | Gunicorn |

---

## 环境要求

### Docker 部署
- Docker 20.10+
- Docker Compose 2.0+

### 本地运行
- Python 3.11+
- Node.js（PyExecJS 依赖，用于密码加密）

---

## 部署方式

### Docker 部署（推荐）

**1. 克隆项目**

```bash
git clone <repo-url>
cd auto-do-bed-sign
```

**2. 生成 Fernet 加密密钥**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

记录输出的密钥，下一步需要用到。

**3. 创建环境变量文件**

在项目根目录创建 `.env` 文件：

```env
# 管理员密码（登录 Web 后台用）
ADMIN_PASSWORD=your-strong-password

# Flask session 密钥（随机字符串即可）
SECRET_KEY=your-random-secret-key

# Fernet 加密密钥（上一步生成的）
FERNET_KEY=your-fernet-key

# SMTP 邮件配置（选填，不配置则不发邮件通知）
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-email@qq.com
SMTP_PASS=your-email-auth-code
```

**4. 启动容器**

```bash
cd gotobed-system
docker-compose up -d --build
```

**5. 访问系统**

浏览器打开 `http://your-server:5000`，使用管理员密码登录。

**6. 查看日志**

```bash
docker logs -f gotobed-system
```

**7. 停止/重启**

```bash
# 停止
docker-compose down

# 重启
docker-compose restart

# 更新代码后重新构建
docker-compose up -d --build
```

---

### 本地开发运行

**1. 安装依赖**

```bash
cd gotobed-system
pip install -r requirements.txt
```

**2. 设置环境变量**

Windows PowerShell：

```powershell
$env:ADMIN_PASSWORD = "test123"
$env:SECRET_KEY = "dev-secret-key"
$env:FERNET_KEY = "<生成的密钥>"
```

Linux / macOS：

```bash
export ADMIN_PASSWORD="test123"
export SECRET_KEY="dev-secret-key"
export FERNET_KEY="<生成的密钥>"
```

**3. 启动**

```bash
python run.py
```

访问 `http://localhost:5000`。

---

## 配置说明

### 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `ADMIN_PASSWORD` | 是 | 管理员登录密码 | `admin123` |
| `SECRET_KEY` | 是 | Flask session 密钥 | `dev-secret-key` |
| `FERNET_KEY` | 是 | 密码加密密钥（Fernet） | 无 |
| `SMTP_HOST` | 否 | SMTP 服务器地址 | `smtp.qq.com` |
| `SMTP_PORT` | 否 | SMTP 端口 | `465` |
| `SMTP_USER` | 否 | 发件人邮箱 | 无 |
| `SMTP_PASS` | 否 | 邮箱授权码 | 无 |

### 预设打卡时间（北京时间）

| Cron 表达式 | 时间 |
|-------------|------|
| `10 9 * * *` | 每天 09:10 |
| `30 9 * * *` | 每天 09:30 |
| `10 10 * * *` | 每天 10:10 |
| `30 10 * * *` | 每天 10:30 |

---

## 使用说明

### 1. 登录管理后台

打开系统地址，输入管理员密码登录。

### 2. 添加用户

点击「新增用户」，填写：

- **账号**（必填）：学工平台用户名
- **密码**（必填）：学工平台密码
- **密保问题/答案**（选填）：仅在触发二次验证时需要
- **通知邮箱**（选填）：查寝结果发送地址
- **打卡时间**（必填）：可多选，至少选一个

### 3. 查看日志

在「执行日志」页面可按用户筛选，查看每次查寝的执行状态和结果。

### 4. 启用/禁用用户

在用户列表中点击「启用」/「禁用」按钮，可临时暂停某个用户的定时任务。

---

## 目录结构

```
gotobed-system/
├── app/
│   ├── __init__.py          # Flask app 工厂
│   ├── models.py            # 数据模型 (User, Log)
│   ├── crypto.py            # 密码加密工具
│   ├── email_sender.py      # 邮件发送
│   ├── scheduler.py         # APScheduler 调度
│   ├── routes/
│   │   ├── __init__.py      # 蓝图注册
│   │   ├── auth.py          # 登录/登出
│   │   ├── users.py         # 用户 CRUD
│   │   └── logs.py          # 日志查看
│   ├── tasks/
│   │   └── gotobed.py       # 查寝执行器
│   ├── templates/           # HTML 模板
│   └── static/              # CSS 样式
├── run.py                   # 入口
├── requirements.txt         # Python 依赖
├── Dockerfile               # Docker 构建文件
├── docker-compose.yml       # Docker 编排
└── .env.example             # 环境变量模板
```

---

## 常见问题

### Q: 部署后浏览器打不开？

检查服务器防火墙是否开放 5000 端口：
```bash
# Ubuntu
sudo ufw allow 5000

# CentOS
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

### Q: 邮件通知不生效？

1. 确认 `.env` 中 SMTP 配置正确
2. QQ 邮箱需要使用授权码（非登录密码）
3. 检查是否被判定为垃圾邮件

### Q: 如何更换管理员密码？

修改 `.env` 中的 `ADMIN_PASSWORD`，然后重启容器：
```bash
docker-compose restart
```

### Q: 数据库文件在哪里？

Docker 部署时，SQLite 数据库文件在 `gotobed-system/data/gotobed.db`，通过 volume 挂载持久化。

### Q: 如何修改打卡时间预设？

编辑 `gotobed-system/app/routes/users.py` 中的 `CRON_PRESETS` 字典，添加或修改 cron 表达式和描述。修改后需重启服务。

### Q: 和 GitHub Actions 可以同时用吗？

可以。两套系统完全独立，原 GitHub Actions 的脚本和 workflow 未做任何修改。
