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

# 复制原脚本的 JS 文件（密码加密依赖）— 使用英文路径避免编码问题
COPY "gzlg助手/g5116.js" ./g5116.js

# 创建数据目录
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "run:app"]
