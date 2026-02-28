# GarminCoach MCP Server & Data Analysis Suite

[![MCP](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.13+-green)](https://www.python.org/)

基于 Model Context Protocol (MCP) 的 Garmin 数据服务。让 AI 直接查询你的运动和健康数据。
作为 `lyros` 基础设施的一部分，通过配套的 `garmin-coach` Skill 提供专业的运动生理学分析。

---

## 🚀 快速开始

### 1. 配置环境变量
在项目根目录创建 `.env` 文件并填入 Garmin 账号信息：
```bash
cp .env.example .env
```

### 2. 同步数据 (支持全量与增量)
项目重构后提供了全局命令：
```bash
uv sync

# 首次全量同步
uv run garmin-coach sync --full --days 90

# 每日增量同步
uv run garmin-coach sync
```

### 3. 配置 MCP 客户端 (Cursor / Claude Desktop / Cherry Studio)

更新客户端配置中的工作目录绝对路径：

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uv",
      "args": [
        "--directory",
        "/你的完整路径/GarminCoach",
        "run",
        "garmin-coach",
        "serve"
      ]
    }
  }
}
```
*提示: 账号密码由于安全原因，由服务从 `.env` 内部加载，不再暴露给大模型客户端配置文件。*

### 4. 配合 Garmin Coach Skill 使用

确保 `garmin-coach` Skill 已安装。
现在你可以直接像教练一样向 AI 提问：
- "早上好教练，我今天的身体状态适合跑长距离吗？"
- "帮我复盘一下昨天那场间歇跑训练，我的心率区间控制得怎么样？"
- "我最近一周的静息心率和睡眠质量有关系吗？"

---

## 🛠 高级命令

```bash
# 查看数据库中的数据统计
uv run garmin-coach stats

# 启动 MCP 服务 (供 AI 客户端调用)
uv run garmin-coach serve
```

---

## 🗂 目录结构与架构
```text
GarminCoach/
├── pyproject.toml
├── .env                  # [请勿提交] 私密环境变量
├── data/                 # [请勿提交] SQLite 数据库
├── .github/workflows/    # 自动化任务 (定时同步)
└── src/garmin_coach/     # 核心功能包
    ├── cli.py            # 统一命令行入口
    ├── config.py         # 环境变量与配置加载
    ├── db/               # 数据库处理
    ├── sync/             # Garmin 官网数据抓取
    └── mcp/              # FastMCP 服务端与工具注册
```
