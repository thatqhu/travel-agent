# 使用 Node.js 18
FROM node:18-alpine

WORKDIR /app

# 复制依赖定义文件
COPY package.json ./

# 安装依赖
RUN cd /app && npm install

# 复制项目文件
COPY . .

# 暴露 Vite 默认端口
EXPOSE 5173

# 启动命令: --host 0.0.0.0 必须加，否则外部无法访问容器内的 Vite
CMD ["npm", "run", "dev", "--", "--host"]
