# Garmin 数据仓库结构 (Schema Reference)

本文档描述 SQLite 数据库 (`data/garmin.db`) 的结构，供 AI 进行自由查询时参考。

---

## 数据库位置

```
data/garmin.db
```

使用 `garmin_db.GarminDatabase` 类或 MCP 工具 `execute_custom_query` 进行查询。

---

## 表结构

### 1. `activities` - 活动记录

存储所有运动活动（跑步、力量训练、游泳等）的汇总数据。

| 字段 | 类型 | 说明 |
|---|---|---|
| `activity_id` | INTEGER | 主键，Garmin 活动 ID |
| `date` | TEXT | 活动日期 (YYYY-MM-DD) |
| `activity_type` | TEXT | 活动类型 (running, strength_training, swimming, cycling, walking...) |
| `activity_name` | TEXT | 活动名称 |
| `distance` | REAL | 距离（米） |
| `duration` | REAL | 时长（秒） |
| `average_speed` | REAL | 平均速度（米/秒）。**配速 = 1000 / average_speed / 60 分钟/公里** |
| `average_hr` | REAL | 平均心率 (bpm) |
| `max_hr` | REAL | 最大心率 (bpm) |
| `average_power` | REAL | 平均功率（瓦特，跑步/骑行适用） |
| `average_cadence` | REAL | 平均步频/踏频 (spm) |
| `stride_length` | REAL | 步幅（厘米） |
| `vertical_oscillation` | REAL | 垂直振幅（厘米） |
| `ground_contact_time` | REAL | 触地时间（毫秒） |
| `elevation_gain` | REAL | 累计爬升（米） |
| `training_effect` | REAL | 训练效果 (1.0-5.0) |
| `calories` | REAL | 消耗卡路里 |
| `summary_json` | TEXT | 原始 summaryDTO JSON |
| `metadata_json` | TEXT | 原始 metadataDTO JSON |
| `full_activity_json` | TEXT | 完整活动 JSON（包含更多细节） |
| `synced_at` | TEXT | 同步时间 |

**常用查询示例：**

```sql
-- 最近10次跑步
SELECT date, activity_name, distance/1000 as km, duration/60 as minutes, average_hr
FROM activities 
WHERE activity_type = 'running' 
ORDER BY date DESC 
LIMIT 10;

-- 计算配速（分钟/公里）
SELECT date, 1000/average_speed/60 as pace_min_per_km
FROM activities 
WHERE activity_type = 'running' AND average_speed > 0
ORDER BY date DESC LIMIT 5;

-- 本月跑步总距离
SELECT SUM(distance)/1000 as total_km 
FROM activities 
WHERE activity_type = 'running' AND date >= '2026-02-01';

-- 按活动类型统计
SELECT activity_type, COUNT(*) as count, SUM(duration)/3600 as total_hours
FROM activities 
GROUP BY activity_type 
ORDER BY count DESC;
```

---

### 2. `activity_laps` - 活动分段数据

存储每个活动的分段（公里/圈）详细数据。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `activity_id` | INTEGER | 关联的活动 ID |
| `lap_index` | INTEGER | 分段序号 (1, 2, 3...) |
| `distance` | REAL | 分段距离（米） |
| `duration` | REAL | 分段时长（秒） |
| `average_speed` | REAL | 分段平均速度（米/秒） |
| `average_hr` | REAL | 分段平均心率 |
| `max_hr` | REAL | 分段最大心率 |
| `average_power` | REAL | 分段平均功率 |
| `average_cadence` | REAL | 分段平均步频 |
| `elevation_gain` | REAL | 分段爬升 |
| `lap_json` | TEXT | 原始 lap JSON |

**常用查询示例：**

```sql
-- 某次活动的每公里配速
SELECT lap_index, 1000/average_speed/60 as pace, average_hr
FROM activity_laps 
WHERE activity_id = 21761882047 
ORDER BY lap_index;

-- 分析配速策略（前半程 vs 后半程）
WITH laps AS (
  SELECT lap_index, average_speed, 
         (SELECT COUNT(*) FROM activity_laps WHERE activity_id = 21761882047) as total_laps
  FROM activity_laps WHERE activity_id = 21761882047
)
SELECT 
  CASE WHEN lap_index <= total_laps/2 THEN 'first_half' ELSE 'second_half' END as half,
  AVG(average_speed) as avg_speed
FROM laps GROUP BY half;
```

---

### 3. `activity_hr_zones` - 心率区间

存储每个活动在不同心率区间的时间分布。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `activity_id` | INTEGER | 关联的活动 ID |
| `zone_number` | INTEGER | 心率区间编号 (1-5) |
| `secs_in_zone` | REAL | 在该区间的秒数 |
| `zone_low_boundary` | INTEGER | 区间下限心率 |

**常用查询示例：**

```sql
-- 某次活动的心率区间分布
SELECT zone_number, secs_in_zone/60 as minutes, zone_low_boundary
FROM activity_hr_zones 
WHERE activity_id = 21761882047 
ORDER BY zone_number;
```

---

### 4. `daily_metrics` - 每日健康指标

存储每天的各类健康数据（睡眠、心率、压力、HRV 等）。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `date` | TEXT | 日期 (YYYY-MM-DD) |
| `metric_type` | TEXT | 指标类型（见下表） |
| `data_json` | TEXT | JSON 格式的原始数据 |
| `synced_at` | TEXT | 同步时间 |

**指标类型 (metric_type) 枚举：**

| 类型 | 说明 | 关键字段路径 |
|---|---|---|
| `sleep` | 睡眠数据 | `dailySleepDTO.sleepTimeSeconds`, `sleepScores.overall.value` |
| `stress` | 压力数据 | `avgStressLevel`, `maxStressLevel` |
| `hrv` | 心率变异性 | `hrvSummary.lastNight`, `hrvSummary.weeklyAvg` |
| `body_battery` | 身体电量 | (数组) `[0].charged`, `[0].drained` |
| `respiration` | 呼吸数据 | `avgWakingRespirationValue`, `avgSleepingRespirationValue` |
| `spo2` | 血氧数据 | `averageSpO2`, `lowestSpO2` |
| `training_status` | 训练状态 | `trainingStatus`, `vo2MaxPreciseValue` |
| `training_readiness` | 训练准备程度 | `score`, `level` |

**常用查询示例：**

```sql
-- 最近7天的睡眠数据
SELECT date, 
       json_extract(data_json, '$.dailySleepDTO.sleepTimeSeconds')/3600.0 as sleep_hours,
       json_extract(data_json, '$.sleepScores.overall.value') as sleep_score
FROM daily_metrics 
WHERE metric_type = 'sleep' AND date >= date('now', '-7 days')
ORDER BY date DESC;

-- 最近7天的压力趋势
SELECT date, 
       json_extract(data_json, '$.avgStressLevel') as avg_stress
FROM daily_metrics 
WHERE metric_type = 'stress' AND date >= date('now', '-7 days')
ORDER BY date DESC;

-- HRV 趋势
SELECT date,
       json_extract(data_json, '$.hrvSummary.weeklyAvg') as weekly_avg_hrv
FROM daily_metrics 
WHERE metric_type = 'hrv' AND date >= date('now', '-14 days')
ORDER BY date DESC;
```

---

### 5. `sync_status` - 同步状态

记录数据同步的历史。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `sync_type` | TEXT | 同步类型 (full, incremental, date_range) |
| `started_at` | TEXT | 开始时间 |
| `completed_at` | TEXT | 完成时间 |
| `records_synced` | INTEGER | 同步的记录数 |
| `last_activity_date` | TEXT | 最后同步的活动日期 |
| `error` | TEXT | 错误信息（如有） |

---

### 6. `user_profile` - 用户档案

存储用户的基本信息，用于个性化训练分析。**只有一条记录**。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键（固定为 1） |
| `display_name` | TEXT | 显示名称 |
| `gender` | TEXT | 性别 ('male' / 'female') |
| `birth_date` | TEXT | 出生日期 (YYYY-MM-DD) |
| `height_cm` | REAL | 身高（厘米） |
| `weight_kg` | REAL | 体重（千克） |
| `resting_hr` | INTEGER | 静息心率 (bpm) |
| `max_hr_measured` | INTEGER | 实测最大心率 (bpm) |
| `lactate_threshold_hr` | INTEGER | 乳酸阈心率 (bpm) |
| `ftp_watts` | INTEGER | 功能阈值功率 (W) |
| `profile_json` | TEXT | 原始档案 JSON |
| `synced_at` | TEXT | 同步时间 |

**常用查询示例：**

```sql
-- 获取用户档案
SELECT * FROM user_profile WHERE id = 1;

-- 计算年龄（SQLite）
SELECT 
    display_name,
    (strftime('%Y', 'now') - strftime('%Y', birth_date)) - 
    (strftime('%m-%d', 'now') < strftime('%m-%d', birth_date)) as age,
    height_cm,
    weight_kg
FROM user_profile WHERE id = 1;
```

---

### 7. `weight_history` - 体重历史

存储体重和体成分的历史记录。

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | TEXT | 日期 (YYYY-MM-DD)，主键 |
| `weight_kg` | REAL | 体重（千克） |
| `bmi` | REAL | BMI 指数 |
| `body_fat_percent` | REAL | 体脂率 (%) |
| `muscle_mass_kg` | REAL | 肌肉量（千克） |
| `bone_mass_kg` | REAL | 骨骼量（千克） |
| `body_water_percent` | REAL | 体水分 (%) |
| `data_json` | TEXT | 原始数据 JSON |
| `synced_at` | TEXT | 同步时间 |

**常用查询示例：**

```sql
-- 最近30天体重趋势
SELECT date, weight_kg, body_fat_percent
FROM weight_history
ORDER BY date DESC
LIMIT 30;

-- 体重变化统计
SELECT 
    MIN(weight_kg) as min_weight,
    MAX(weight_kg) as max_weight,
    AVG(weight_kg) as avg_weight
FROM weight_history
WHERE date >= date('now', '-30 days');
```

---

## 跨表查询示例

### 运动后睡眠质量分析

```sql
-- 前一天有跑步 vs 无跑步的睡眠对比
WITH running_days AS (
  SELECT DISTINCT date FROM activities WHERE activity_type = 'running'
)
SELECT 
  CASE WHEN date(m.date, '-1 day') IN (SELECT date FROM running_days) 
       THEN '前一天跑步' ELSE '前一天未跑步' END as category,
  AVG(json_extract(m.data_json, '$.dailySleepDTO.sleepTimeSeconds'))/3600.0 as avg_sleep_hours
FROM daily_metrics m
WHERE m.metric_type = 'sleep'
GROUP BY category;
```

### 高强度训练后的 HRV 变化

```sql
-- 找出训练效果 > 3.5 的活动，查看次日 HRV
SELECT a.date as workout_date, 
       a.activity_name,
       a.training_effect,
       json_extract(h.data_json, '$.hrvSummary.weeklyAvg') as next_day_hrv
FROM activities a
LEFT JOIN daily_metrics h ON date(a.date, '+1 day') = h.date AND h.metric_type = 'hrv'
WHERE a.training_effect > 3.5
ORDER BY a.date DESC
LIMIT 10;
```

---

## 使用方式

### 通过 MCP 工具查询

使用 `execute_custom_query` 工具：

```
查询：SELECT date, distance/1000 as km FROM activities WHERE activity_type='running' ORDER BY date DESC LIMIT 5
```

### 通过 Python 代码查询

```python
from garmin_db import GarminDatabase

db = GarminDatabase()
results = db.execute_query("SELECT * FROM activities LIMIT 5")
for row in results:
    print(row)
```

---

## 数据同步

```bash
# 增量同步（日常使用）
uv run python sync_engine.py

# 全量同步（首次或重建）
uv run python sync_engine.py --full --days 90

# 查看统计
uv run python sync_engine.py --stats
```
