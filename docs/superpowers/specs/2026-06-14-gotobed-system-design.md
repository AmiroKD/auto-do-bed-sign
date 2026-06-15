# 查寝管理系统 设计文档

> **日期**: 2026-06-14
> **版本**: v1.0
> **状态**: 待审阅

## 1. 概述

将现有 GitHub Actions 定时查寝脚本（`goToBed.py`）重构为自托管的 Web 管理系统，支持多用户管理、定时任务调度和执行日志查看。

### 1.1 目标

- 提供 Web 管理界面，支持增删改查查寝用户
- 每个用户可独立配置 cron 定时任务时间
- 支持必填字段（账号、密码）和选填字段（密保问题/答案）
- Docker 单容器部署，一键启动

### 1.2 范围

- **包含**：查寝功能（gotobed），不含签到（dowork）
- **规模**：1-20 个用户

## 2. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Web 框架 | Flask | 轻量，与现有 Python 脚本无缝集成 |
| 定时调度 | APScheduler | 进程内调度，无需外部依赖 |
| 数据库 | SQLite | 小规模足够，零配置 |
| ORM | Flask-SQLAlchemy | Flask 生态标准 |
| 认证 | Flask-Login | 管理员认证 |
| 密码加密 | cryptography.fernet | 对称加密，存储用户密码 |
| CSS 框架 | Bootstrap 5 | 简洁实用 |
| 容器化 | Docker + docker-compose | 一键部署 |
| WSGI 服务器 | Gunicorn | 生产级 |

## 3. 架构

```
┌─────────────────────────────────────────────────┐
│                   Docker 容器                     │
│                                                   │
│  ┌──────────┐    ┌──────────────┐    ┌─────────┐ │
│  │  Flask    │    │  APScheduler │    │ SQLite  │ │
│  │  Web UI   │◄──►│  定时调度器   │◄──►│ 数据库   │ │
│  │ (管理后台) │    │ (cron任务)    │    │(用户/日志)│ │
│  └──────────┘    └──────┬───────┘    └─────────┘ │
│       ▲                 │                         │
│       │                 ▼                         │
│  ┌────┴────┐    ┌──────────────┐                  │
│  │ 浏览器   │    │  goToBed     │                  │
│  │(管理员)  │    │  查寝执行器   │                  │
│  └─────────┘    └──────────────┘                  │
└─────────────────────────────────────────────────┘
```

### 3.1 核心模块

1. **Web 管理后台** — Flask + Jinja2，管理员密码认证
2. **定时调度器** — APScheduler CronTrigger，从数据库读取用户的 cron 表达式
3. **查寝执行器** — 重构自 `goToBed.py`，函数化，参数传入凭据
4. **数据存储** — SQLite，用户信息 + 执行日志

## 4. 数据模型

### 4.1 users 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| username | TEXT | NOT NULL | 学工平台账号 |
| password_encrypted | TEXT | NOT NULL | 学工平台密码（Fernet 加密） |
| principal | TEXT | NULLABLE | 密保问题（选填） |
| credential | TEXT | NULLABLE | 密保答案（选填） |
| email | TEXT | NULLABLE | 结果通知邮箱 |
| cron_expr | TEXT | NOT NULL | cron 表达式，如 `10 12 * * *` |
| enabled | BOOLEAN | DEFAULT TRUE | 是否启用 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | DEFAULT NOW | 更新时间 |

### 4.2 logs 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| user_id | INTEGER | FK → users.id | 关联用户 |
| status | TEXT | NOT NULL | `success` / `failure` |
| message | TEXT | NOT NULL | 执行结果详情 |
| executed_at | DATETIME | DEFAULT NOW | 执行时间 |

### 4.3 管理员认证

- 管理员密码通过环境变量 `ADMIN_PASSWORD` 设置
- Flask session secret 通过环境变量 `SECRET_KEY` 设置
- 密码加密密钥通过环境变量 `FERNET_KEY` 设置

## 5. Web 管理后台

### 5.1 页面

| 路由 | 页面 | 功能 |
|------|------|------|
| `/login` | 登录页 | 管理员输入密码 |
| `/` | 用户列表 | 展示所有用户，支持新增/编辑/删除/启禁用 |
| `/users/new` | 新增用户 | 表单：账号、密码、密保、邮箱、cron |
| `/users/<id>/edit` | 编辑用户 | 同上，密码留空表示不修改 |
| `/logs` | 执行日志 | 按用户筛选，分页，显示状态和结果 |

### 5.2 表单字段

- **账号**（必填）：学工平台用户名
- **密码**（必填，编辑时选填）：学工平台密码
- **密保问题**（选填）：二次验证用
- **密保答案**（选填）：二次验证用
- **通知邮箱**（选填）：查寝结果发送地址
- **Cron 表达式**（必填）：提供常用预设（每天20:10、每天22:00、自定义）
- **启用**（默认开启）：开关

## 6. 定时调度与执行

### 6.1 调度流程

1. 应用启动 → 从 SQLite 加载所有 `enabled=True` 的用户
2. 为每个用户注册 APScheduler `CronTrigger` 任务
3. 用户 CRUD 操作后，动态增删调度任务（无需重启）
4. 到达 cron 时间 → 触发查寝

### 6.2 查寝执行

重构自 `goToBed.py`，主要改动：

- **去除环境变量依赖**：凭据通过函数参数传入
- **函数化**：`def run_gotobed(username, password, principal=None, credential=None, email=None) -> dict`
- **保留核心逻辑**：验证码 OCR、登录、二次验证、cookie 获取、查寝签到、失败重试
- **结果记录**：执行完成后写入 logs 表
- **邮件通知**：保留，从用户配置读取邮箱地址
- **并发控制**：`max_instances=1`，同一用户不并行执行

### 6.3 重试策略

与原脚本一致：最多 5 次尝试，指数退避（5s, 10s, 20s, 40s, 60s），失败后发送邮件通知。

## 7. 目录结构

```
auto-do-bed-sign/
├── gzlg助手/                    # 原有脚本（保留不动）
├── gotobed-system/              # 新增管理系统
│   ├── app/
│   │   ├── __init__.py          # Flask app 工厂
│   │   ├── models.py            # SQLAlchemy 模型
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # 登录/登出
│   │   │   ├── users.py         # 用户 CRUD
│   │   │   └── logs.py          # 日志查看
│   │   ├── scheduler.py         # APScheduler 集成
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   └── gotobed.py       # 查寝执行（重构自原脚本）
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── login.html
│   │   │   ├── users/
│   │   │   │   ├── list.html
│   │   │   │   └── form.html
│   │   │   └── logs/
│   │   │       └── list.html
│   │   └── static/
│   │       └── style.css
│   ├── config.py                # 配置
│   ├── run.py                   # 入口
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── .github/workflows/           # 原有（保留不动）
└── README.md
```

## 8. Docker 部署

### docker-compose.yml

```yaml
version: '3.8'
services:
  gotobed:
    build: ./gotobed-system
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

**注意**：Dockerfile 需要将 `gzlg助手/g5116.js` 复制到容器内，因为查寝执行器依赖它进行密码加密。构建上下文设为项目根目录。

```env
ADMIN_PASSWORD=your-admin-password
SECRET_KEY=your-flask-secret-key
FERNET_KEY=your-fernet-key
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-email@qq.com
SMTP_PASS=your-email-auth-code
```

## 9. 安全设计

- 管理员密码通过环境变量设置，不在代码中硬编码
- 用户密码使用 Fernet 对称加密存储
- Flask session 使用随机 SECRET_KEY
- SQLite 数据通过 Docker volume 持久化
- 容器内设置 `TZ=Asia/Shanghai` 保证时间正确

## 10. 邮件通知

原脚本中 QQ 邮箱发件人凭据硬编码在 `emailSender.py` 中。管理系统改为通过环境变量配置：

```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-email@qq.com
SMTP_PASS=your-email-auth-code
```

重构后的邮件发送函数从环境变量读取配置，支持任意 SMTP 服务器。

## 11. 依赖清单

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
