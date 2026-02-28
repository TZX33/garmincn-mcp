#!/usr/bin/env python3
"""
Garmin SQLite 数据库管理器

提供结构化的本地数据存储，支持：
- 活动数据（汇总 + 分段 + 心率区间）
- 每日健康指标
- 时间序列数据（可选）

目录结构：
data/garmin.db
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager


from garmin_coach.config import config


class GarminDatabase:
    """SQLite 数据库管理器"""

    # 数据库版本，用于未来的 schema 迁移
    DB_VERSION = 1

    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为 config.db_path
        """
        if db_path is None:
            self.db_path = config.db_path
        else:
            self.db_path = Path(db_path)

        self._ensure_db_dir()
        self._init_schema()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 支持字典式访问
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self):
        """初始化数据库 schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 元数据表（存储数据库版本等信息）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)

            # 活动主表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    activity_type TEXT,
                    activity_name TEXT,
                    distance REAL,
                    duration REAL,
                    average_speed REAL,
                    average_hr REAL,
                    max_hr REAL,
                    average_power REAL,
                    average_cadence REAL,
                    stride_length REAL,
                    vertical_oscillation REAL,
                    ground_contact_time REAL,
                    elevation_gain REAL,
                    training_effect REAL,
                    calories REAL,
                    summary_json TEXT,
                    metadata_json TEXT,
                    full_activity_json TEXT,
                    synced_at TEXT
                )
            """)

            # 活动分段表（每公里/每圈）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_laps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id INTEGER NOT NULL,
                    lap_index INTEGER,
                    distance REAL,
                    duration REAL,
                    average_speed REAL,
                    average_hr REAL,
                    max_hr REAL,
                    average_power REAL,
                    average_cadence REAL,
                    stride_length REAL,
                    vertical_oscillation REAL,
                    ground_contact_time REAL,
                    elevation_gain REAL,
                    elevation_loss REAL,
                    lap_json TEXT,
                    FOREIGN KEY (activity_id) REFERENCES activities(activity_id) ON DELETE CASCADE
                )
            """)

            # 心率区间表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_hr_zones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id INTEGER NOT NULL,
                    zone_number INTEGER,
                    secs_in_zone REAL,
                    zone_low_boundary INTEGER,
                    FOREIGN KEY (activity_id) REFERENCES activities(activity_id) ON DELETE CASCADE
                )
            """)

            # 每日健康指标表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    date TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    data_json TEXT,
                    synced_at TEXT,
                    PRIMARY KEY (date, metric_type)
                )
            """)

            # 同步状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT,
                    last_sync_date TEXT,
                    items_synced INTEGER,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT
                )
            """)

            # 用户档案表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    display_name TEXT,
                    gender TEXT,
                    birth_date TEXT,
                    height_cm REAL,
                    weight_kg REAL,
                    resting_hr INTEGER,
                    max_hr_measured INTEGER,
                    lactate_threshold_hr INTEGER,
                    ftp_watts INTEGER,
                    profile_json TEXT,
                    synced_at TEXT
                )
            """)

            # 体重历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weight_history (
                    date TEXT PRIMARY KEY,
                    weight_kg REAL,
                    bmi REAL,
                    body_fat_percent REAL,
                    muscle_mass_kg REAL,
                    bone_mass_kg REAL,
                    body_water_percent REAL,
                    data_json TEXT,
                    synced_at TEXT
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_laps_activity ON activity_laps(activity_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_hr_zones_activity ON activity_hr_zones(activity_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_metrics_type ON daily_metrics(metric_type)"
            )

            # 设置数据库版本
            cursor.execute(
                """
                INSERT OR REPLACE INTO metadata (key, value, updated_at)
                VALUES ('db_version', ?, ?)
            """,
                (str(self.DB_VERSION), datetime.now().isoformat()),
            )

            conn.commit()

    # ==================== 活动数据操作 ====================

    def save_activity(
        self,
        activity_data: Dict,
        summary_data: Dict = None,
        metadata_data: Dict = None,
        full_data: Dict = None,
    ) -> int:
        """
        保存或更新活动数据

        Args:
            activity_data: 基础活动数据（来自 get_activities）
            summary_data: 汇总数据（来自 get_activity 的 summaryDTO）
            metadata_data: 元数据（来自 get_activity 的 metadataDTO）
            full_data: 完整活动数据（原始 JSON）

        Returns:
            activity_id
        """
        activity_id = activity_data.get("activityId")
        if not activity_id:
            raise ValueError("activity_data must contain 'activityId'")

        # 合并数据源
        summary = summary_data or activity_data

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO activities (
                    activity_id, date, activity_type, activity_name,
                    distance, duration, average_speed, average_hr, max_hr,
                    average_power, average_cadence, stride_length,
                    vertical_oscillation, ground_contact_time, elevation_gain,
                    training_effect, calories, summary_json, metadata_json,
                    full_activity_json, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    activity_id,
                    activity_data.get("startTimeLocal", "")[:10],  # 提取日期部分
                    activity_data.get("activityType", {}).get("typeKey"),
                    activity_data.get("activityName"),
                    summary.get("distance"),
                    summary.get("duration"),
                    summary.get("averageSpeed"),
                    summary.get("averageHR"),
                    summary.get("maxHR"),
                    summary.get("averagePower"),
                    summary.get("averageRunCadence")
                    or summary.get("averageRunningCadenceInStepsPerMinute"),
                    summary.get("strideLength") or summary.get("avgStrideLength"),
                    summary.get("verticalOscillation")
                    or summary.get("avgVerticalOscillation"),
                    summary.get("groundContactTime")
                    or summary.get("avgGroundContactTime"),
                    summary.get("elevationGain"),
                    summary.get("trainingEffect")
                    or summary.get("aerobicTrainingEffect"),
                    summary.get("calories"),
                    json.dumps(summary_data, ensure_ascii=False)
                    if summary_data
                    else None,
                    json.dumps(metadata_data, ensure_ascii=False)
                    if metadata_data
                    else None,
                    json.dumps(full_data, ensure_ascii=False) if full_data else None,
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            return activity_id

    def save_activity_laps(self, activity_id: int, laps: List[Dict]):
        """
        保存活动分段数据

        Args:
            activity_id: 活动ID
            laps: 分段数据列表（来自 get_activity_splits 的 lapDTOs）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 先删除旧数据
            cursor.execute(
                "DELETE FROM activity_laps WHERE activity_id = ?", (activity_id,)
            )

            for lap in laps:
                cursor.execute(
                    """
                    INSERT INTO activity_laps (
                        activity_id, lap_index, distance, duration,
                        average_speed, average_hr, max_hr, average_power,
                        average_cadence, stride_length, vertical_oscillation,
                        ground_contact_time, elevation_gain, elevation_loss, lap_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        activity_id,
                        lap.get("lapIndex"),
                        lap.get("distance"),
                        lap.get("duration"),
                        lap.get("averageSpeed"),
                        lap.get("averageHR"),
                        lap.get("maxHR"),
                        lap.get("averagePower"),
                        lap.get("averageRunCadence"),
                        lap.get("strideLength"),
                        lap.get("verticalOscillation"),
                        lap.get("groundContactTime"),
                        lap.get("elevationGain"),
                        lap.get("elevationLoss"),
                        json.dumps(lap, ensure_ascii=False),
                    ),
                )

            conn.commit()

    def save_activity_hr_zones(self, activity_id: int, zones: List[Dict]):
        """
        保存活动心率区间数据

        Args:
            activity_id: 活动ID
            zones: 心率区间数据列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 先删除旧数据
            cursor.execute(
                "DELETE FROM activity_hr_zones WHERE activity_id = ?", (activity_id,)
            )

            for zone in zones:
                cursor.execute(
                    """
                    INSERT INTO activity_hr_zones (
                        activity_id, zone_number, secs_in_zone, zone_low_boundary
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        activity_id,
                        zone.get("zoneNumber"),
                        zone.get("secsInZone"),
                        zone.get("zoneLowBoundary"),
                    ),
                )

            conn.commit()

    def get_activity(self, activity_id: int) -> Optional[Dict]:
        """获取单个活动数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM activities WHERE activity_id = ?", (activity_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_activity_full_data(self, activity_id: int) -> Optional[Dict]:
        """获取活动的完整原始数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT full_activity_json FROM activities WHERE activity_id = ?",
                (activity_id,),
            )
            row = cursor.fetchone()
            if row and row["full_activity_json"]:
                return json.loads(row["full_activity_json"])
            return None

    def get_activities_by_date(
        self, start_date: str, end_date: str = None
    ) -> List[Dict]:
        """
        按日期范围获取活动列表

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)，默认与 start_date 相同
        """
        end_date = end_date or start_date

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM activities
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC
            """,
                (start_date, end_date),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_activities_by_type(self, activity_type: str, limit: int = 20) -> List[Dict]:
        """
        按活动类型获取活动列表

        Args:
            activity_type: 活动类型 (如 'running', 'strength_training')
            limit: 最大返回数量
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM activities
                WHERE activity_type LIKE ?
                ORDER BY date DESC
                LIMIT ?
            """,
                (f"%{activity_type}%", limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_activities(self, limit: int = 20) -> List[Dict]:
        """获取最近的活动"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM activities
                ORDER BY date DESC
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_activity_laps(self, activity_id: int) -> List[Dict]:
        """获取活动的分段数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM activity_laps
                WHERE activity_id = ?
                ORDER BY lap_index
            """,
                (activity_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_activity_hr_zones(self, activity_id: int) -> List[Dict]:
        """获取活动的心率区间数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM activity_hr_zones
                WHERE activity_id = ?
                ORDER BY zone_number
            """,
                (activity_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def activity_exists(self, activity_id: int) -> bool:
        """检查活动是否已存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM activities WHERE activity_id = ?", (activity_id,)
            )
            return cursor.fetchone() is not None

    # ==================== 每日健康指标操作 ====================

    def save_daily_metric(self, date: str, metric_type: str, data: Any):
        """
        保存每日健康指标

        Args:
            date: 日期 (YYYY-MM-DD)
            metric_type: 指标类型 (如 'sleep', 'heart_rates', 'stress' 等)
            data: 数据（将被 JSON 序列化）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO daily_metrics (date, metric_type, data_json, synced_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    date,
                    metric_type,
                    json.dumps(data, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_daily_metric(self, date: str, metric_type: str) -> Optional[Dict]:
        """获取指定日期和类型的健康指标"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data_json FROM daily_metrics
                WHERE date = ? AND metric_type = ?
            """,
                (date, metric_type),
            )
            row = cursor.fetchone()
            if row and row["data_json"]:
                return json.loads(row["data_json"])
            return None

    def get_daily_metrics_range(
        self, start_date: str, end_date: str, metric_type: str = None
    ) -> List[Dict]:
        """
        获取日期范围内的健康指标

        Args:
            start_date: 开始日期
            end_date: 结束日期
            metric_type: 可选，指定类型
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if metric_type:
                cursor.execute(
                    """
                    SELECT date, metric_type, data_json, synced_at FROM daily_metrics
                    WHERE date >= ? AND date <= ? AND metric_type = ?
                    ORDER BY date
                """,
                    (start_date, end_date, metric_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT date, metric_type, data_json, synced_at FROM daily_metrics
                    WHERE date >= ? AND date <= ?
                    ORDER BY date, metric_type
                """,
                    (start_date, end_date),
                )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "date": row["date"],
                        "metric_type": row["metric_type"],
                        "data": json.loads(row["data_json"])
                        if row["data_json"]
                        else None,
                        "synced_at": row["synced_at"],
                    }
                )
            return results

    def daily_metric_exists(self, date: str, metric_type: str) -> bool:
        """检查每日指标是否已存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM daily_metrics
                WHERE date = ? AND metric_type = ?
            """,
                (date, metric_type),
            )
            return cursor.fetchone() is not None

    # ==================== 同步状态操作 ====================

    def log_sync_start(self, sync_type: str) -> int:
        """记录同步开始"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sync_status (sync_type, status, started_at)
                VALUES (?, 'running', ?)
            """,
                (sync_type, datetime.now().isoformat()),
            )
            conn.commit()
            return cursor.lastrowid

    def log_sync_complete(
        self,
        sync_id: int,
        items_synced: int,
        last_sync_date: str = None,
        error: str = None,
    ):
        """记录同步完成"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sync_status
                SET status = ?, items_synced = ?, last_sync_date = ?,
                    completed_at = ?, error_message = ?
                WHERE id = ?
            """,
                (
                    "error" if error else "completed",
                    items_synced,
                    last_sync_date,
                    datetime.now().isoformat(),
                    error,
                    sync_id,
                ),
            )
            conn.commit()

    def get_last_sync(self, sync_type: str) -> Optional[Dict]:
        """获取最后一次同步记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM sync_status
                WHERE sync_type = ? AND status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            """,
                (sync_type,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # ==================== 用户档案操作 ====================

    def save_user_profile(self, profile_data: Dict) -> None:
        """
        保存用户档案（只保留一条记录）

        Args:
            profile_data: 用户档案数据，可包含以下字段：
                - display_name: 显示名称
                - gender: 性别 ('male' / 'female')
                - birth_date: 出生日期 (YYYY-MM-DD)
                - height_cm: 身高（厘米）
                - weight_kg: 体重（千克）
                - resting_hr: 静息心率
                - max_hr_measured: 实测最大心率
                - lactate_threshold_hr: 乳酸阈心率
                - ftp_watts: 功能阈值功率
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO user_profile (
                    id, display_name, gender, birth_date, height_cm, weight_kg,
                    resting_hr, max_hr_measured, lactate_threshold_hr, ftp_watts,
                    profile_json, synced_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    profile_data.get("display_name"),
                    profile_data.get("gender"),
                    profile_data.get("birth_date"),
                    profile_data.get("height_cm"),
                    profile_data.get("weight_kg"),
                    profile_data.get("resting_hr"),
                    profile_data.get("max_hr_measured"),
                    profile_data.get("lactate_threshold_hr"),
                    profile_data.get("ftp_watts"),
                    json.dumps(profile_data, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_user_profile(self) -> Optional[Dict]:
        """获取用户档案"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profile WHERE id = 1")
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 计算年龄
                if result.get("birth_date"):
                    try:
                        birth = datetime.strptime(result["birth_date"], "%Y-%m-%d")
                        today = datetime.now()
                        age = today.year - birth.year
                        if (today.month, today.day) < (birth.month, birth.day):
                            age -= 1
                        result["age"] = age
                        # 估算最大心率（如果没有实测值）
                        if not result.get("max_hr_measured"):
                            result["max_hr_estimated"] = 220 - age
                    except ValueError:
                        pass
                return result
            return None

    def save_weight_record(self, date: str, data: Dict) -> None:
        """
        保存体重记录

        Args:
            date: 日期 (YYYY-MM-DD)
            data: 体重数据
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO weight_history (
                    date, weight_kg, bmi, body_fat_percent, muscle_mass_kg,
                    bone_mass_kg, body_water_percent, data_json, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    date,
                    data.get("weight_kg") or data.get("weight"),
                    data.get("bmi"),
                    data.get("body_fat_percent") or data.get("bodyFat"),
                    data.get("muscle_mass_kg") or data.get("muscleMass"),
                    data.get("bone_mass_kg") or data.get("boneMass"),
                    data.get("body_water_percent") or data.get("bodyWater"),
                    json.dumps(data, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_weight_history(self, limit: int = 30) -> List[Dict]:
        """获取体重历史记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM weight_history
                ORDER BY date DESC
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_weight(self) -> Optional[Dict]:
        """获取最新的体重记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM weight_history
                ORDER BY date DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== 统计和工具方法 ====================

    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 活动统计
            cursor.execute("SELECT COUNT(*) as count FROM activities")
            activities_count = cursor.fetchone()["count"]

            cursor.execute("SELECT MIN(date) as min, MAX(date) as max FROM activities")
            activities_range = cursor.fetchone()

            # 每日指标统计
            cursor.execute("SELECT COUNT(*) as count FROM daily_metrics")
            metrics_count = cursor.fetchone()["count"]

            cursor.execute("SELECT DISTINCT metric_type FROM daily_metrics")
            metric_types = [row["metric_type"] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT MIN(date) as min, MAX(date) as max FROM daily_metrics"
            )
            metrics_range = cursor.fetchone()

            # 分段统计
            cursor.execute("SELECT COUNT(*) as count FROM activity_laps")
            laps_count = cursor.fetchone()["count"]

            # 数据库文件大小
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            return {
                "activities": {
                    "count": activities_count,
                    "date_range": {
                        "min": activities_range["min"],
                        "max": activities_range["max"],
                    },
                },
                "daily_metrics": {
                    "count": metrics_count,
                    "types": metric_types,
                    "date_range": {
                        "min": metrics_range["min"],
                        "max": metrics_range["max"],
                    },
                },
                "activity_laps": {"count": laps_count},
                "database": {
                    "path": str(self.db_path),
                    "size_mb": round(db_size / 1024 / 1024, 2),
                },
            }

    def print_stats(self):
        """打印数据库统计摘要"""
        stats = self.get_stats()

        print("\n📊 Garmin 数据库统计")
        print("=" * 50)

        print(f"\n🏃 活动数据:")
        print(f"   总计: {stats['activities']['count']} 条")
        if stats["activities"]["date_range"]["min"]:
            print(
                f"   日期范围: {stats['activities']['date_range']['min']} ~ {stats['activities']['date_range']['max']}"
            )
        print(f"   分段记录: {stats['activity_laps']['count']} 条")

        print(f"\n💓 每日健康指标:")
        print(f"   总计: {stats['daily_metrics']['count']} 条")
        if stats["daily_metrics"]["types"]:
            print(f"   类型: {', '.join(stats['daily_metrics']['types'])}")
        if stats["daily_metrics"]["date_range"]["min"]:
            print(
                f"   日期范围: {stats['daily_metrics']['date_range']['min']} ~ {stats['daily_metrics']['date_range']['max']}"
            )

        print(f"\n💾 数据库:")
        print(f"   路径: {stats['database']['path']}")
        print(f"   大小: {stats['database']['size_mb']} MB")

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """
        执行自定义 SQL 查询

        Args:
            query: SQL 查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


# 便捷函数
def get_database() -> GarminDatabase:
    """获取默认数据库实例"""
    return GarminDatabase()


if __name__ == "__main__":
    # 测试数据库初始化
    print("🔧 初始化 Garmin 数据库...")
    db = GarminDatabase()
    db.print_stats()
    print("\n✅ 数据库初始化成功!")
