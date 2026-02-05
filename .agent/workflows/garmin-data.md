---
description: 获取和分析 Garmin 健康数据
---

# Garmin 健康数据分析

此 workflow 帮助你获取和分析 Garmin 健康数据。

## 前提条件

1. 你需要有一个 Garmin Connect 账号（国际版或中国版）
2. 确保已配置环境变量

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

### 2. 配置内容说明

```.env
# 你的佳明账号邮箱
GARMIN_EMAIL=your_email@example.com

# 你的佳明账号密码
GARMIN_PASSWORD=your_password

# 是否使用中国版
# true = 中国版 (connect.garmin.cn)
# false = 国际版 (connect.garmin.com)
IS_CN=false
```

### 3. 构建和安装 MCP 服务器

// turbo
```bash
uv build
```

// turbo
```bash
uv tool install --force dist/mcp_server_garmincn-0.1.0.tar.gz
```

### 4. 测试数据获取

// turbo
```bash
source ~/.zshrc && uv run python3 fetch_garmin_data.py
```

## 可用的数据分析命令

获取数据后，你可以让 AI 帮你分析：

- "分析我最近的睡眠质量"
- "查看我的跑步训练情况"
- "分析我的心率变化趋势"
- "获取我今天的步数和卡路里消耗"

## 故障排除

### 问题：认证失败

1. 检查 .env 文件中的邮箱和密码是否正确
2. 确认 IS_CN 设置是否正确（国际版用 false，中国版用 true）
3. 清理 token 缓存：`rm -rf ~/.garminconnect`

### 问题：找不到活动数据

1. 确保你的佳明账号有关联的设备
2. 确保设备数据已同步到云端
3. 检查 IS_CN 设置是否与你的账号区域匹配
