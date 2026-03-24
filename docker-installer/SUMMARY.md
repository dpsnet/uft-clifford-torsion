# OpenClaw Docker 一键安装包 - 创建完成

## 📦 包内容

```
openclaw-docker-installer/
├── README.md                 # 主文档
├── LICENSE                   # MIT 许可证
├── Dockerfile               # Docker 镜像构建文件
├── docker-compose.yml       # Docker Compose 配置
├── install.sh               # 一键安装脚本
├── quickstart.sh            # 快速启动脚本
├── Makefile                 # 管理命令
├── .env.example             # 环境变量示例
├── config/
│   └── openclaw.yaml       # OpenClaw 配置文件
└── SUMMARY.md              # 本文件
```

## 🚀 使用方法

### 1. 在线安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/dpsnet/openclaw-docker/main/install.sh | bash
```

### 2. 本地安装

```bash
# 解压安装包
tar -xzf openclaw-docker-installer.tar.gz
cd openclaw-docker-installer

# 运行安装
./install.sh
```

### 3. 使用 Makefile

```bash
# 查看所有命令
make help

# 安装
make install

# 启动
make start

# 停止
make stop

# 查看日志
make logs
```

## 📋 功能特性

- ✅ 支持 Linux / macOS / Windows (WSL)
- ✅ 一键安装，自动配置
- ✅ 交互式 API 密钥配置
- ✅ 多种 AI 模型支持（OpenAI、Anthropic、Kimi、Google）
- ✅ 多种 IM 通道（Telegram、Discord、Slack、飞书、钉钉）
- ✅ 可选 PostgreSQL 数据库
- ✅ 可选 Redis 缓存
- ✅ 数据持久化
- ✅ 自动备份/恢复
- ✅ 健康检查
- ✅ 资源限制配置

## 🔧 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 内存
- 10GB+ 磁盘空间

## 🌐 默认端口

| 端口 | 服务 | 说明 |
|------|------|------|
| 3000 | Web UI | OpenClaw 网页界面 |
| 8080 | API Gateway | API 网关服务 |

## 📂 数据持久化

- 工作空间：`./data/workspace` 或 Docker volume
- 记忆存储：`./data/memory` 或 Docker volume
- 配置文件：`./config/`

## 🔒 安全配置

- 非 root 用户运行容器
- 只读挂载配置文件
- 健康检查
- 资源限制

## 📝 后续步骤

1. 将安装包上传到 GitHub 或其他仓库
2. 更新 README.md 中的仓库地址
3. 测试安装脚本
4. 发布版本

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📄 许可证

MIT License

---

创建时间: 2026-03-24
版本: 1.0.0
