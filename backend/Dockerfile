# 使用轻量级 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 防止 Python 生成 .pyc 文件，并让 stdout 直接输出到日志
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 先复制依赖文件，利用 Docker 缓存层加速构建
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制其余代码 (在开发模式下，docker-compose 的 volume 会覆盖这里，但这步用于生产构建)
COPY . .

# 默认启动命令 (会被 docker-compose 覆盖)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
