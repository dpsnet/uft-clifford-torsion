#!/bin/bash
#
# OpenClaw Docker 一键安装脚本
# 支持 Linux、macOS 和 Windows (WSL)
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 版本信息
VERSION="1.0.0"
OPENCLAW_VERSION="2026.2.13"

# 打印彩色消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查系统要求
check_requirements() {
    print_info "检查系统要求..."
    
    # 检查操作系统
    OS="$(uname -s)"
    case "$OS" in
        Linux*)     PLATFORM=Linux;;
        Darwin*)    PLATFORM=Mac;;
        CYGWIN*|MINGW*|MSYS*) PLATFORM=Windows;;
        *)          PLATFORM="UNKNOWN:$OS";;
    esac
    
    print_info "检测到操作系统: $PLATFORM"
    
    # 检查 Docker
    if ! command_exists docker; then
        print_error "Docker 未安装"
        print_info "请访问 https://docs.docker.com/get-docker/ 安装 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command_exists docker-compose; then
        if docker compose version >/dev/null 2>&1; then
            DOCKER_COMPOSE="docker compose"
        else
            print_error "Docker Compose 未安装"
            print_info "请访问 https://docs.docker.com/compose/install/ 安装 Docker Compose"
            exit 1
        fi
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    # 检查 Docker 守护进程
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker 守护进程未运行"
        print_info "请启动 Docker 服务:"
        print_info "  Linux: sudo systemctl start docker"
        print_info "  macOS: 启动 Docker Desktop"
        exit 1
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df -BG "$HOME" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 10 ]; then
        print_warning "可用磁盘空间不足 10GB，建议清理后再安装"
        read -p "是否继续安装? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_success "系统检查通过"
}

# 下载安装文件
download_files() {
    print_info "下载 OpenClaw Docker 配置文件..."
    
    INSTALL_DIR="${INSTALL_DIR:-$HOME/openclaw-docker}"
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # 下载文件
    BASE_URL="https://raw.githubusercontent.com/dpsnet/openclaw-docker/main"
    
    # 如果本地有文件，优先使用本地文件
    if [ -f "$0" ] && [ -f "docker-compose.yml" ]; then
        print_info "使用本地文件..."
        cp "$0" install.sh 2>/dev/null || true
    else
        # 从远程下载
        print_info "从 GitHub 下载配置文件..."
        curl -fsSL -o docker-compose.yml "$BASE_URL/docker-compose.yml" || wget -q "$BASE_URL/docker-compose.yml"
        curl -fsSL -o Dockerfile "$BASE_URL/Dockerfile" || wget -q "$BASE_URL/Dockerfile"
        curl -fsSL -o .env.example "$BASE_URL/.env.example" || wget -q "$BASE_URL/.env.example"
        curl -fsSL -o install.sh "$BASE_URL/install.sh" || wget -q "$BASE_URL/install.sh"
        chmod +x install.sh
    fi
    
    print_success "文件下载完成"
}

# 配置环境变量
setup_environment() {
    print_info "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        
        # 提示用户输入 API 密钥
        echo
        print_info "请配置你的 AI 模型 API 密钥（可选，可后续在 .env 文件中配置）："
        echo
        
        read -p "OpenAI API Key (按回车跳过): " OPENAI_KEY
        if [ -n "$OPENAI_KEY" ]; then
            sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_KEY/" .env
        fi
        
        read -p "Anthropic API Key (按回车跳过): " ANTHROPIC_KEY
        if [ -n "$ANTHROPIC_KEY" ]; then
            sed -i "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$ANTHROPIC_KEY/" .env
        fi
        
        read -p "Kimi API Key (按回车跳过): " KIMI_KEY
        if [ -n "$KIMI_KEY" ]; then
            sed -i "s/KIMI_API_KEY=.*/KIMI_API_KEY=$KIMI_KEY/" .env
        fi
        
        read -p "Telegram Bot Token (按回车跳过): " TG_TOKEN
        if [ -n "$TG_TOKEN" ]; then
            sed -i "s/TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=$TG_TOKEN/" .env
        fi
        
        read -p "Discord Bot Token (按回车跳过): " DISCORD_TOKEN
        if [ -n "$DISCORD_TOKEN" ]; then
            sed -i "s/DISCORD_BOT_TOKEN=.*/DISCORD_BOT_TOKEN=$DISCORD_TOKEN/" .env
        fi
        
        echo
        print_success "环境变量配置完成"
        print_info "你可以随时编辑 .env 文件修改配置"
    else
        print_warning ".env 文件已存在，跳过配置"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建工作目录..."
    
    mkdir -p config
    mkdir -p data/workspace
    mkdir -p data/memory
    
    # 创建默认配置文件
    if [ ! -f "config/openclaw.yaml" ]; then
        cat > config/openclaw.yaml << 'EOF'
# OpenClaw 配置文件

# 网关配置
gateway:
  host: 0.0.0.0
  port: 8080
  
# Web UI 配置
web:
  host: 0.0.0.0
  port: 3000
  
# 日志配置
logging:
  level: info
  format: json
  
# 心跳配置
heartbeat:
  enabled: true
  interval: 30000
  
# 模型配置
models:
  default: kimi-coding/k2p5
  available:
    - kimi-coding/k2p5
    - openai/gpt-4
    - anthropic/claude-3-opus
EOF
    fi
    
    print_success "目录创建完成"
}

# 启动服务
start_services() {
    print_info "启动 OpenClaw 服务..."
    
    # 拉取最新镜像
    $DOCKER_COMPOSE pull
    
    # 启动服务
    $DOCKER_COMPOSE up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 5
    
    # 检查服务状态
    if $DOCKER_COMPOSE ps | grep -q "Up"; then
        print_success "OpenClaw 服务启动成功！"
        echo
        print_info "访问地址："
        print_info "  Web UI: http://localhost:3000"
        print_info "  API Gateway: http://localhost:8080"
        echo
        print_info "查看日志: $DOCKER_COMPOSE logs -f"
        print_info "停止服务: $DOCKER_COMPOSE down"
    else
        print_error "服务启动失败，请检查日志："
        $DOCKER_COMPOSE logs
        exit 1
    fi
}

# 显示安装信息
show_info() {
    echo
    echo "========================================"
    print_success "OpenClaw Docker 安装完成！"
    echo "========================================"
    echo
    print_info "安装目录: $INSTALL_DIR"
    print_info "版本: $OPENCLAW_VERSION"
    echo
    print_info "常用命令："
    print_info "  启动服务: cd $INSTALL_DIR && $DOCKER_COMPOSE up -d"
    print_info "  停止服务: cd $INSTALL_DIR && $DOCKER_COMPOSE down"
    print_info "  查看日志: cd $INSTALL_DIR && $DOCKER_COMPOSE logs -f"
    print_info "  更新版本: cd $INSTALL_DIR && $DOCKER_COMPOSE pull && $DOCKER_COMPOSE up -d"
    echo
    print_info "配置文件："
    print_info "  环境变量: $INSTALL_DIR/.env"
    print_info "  主配置: $INSTALL_DIR/config/openclaw.yaml"
    echo
    print_info "文档: https://docs.openclaw.ai"
    print_info "GitHub: https://github.com/openclaw/openclaw"
    echo
}

# 主函数
main() {
    echo
    echo "========================================"
    echo "  OpenClaw Docker 一键安装脚本 v$VERSION"
    echo "========================================"
    echo
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --with-db)
                WITH_DB=true
                shift
                ;;
            --with-cache)
                WITH_CACHE=true
                shift
                ;;
            -h|--help)
                echo "用法: $0 [选项]"
                echo
                echo "选项:"
                echo "  -d, --dir <目录>      指定安装目录 (默认: ~/openclaw-docker)"
                echo "  --with-db             同时安装 PostgreSQL 数据库"
                echo "  --with-cache          同时安装 Redis 缓存"
                echo "  -h, --help            显示帮助信息"
                echo
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行安装步骤
    check_requirements
    download_files
    create_directories
    setup_environment
    start_services
    show_info
}

# 运行主函数
main "$@"
