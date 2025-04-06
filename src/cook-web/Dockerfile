# 构建阶段
FROM node:20.11.1-alpine AS builder
# 使用 pnpm
RUN corepack enable
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

WORKDIR /app

# 首先只复制依赖相关文件
COPY package.json pnpm-lock.yaml* ./

# 安装依赖并清理缓存
RUN pnpm install --frozen-lockfile && \
    pnpm store prune

# 复制源代码
COPY . .

# 构建应用
RUN pnpm build

# 生产阶段
FROM node:20.11.1-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN corepack enable && \
    apk add --no-cache libc6-compat

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

# 复制必要的文件
COPY --from=builder /app/package.json ./
COPY --from=builder /app/pnpm-lock.yaml ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# 只安装生产依赖并清理
RUN pnpm install --prod --frozen-lockfile && \
    pnpm store prune && \
    rm -rf /root/.cache && \
    rm -rf /root/.npm && \
    rm -rf /tmp/*

EXPOSE ${PORT:-3000}

# 使用非 root 用户运行
USER node

# 启动应用
CMD ["pnpm", "start"]
