#!/bin/bash
#
# OpenClaw 快速启动脚本
# 用于快速启动已安装的 OpenClaw

set -e

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 启动 OpenClaw...${NC}"

# 切换到脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查是否已安装
if [ ! -f ".env" ]; then
    echo "❌ OpenClaw 未安装"
    echo "请先运行: ./install.sh"
    exit 1
fi

# 启动服务
docker-compose up -d

# 等待服务启动
sleep 3

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ OpenClaw 启动成功！${NC}"
    echo ""
    echo "📱 Web UI: http://localhost:3000"
    echo "🔌 API: http://localhost:8080"
    echo ""
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
else
    echo "❌ 启动失败，请检查日志:"
    docker-compose logs
    exit 1
fi
