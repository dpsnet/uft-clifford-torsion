# OpenClaw Docker 一键安装包

快速在 Docker 中部署 OpenClaw AI 网关。

## 快速开始

### 方法一：使用安装脚本（推荐）

```bash
# 下载并运行安装脚本
curl -fsSL https://raw.githubusercontent.com/dpsnet/openclaw-docker/main/install.sh | bash

# 或使用 wget
wget -qO- https://raw.githubusercontent.com/dpsnet/openclaw-docker/main/install.sh | bash
```

### 方法二：手动 Docker Compose

```bash
# 1. 克隆仓库
git clone https://github.com/dpsnet/openclaw-docker.git
cd openclaw-docker

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 3. 启动服务
docker-compose up -d
```

## 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存
- 10GB+ 磁盘空间

## 配置说明

### 环境变量 (.env)

| 变量 | 说明 | 必需 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | 可选 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | 可选 |
| `KIMI_API_KEY` | Kimi API 密钥 | 可选 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 可选 |
| `DISCORD_BOT_TOKEN` | Discord Bot Token | 可选 |

### 端口映射

| 端口 | 服务 | 说明 |
|------|------|------|
| 3000 | Web UI | OpenClaw 网页界面 |
| 8080 | Gateway API | API 网关服务 |

## 使用说明

### 启动服务

```bash
docker-compose up -d
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f openclaw
```

### 停止服务

```bash
docker-compose down
```

### 更新到最新版本

```bash
docker-compose pull
docker-compose up -d
```

## 目录结构

```
openclaw-docker/
├── docker-compose.yml      # Docker Compose 配置
├── Dockerfile              # 镜像构建文件
├── install.sh              # 一键安装脚本
├── .env.example            # 环境变量示例
├── config/                 # 配置文件目录
│   └── openclaw.yaml      # OpenClaw 主配置
└── data/                   # 数据持久化目录
    ├── workspace/         # 工作空间
    └── memory/            # 记忆存储
```

## 故障排除

### 容器无法启动

```bash
# 检查日志
docker-compose logs openclaw

# 检查端口占用
sudo lsof -i :3000
sudo lsof -i :8080
```

### 权限问题

```bash
# 修复数据目录权限
sudo chown -R 1000:1000 ./data
```

### 网络问题

```bash
# 重置 Docker 网络
docker-compose down
docker network prune
docker-compose up -d
```

## 自定义配置

### 修改配置文件

编辑 `config/openclaw.yaml` 文件，然后重启服务：

```bash
docker-compose restart
```

### 添加自定义插件

将插件文件放入 `config/plugins/` 目录，然后在配置中启用。

## 许可证

MIT License - 详见 LICENSE 文件

## 支持与反馈

- GitHub Issues: https://github.com/dpsnet/openclaw-docker/issues
- OpenClaw 官方: https://github.com/openclaw/openclaw
