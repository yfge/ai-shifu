# 构建阶段
FROM node:20.11.1-alpine AS builder

WORKDIR /app

# 首先只复制依赖相关文件
COPY package.json package-lock.json* ./

# 安装依赖并清理缓存
RUN npm ci && \
    npm cache clean --force

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM node:20.11.1-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN apk add --no-cache libc6-compat

# 复制必要的文件
COPY --from=builder /app/package.json ./
COPY --from=builder /app/package-lock.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# 只安装生产依赖并清理
RUN npm ci --only=production && \
    npm cache clean --force && \
    rm -rf /root/.cache && \
    rm -rf /root/.npm && \
    rm -rf /tmp/*

EXPOSE ${PORT:-3000}

# 使用非 root 用户运行
USER node

# 启动应用
CMD ["npm", "start"]
