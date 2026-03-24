# OpenClaw Docker 镜像
# 基于 Node.js 22 构建

FROM node:22-slim AS base

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    build-essential \
    libssl-dev \
    libffi-dev \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 pnpm
RUN npm install -g pnpm@10.23.0

# 开发阶段 - 用于本地开发
FROM base AS development

# 安装开发工具
RUN apt-get update && apt-get install -y \
    vim \
    nano \
    htop \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 设置开发环境变量
ENV NODE_ENV=development
ENV OPENCLAW_PROFILE=dev

# 复制 package.json
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 暴露端口
EXPOSE 3000 8080

# 启动命令
CMD ["pnpm", "dev"]

# 生产阶段
FROM base AS production

# 设置生产环境变量
ENV NODE_ENV=production
ENV OPENCLAW_PROFILE=default

# 复制构建好的文件
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/dist ./dist
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/extensions ./extensions
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/skills ./skills
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/docs ./docs
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/assets ./assets
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/openclaw.mjs ./openclaw.mjs
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/package.json ./package.json

# 复制生产依赖
COPY --from=openclaw:latest /usr/lib/node_modules/openclaw/node_modules ./node_modules

# 创建工作目录
RUN mkdir -p /root/.openclaw/workspace /root/.openclaw/memory /root/.openclaw/config

# 设置权限
RUN chown -R node:node /app /root/.openclaw

# 切换到非 root 用户
USER node

# 暴露端口
EXPOSE 3000 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
ENTRYPOINT ["node", "openclaw.mjs"]
CMD ["gateway"]
