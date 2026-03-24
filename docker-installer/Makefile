# OpenClaw Docker Makefile
# 简化 Docker 管理命令

.PHONY: help install start stop restart logs update clean build

# 默认目标
help:
	@echo "OpenClaw Docker 管理命令"
	@echo ""
	@echo "常用命令:"
	@echo "  make install    - 首次安装 OpenClaw"
	@echo "  make start      - 启动服务"
	@echo "  make stop       - 停止服务"
	@echo "  make restart    - 重启服务"
	@echo "  make logs       - 查看日志"
	@echo "  make status     - 查看服务状态"
	@echo "  make update     - 更新到最新版本"
	@echo "  make clean      - 清理数据（警告：会删除所有数据！）"
	@echo "  make backup     - 备份数据"
	@echo "  make restore    - 恢复数据"
	@echo ""
	@echo "高级命令:"
	@echo "  make build      - 重新构建镜像"
	@echo "  make shell      - 进入容器 shell"
	@echo "  make config     - 编辑配置文件"
	@echo "  make test       - 运行测试"

# 安装
install:
	@./install.sh

# 启动服务
start:
	@docker-compose up -d
	@echo "✅ OpenClaw 已启动"
	@echo "   Web UI: http://localhost:3000"
	@echo "   API: http://localhost:8080"

# 停止服务
stop:
	@docker-compose down
	@echo "✅ OpenClaw 已停止"

# 重启服务
restart:
	@docker-compose restart
	@echo "✅ OpenClaw 已重启"

# 查看日志
logs:
	@docker-compose logs -f --tail=100

# 查看状态
status:
	@docker-compose ps
	@echo ""
	@docker-compose stats --no-stream 2>/dev/null || true

# 更新版本
update:
	@echo "正在更新 OpenClaw..."
	@docker-compose pull
	@docker-compose up -d
	@echo "✅ 更新完成"

# 清理数据（危险操作！）
clean:
	@echo "⚠️  警告：这将删除所有 OpenClaw 数据！"
	@read -p "确定要继续吗? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose down -v; \
		docker volume rm openclaw-docker_openclaw_workspace openclaw-docker_openclaw_memory 2>/dev/null || true; \
		docker rmi openclaw-docker_openclaw 2>/dev/null || true; \
		echo "✅ 数据已清理"; \
	else \
		echo "已取消"; \
	fi

# 备份数据
backup:
	@mkdir -p backups
	@BACKUP_NAME="backup-$$(date +%Y%m%d-%H%M%S).tar.gz"; \
	docker-compose down; \
	tar -czf "backups/$$BACKUP_NAME" data/ config/; \
	docker-compose up -d; \
	echo "✅ 备份完成: backups/$$BACKUP_NAME"

# 恢复数据
restore:
	@echo "可用备份文件:"
	@ls -1 backups/ 2>/dev/null || echo "无备份文件"
	@echo ""
	@read -p "输入要恢复的备份文件名: " backup_file; \
	if [ -f "backups/$$backup_file" ]; then \
		docker-compose down; \
		tar -xzf "backups/$$backup_file"; \
		docker-compose up -d; \
		echo "✅ 恢复完成"; \
	else \
		echo "❌ 备份文件不存在"; \
	fi

# 重新构建
build:
	@docker-compose build --no-cache
	@echo "✅ 镜像构建完成"

# 进入容器 shell
shell:
	@docker-compose exec openclaw /bin/bash

# 编辑配置
config:
	@$${EDITOR:-vi} config/openclaw.yaml

# 运行测试
test:
	@docker-compose exec openclaw npm test 2>/dev/null || echo "测试未配置"

# 查看版本
version:
	@echo "OpenClaw Docker Installer v1.0.0"
	@docker-compose exec openclaw openclaw --version 2>/dev/null || echo "OpenClaw 未运行"
