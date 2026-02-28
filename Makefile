.PHONY: help install sync serve check

help:
	@echo "Garmin Coach Makefile"
	@echo "  make install  - 安装依赖"
	@echo "  make sync     - 同步 Garmin 数据到本地数据库"
	@echo "  make serve    - 启动 MCP 服务"
	@echo "  make check    - 运行代码检查"
	@echo "  make publish  - 将代码推送到 GitHub"

install:
	uv sync

sync:
	uv run garmin-coach sync

serve:
	uv run garmin-coach serve

stats:
	uv run garmin-coach stats

check:
	uv tool run ruff check src/

publish:
	@echo "Checking for sensitive data..."
	@git diff --cached --name-only | grep -E "(\.env|\.db)$$" && echo "❌ STOP! You are trying to commit sensitive files." && exit 1 || echo "✅ Safe to commit."
	git push origin master
