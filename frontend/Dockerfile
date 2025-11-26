# 使用 Node.js 18
FROM node:18-alpine

WORKDIR /app

COPY package.json ./

RUN cd /app && npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
