# Garmin MCP Server & Data Analysis Suite

[![MCP](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.13+-green)](https://www.python.org/)

这是一个基于 Model Context Protocol (MCP) 的 Garmin 数据服务，同时包含了一套强大的 Python 脚本工具箱，用于深度分析你的 Garmin 健康与运动数据。

---

## 📋 开发路线图 (Roadmap)

> 以下是本项目的功能演进计划。欢迎通过 Issue 提出建议。

### ✅ 已完成 (Done)

- [x] **MCP Server 基础功能** - 让 AI 通过 MCP 协议访问 Garmin 数据
- [x] **健康分析脚本** - 心率、压力、HRV、身体电量、血氧综合报告
- [x] **睡眠分析脚本** - 30天趋势、运动关联分析、睡眠质量评分
- [x] **跑步分析脚本** - 目标评估、配速策略、VDOT 计算
- [x] **本地 JSON 缓存** - 历史数据本地持久化，减少 API 调用 90%+

### 🚧 进行中 (In Progress)

- [ ] **其他分析脚本接入缓存** - `analyze_running_goals.py` 等

### 📅 计划中 (Planned)

| 优先级 | 功能 | 描述 | 预计价值 |
|:---:|---|---|---|
| P1 | **SQLite 数据仓库** | 将 JSON 缓存升级为 SQLite 结构化存储 | SQL 查询、跨数据关联、长期趋势分析 |
| P1 | **MCP Server 查询本地数据** | AI 可直接查询本地数据库，无需每次调 API | 秒级响应、无 Rate Limit 风险 |
| P2 | **增量同步引擎** | 自动化数据同步 (`sync.py --auto`) | 数据始终最新 |
| P2 | **Jupyter Notebook 模板** | 可视化分析模板 | 图表展示、交互式探索 |
| P3 | **数据导出** | 支持导出为 CSV/Parquet | 便于其他工具使用 |
| P3 | **训练负荷分析** | 基于 TSS/ATL/CTL 的疲劳与恢复模型 | 科学化训练指导 |

---

## ✨ 主要功能 (Features)

### 1. 🤖 MCP Server
提供给 AI 助手使用的工具接口，使其能够读取你的 Garmin 数据并回答相关问题。

### 2. 📊 深度分析脚本 (Analysis Scripts)

> **注意**：这些分析脚本是本项目独有的扩展功能，基于原 MCP 服务能力构建，用于生成详细的终端报告。

| 脚本 | 功能 | 数据范围 |
|---|---|---|
| `fetch_health_analysis.py` | 💓 综合健康报告（心率、压力、HRV、电量、血氧） | 最近 7 天 |
| `fetch_sleep_analysis.py` | 💤 睡眠趋势与运动关联分析 | 最近 30 天 |
| `analyze_running_goals.py` | 🏃 跑步目标评估与建议 | 最近 20 次活动 |
| `analyze_effort.py` | 🕵️ 单次跑步强度深度拆解 | 指定活动 |
| `analyze_vdot.py` | ⚡ VDOT 跑力与配速计算 | 基于成绩 |

### 3. �️ 本地数据缓存

项目内置智能缓存系统 (`cache_manager.py`)，采用**本地优先策略**：

- **历史数据**：从本地 JSON 文件读取（毫秒级）
- **近期数据**（最近 2 天）：从 API 获取并更新缓存（保证数据新鲜度）

**效果对比**：

| 场景 | 改造前 | 改造后 |
|---|:---:|:---:|
| 睡眠分析 API 调用 | ~30 次 | **~3 次** |
| 健康分析 API 调用 | ~39 次 | **~23 次** |
| Rate Limit 风险 | 高 | **显著降低** |
| 重复运行速度 | 10-30 秒 | **< 2 秒** |

---

## 🚀 快速开始 (Getting Started)

### 1. 克隆项目
```bash
git clone https://github.com/TZX33/garmincn-mcp.git
cd garmincn-mcp
```

### 2. 环境配置
本项目使用 `uv` 进行包管理，也支持标准的 `pip`。

推荐创建 `.env` 文件来管理敏感信息：
```bash
cp .env.example .env
```
编辑 `.env` 文件，填入你的 Garmin 账号信息：
```properties
EMAIL=your_email@example.com
PASSWORD=your_password
# 如果是佳明中国区账号，请设置为 true；国际区账号保持 false
IS_CN=false
```

### 3. 安装依赖

使用 `uv` (推荐):
```bash
uv sync
```

或者使用 `pip`:
```bash
pip install -e .
```

---

## 🛠️ 使用指南 (Usage)

### 运行分析脚本

使用 `uv run` 确保在正确的虚拟环境中运行：

```bash
# 查看综合健康报告
uv run python fetch_health_analysis.py

# 查看睡眠分析（30天趋势）
uv run python fetch_sleep_analysis.py

# 分析最近的跑步目标
uv run python analyze_running_goals.py

# 深度分析最近一次跑步的努力程度
uv run python analyze_effort.py
```

### 运行 MCP Server

#### 方法 A: 使用 `uvx` 直接运行 (推荐)
如果你安装了 `uv`，可以直接作为工具运行：
```bash
uvx --from git+https://github.com/TZX33/garmincn-mcp.git mcp-server-garmincn
```

#### 方法 B: 本地构建运行
```bash
uv build
uv tool install dist/*.whl --force
mcp-server-garmincn
```

#### 在 Cherry Studio / Claude Desktop 中配置
在你的 MCP 客户端配置文件中添加：

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/garmincn-mcp",
        "run",
        "mcp-server-garmincn"
      ],
      "env": {
        "EMAIL": "your_email@example.com",
        "PASSWORD": "your_password",
        "IS_CN": "false"
      }
    }
  }
}
```

---

## 🧠 数据分析方式对比

本项目支持多种数据分析方式，各有优劣：

| 方式 | 适用场景 | 优势 | 劣势 |
|---|---|---|---|
| **📜 终端脚本** | 日常快速查看 | 一键运行、结果清晰 | 固定问题、无图表 |
| **🤖 MCP + AI** | 即兴探索 | 自然语言、灵活提问 | 依赖 AI 能力 |
| **📓 Jupyter** | 深度分析 | 可视化、交互式 | 需编程技能 |
| **📊 仪表盘** | 长期追踪 | 专业图表、告警 | 设置成本高 |

**推荐策略**：
- 日常使用 → 终端脚本
- 特定问题 → MCP + AI 对话
- 季度复盘 → Jupyter Notebook

---

## 📁 项目结构

```
garmincn-mcp/
├── src/mcp_server_garmincn/    # MCP Server 核心代码（原仓库）
├── cache_manager.py            # 本地缓存管理器
├── fetch_health_analysis.py    # 综合健康分析脚本
├── fetch_sleep_analysis.py     # 睡眠趋势分析脚本
├── analyze_running_goals.py    # 跑步目标分析脚本
├── analyze_effort.py           # 运动强度分析脚本
├── analyze_vdot.py             # VDOT 跑力计算
├── data/cache/                 # 本地数据缓存（自动创建，已 gitignore）
├── .env.example                # 环境变量模板
└── pyproject.toml              # 项目配置
```

---

## ⚠️ 注意事项

- **安全性**：`.env` 文件和 `data/cache/` 目录包含敏感信息，已被 `.gitignore` 排除。
- **API 限制**：虽然缓存大幅减少了请求，但首次使用或长时间未同步时仍可能触发 Rate Limit。
- **数据来源**：所有数据来自非官方 Garmin Connect API (`garth`/`garminconnect`)。
- **分析结论**：脚本提供的评分和建议基于通用标准，请结合个人情况解读。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

如果你有新的分析需求或发现了 Bug，请在 [Issues](https://github.com/TZX33/garmincn-mcp/issues) 中告诉我们。

---

## 📄 License

MIT License. 本项目包含 AI 生成代码，你可以自由使用和修改。

---

## 🙏 致谢

- [guaidaoyiyoudao/garmincn-mcp](https://github.com/guaidaoyiyoudao/garmincn-mcp) - 原始 MCP Server 实现
- [garminconnect](https://github.com/cyberjunky/python-garminconnect) - Garmin Connect API 封装
- [Model Context Protocol](https://modelcontextprotocol.io/) - AI 工具调用协议