---
description: 获取和分析 Garmin 健康数据
---

# Garmin 健康数据分析 (GarminCoach)

此 workflow 帮助你获取和分析 Garmin 健康数据。经过架构重构，现在所有功能已整合至 `garmin-coach` CLI 工具中。

## 前提条件

1. 你需要有一个 Garmin Connect 账号（国际版或中国版）
2. 确保已配置环境变量 `.env`

## 配置步骤

### 1. 检查 .env 文件是否存在

```bash
cat .env 2>/dev/null || echo "需要创建 .env 文件"
```

如果不存在，复制示例文件并编辑：

```bash
cp .env.example .env
# 然后编辑 .env 填入你的账号信息
```

### 2. 初始化与安装

// turbo
```bash
make install
```

### 3. 数据同步与检查

你可以使用新的 CLI 进行数据同步：

// turbo
```bash
garmin-coach sync
```
或者首次使用时全量同步：
```bash
garmin-coach sync --full --days 90
```

查看数据库状态：
// turbo
```bash
garmin-coach stats
```

## 自动化运行 (GitHub Actions)

项目已配置 `.github/workflows/auto-sync.yml`，只要在 GitHub 仓库的 **Settings -> Secrets and variables -> Actions** 中配置好以下 Secrets，它就会在每天凌晨 2 点自动同步你的 Garmin 数据：

- `GARMIN_EMAIL`: 你的邮箱
- `GARMIN_PASSWORD`: 你的密码
- `IS_CN`: "true" 或 "false"

## MCP Server 使用方式

对于 AI Agent (Cursor / Claude Desktop / Trae)，你只需要将 MCP command 指向：

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uv",
      "args": [
        "--directory",
        "<你的项目绝对路径>",
        "run",
        "garmin-coach",
        "serve"
      ]
    }
  }
}
```
不再需要在 JSON 配置文件中明文写账号密码，程序会自动读取本地的 `.env`。
