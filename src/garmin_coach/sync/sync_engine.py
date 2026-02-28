#!/usr/bin/env python3
"""
Garmin 数据同步引擎

将 Garmin Connect API 数据同步到本地 SQLite 数据库。

支持的同步模式：
- 全量同步：同步所有历史数据
- 增量同步：只同步新数据和最近N天的数据
- 指定范围同步：同步特定日期范围

使用方法：
    # 增量同步（推荐日常使用）
    uv run python sync_engine.py

    # 全量同步（首次使用）
    uv run python sync_engine.py --full

    # 指定日期范围
    uv run python sync_engine.py --from 2026-01-01 --to 2026-01-31

    # 强制刷新特定日期
    uv run python sync_engine.py --force-refresh --date 2026-02-05
"""

import sys
import os
import argparse
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from garmin_coach.api.garmin_client import GarminService
from garmin_coach.db.garmin_db import GarminDatabase


class SyncEngine:
    """Garmin 数据同步引擎"""

    # 成熟窗口：最近N天的数据需要刷新（可能有更新）
    MATURITY_WINDOW_DAYS = 2

    # 每日健康指标类型
    # 注意：部分 API (steps, floors, resting_hr, user_summary, intensity_minutes)
    # 在某些情况下会返回 403 错误，已暂时移除
    DAILY_METRIC_TYPES = [
        ("sleep", "get_sleep_data"),
        ("heart_rates", "get_heart_rates"),
        ("stress", "get_stress_data"),
        ("hrv", "get_hrv_data"),
        ("body_battery", "get_body_battery"),
        ("respiration", "get_respiration_data"),
        ("spo2", "get_spo2_data"),
        ("training_readiness", "get_training_readiness"),
        ("training_status", "get_training_status"),
        ("max_metrics", "get_max_metrics"),
    ]

    # API 调用间隔（秒），避免 Rate Limit
    API_DELAY = 0.3

    def __init__(self, verbose: bool = True):
        """
        初始化同步引擎

        Args:
            verbose: 是否打印详细日志
        """
        self.verbose = verbose
        self.db = GarminDatabase()
        self.api = None

        # 统计
        self.stats = {
            "activities_synced": 0,
            "activities_skipped": 0,
            "laps_synced": 0,
            "hr_zones_synced": 0,
            "daily_metrics_synced": 0,
            "daily_metrics_skipped": 0,
            "profile_synced": False,
            "weight_records_synced": 0,
            "api_calls": 0,
            "errors": [],
        }

    def _log(self, message: str, level: str = "INFO"):
        """打印日志"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {
                "INFO": "ℹ️",
                "SUCCESS": "✅",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "PROGRESS": "🔄",
            }.get(level, "  ")
            print(f"[{timestamp}] {prefix} {message}")

    def _api_call(self, method_name: str, *args, **kwargs):
        """
        封装 API 调用，添加延迟和错误处理
        """
        self.stats["api_calls"] += 1
        time.sleep(self.API_DELAY)

        method = getattr(self.api, method_name)
        return method(*args, **kwargs)

    def init_api(self) -> bool:
        """初始化 Garmin API 连接"""
        self._log("正在连接 Garmin API...", "PROGRESS")

        garmin_service = GarminService()
        if not garmin_service.init_api():
            self._log("Garmin API 连接失败", "ERROR")
            return False

        self.api = garmin_service.garminapi
        self._log("Garmin API 连接成功", "SUCCESS")
        return True

    def _is_data_mature(self, date_str: str) -> bool:
        """
        判断指定日期的数据是否已经"成熟"（不再需要刷新）
        """
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            days_ago = (today - date).days
            return days_ago >= self.MATURITY_WINDOW_DAYS
        except ValueError:
            return True

    # ==================== 活动数据同步 ====================

    def sync_activities(self, limit: int = 100, force_refresh: bool = False) -> int:
        """
        同步活动数据

        Args:
            limit: 获取的最大活动数量
            force_refresh: 是否强制刷新已存在的活动

        Returns:
            同步的活动数量
        """
        self._log(
            f"开始同步活动数据 (limit={limit}, force={force_refresh})...", "PROGRESS"
        )

        try:
            activities = self._api_call("get_activities", 0, limit)
        except Exception as e:
            self._log(f"获取活动列表失败: {e}", "ERROR")
            self.stats["errors"].append(f"get_activities: {e}")
            return 0

        synced = 0
        for i, activity in enumerate(activities):
            activity_id = activity.get("activityId")
            activity_name = activity.get("activityName", "Unknown")
            activity_date = activity.get("startTimeLocal", "")[:10]

            # 检查是否需要同步
            if not force_refresh and self.db.activity_exists(activity_id):
                self.stats["activities_skipped"] += 1
                continue

            self._log(
                f"[{i + 1}/{len(activities)}] 同步活动: {activity_date} - {activity_name}",
                "PROGRESS",
            )

            try:
                # 获取完整活动数据
                full_activity = self._api_call("get_activity", activity_id)
                summary_data = (
                    full_activity.get("summaryDTO", {}) if full_activity else {}
                )
                metadata_data = (
                    full_activity.get("metadataDTO", {}) if full_activity else {}
                )

                # 保存活动
                self.db.save_activity(
                    activity_data=activity,
                    summary_data=summary_data,
                    metadata_data=metadata_data,
                    full_data=full_activity,
                )

                # 获取并保存分段数据
                try:
                    splits = self._api_call("get_activity_splits", activity_id)
                    if splits and "lapDTOs" in splits:
                        self.db.save_activity_laps(activity_id, splits["lapDTOs"])
                        self.stats["laps_synced"] += len(splits["lapDTOs"])
                except Exception as e:
                    self._log(f"获取分段数据失败: {e}", "WARNING")

                # 获取并保存心率区间
                try:
                    hr_zones = self._api_call(
                        "get_activity_hr_in_timezones", activity_id
                    )
                    if hr_zones:
                        self.db.save_activity_hr_zones(activity_id, hr_zones)
                        self.stats["hr_zones_synced"] += len(hr_zones)
                except Exception as e:
                    self._log(f"获取心率区间失败: {e}", "WARNING")

                synced += 1
                self.stats["activities_synced"] += 1

            except Exception as e:
                self._log(f"同步活动 {activity_id} 失败: {e}", "ERROR")
                self.stats["errors"].append(f"Activity {activity_id}: {e}")

        self._log(
            f"活动同步完成: {synced} 个新同步, {self.stats['activities_skipped']} 个已存在",
            "SUCCESS",
        )
        return synced

    # ==================== 每日健康指标同步 ====================

    def sync_daily_metrics(
        self,
        start_date: str,
        end_date: str = None,
        force_refresh: bool = False,
        metric_types: List[str] = None,
    ) -> int:
        """
        同步每日健康指标

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期，默认为今天
            force_refresh: 是否强制刷新
            metric_types: 要同步的指标类型列表，默认全部

        Returns:
            同步的指标数量
        """
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        self._log(f"开始同步每日健康指标 ({start_date} ~ {end_date})...", "PROGRESS")

        # 生成日期列表
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        # 确定要同步的指标类型
        types_to_sync = self.DAILY_METRIC_TYPES
        if metric_types:
            types_to_sync = [
                (t, m) for t, m in self.DAILY_METRIC_TYPES if t in metric_types
            ]

        synced = 0
        total = len(dates) * len(types_to_sync)
        current_item = 0

        for date_str in dates:
            is_mature = self._is_data_mature(date_str)

            for metric_type, api_method in types_to_sync:
                current_item += 1

                # 检查是否需要同步
                should_sync = (
                    force_refresh
                    or not is_mature
                    or not self.db.daily_metric_exists(date_str, metric_type)
                )

                if not should_sync:
                    self.stats["daily_metrics_skipped"] += 1
                    continue

                try:
                    # 调用 API 获取数据
                    method = getattr(self.api, api_method)
                    self.stats["api_calls"] += 1
                    time.sleep(self.API_DELAY)
                    data = method(date_str)

                    if data:
                        self.db.save_daily_metric(date_str, metric_type, data)
                        synced += 1
                        self.stats["daily_metrics_synced"] += 1

                except Exception as e:
                    # 某些日期可能没有数据，不算错误
                    if "404" not in str(e) and "Not Found" not in str(e):
                        self._log(f"{date_str}/{metric_type}: {e}", "WARNING")

                # 每 50 个打印一次进度
                if current_item % 50 == 0:
                    self._log(
                        f"进度: {current_item}/{total} ({current_item * 100 // total}%)",
                        "PROGRESS",
                    )

        self._log(
            f"每日指标同步完成: {synced} 个新同步, {self.stats['daily_metrics_skipped']} 个已存在",
            "SUCCESS",
        )
        return synced

    # ==================== 用户档案同步 ====================

    def sync_user_profile(self) -> bool:
        """
        同步用户档案（身高、体重、年龄等）

        Returns:
            是否成功同步
        """
        self._log("开始同步用户档案...", "PROGRESS")

        try:
            profile_data = {}

            # 优先使用 get_user_profile，因为它包含完整的 userData
            try:
                user_profile = self._api_call("get_user_profile")
                if user_profile:
                    # 从 userData 字段提取详细信息
                    user_data = user_profile.get("userData", {})

                    # 基本信息
                    profile_data["gender"] = (
                        user_data.get("gender", "").lower()
                        if user_data.get("gender")
                        else None
                    )
                    profile_data["birth_date"] = user_data.get("birthDate")
                    profile_data["height_cm"] = user_data.get("height")
                    # Garmin 存储体重为克，需要转换为千克
                    weight_grams = user_data.get("weight")
                    if weight_grams:
                        profile_data["weight_kg"] = weight_grams / 1000

                    # 心率和功率设置
                    if user_data.get("restingHeartRate"):
                        profile_data["resting_hr"] = user_data.get("restingHeartRate")
                    if user_data.get("lactateThresholdHeartRate"):
                        profile_data["lactate_threshold_hr"] = user_data.get(
                            "lactateThresholdHeartRate"
                        )
                    if user_data.get("vo2MaxRunning"):
                        profile_data["vo2max"] = user_data.get("vo2MaxRunning")

                    self._log(f"从 get_user_profile 获取到用户数据", "INFO")

            except Exception as e:
                self._log(f"get_user_profile 失败: {e}", "WARNING")

            # 尝试从 get_userprofile_settings 获取显示名称
            try:
                user_settings = self._api_call("get_userprofile_settings")
                if user_settings:
                    display_name = user_settings.get("displayName")
                    if display_name and display_name != profile_data.get(
                        "display_name"
                    ):
                        profile_data["display_name"] = display_name
            except Exception as e:
                self._log(f"get_userprofile_settings 失败: {e}", "WARNING")

            # 如果有数据，保存到数据库
            if profile_data:
                # 输出关键信息
                self._log(f"  性别: {profile_data.get('gender', 'N/A')}", "INFO")
                self._log(
                    f"  出生日期: {profile_data.get('birth_date', 'N/A')}", "INFO"
                )
                self._log(f"  身高: {profile_data.get('height_cm', 'N/A')} cm", "INFO")
                self._log(f"  体重: {profile_data.get('weight_kg', 'N/A')} kg", "INFO")
                self._log(
                    f"  乳酸阈心率: {profile_data.get('lactate_threshold_hr', 'N/A')} bpm",
                    "INFO",
                )

                self.db.save_user_profile(profile_data)
                self.stats["profile_synced"] = True
                self._log(f"用户档案同步成功", "SUCCESS")
                return True
            else:
                self._log("没有获取到用户档案数据", "WARNING")
                return False

        except Exception as e:
            self._log(f"同步用户档案失败: {e}", "ERROR")
            self.stats["errors"].append(f"User profile: {e}")
            return False

    def sync_weight_history(self, days_back: int = 30) -> int:
        """
        同步体重历史记录

        Args:
            days_back: 回溯天数

        Returns:
            同步的记录数
        """
        self._log(f"开始同步体重历史 (最近 {days_back} 天)...", "PROGRESS")

        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )

            # 尝试获取体重记录
            try:
                weigh_ins = self._api_call("get_weigh_ins", start_date, end_date)
            except Exception:
                # 某些 API 版本使用不同的方法名
                try:
                    weigh_ins = self._api_call("get_body_composition", start_date)
                except Exception as e:
                    self._log(f"获取体重数据失败: {e}", "WARNING")
                    return 0

            if not weigh_ins:
                self._log("没有找到体重记录", "INFO")
                return 0

            synced = 0

            # 处理不同的数据结构
            records = (
                weigh_ins
                if isinstance(weigh_ins, list)
                else weigh_ins.get("dateWeightList", [])
            )

            for record in records:
                try:
                    # 尝试提取日期
                    date_str = record.get("date") or record.get("calendarDate")
                    if not date_str:
                        # 尝试从时间戳提取
                        timestamp = record.get("timestampGMT") or record.get(
                            "sampleDate"
                        )
                        if timestamp:
                            date_str = datetime.fromtimestamp(
                                timestamp / 1000
                            ).strftime("%Y-%m-%d")

                    if date_str:
                        weight_data = {
                            "weight_kg": (
                                record.get("weight") or record.get("weightSum", 0)
                            )
                            / 1000,  # 转换为千克
                            "bmi": record.get("bmi"),
                            "body_fat_percent": record.get("bodyFat")
                            or record.get("bodyFatPercentage"),
                            "muscle_mass_kg": (record.get("muscleMass", 0) or 0) / 1000
                            if record.get("muscleMass")
                            else None,
                            "bone_mass_kg": (record.get("boneMass", 0) or 0) / 1000
                            if record.get("boneMass")
                            else None,
                            "body_water_percent": record.get("bodyWater"),
                        }

                        self.db.save_weight_record(date_str, weight_data)
                        synced += 1

                except Exception as e:
                    self._log(f"处理体重记录失败: {e}", "WARNING")

            self.stats["weight_records_synced"] = synced
            self._log(f"体重历史同步完成: {synced} 条记录", "SUCCESS")
            return synced

        except Exception as e:
            self._log(f"同步体重历史失败: {e}", "ERROR")
            self.stats["errors"].append(f"Weight history: {e}")
            return 0

    # ==================== 同步策略 ====================

    def sync_incremental(self, activity_limit: int = 50, days_back: int = 7):
        """
        增量同步（推荐日常使用）

        只同步：
        - 最近 N 个活动中的新活动
        - 最近 days_back 天的每日指标（强制刷新最近 MATURITY_WINDOW_DAYS 天）
        """
        self._log("=" * 60, "INFO")
        self._log("🔄 开始增量同步", "INFO")
        self._log("=" * 60, "INFO")

        if not self.init_api():
            return False

        sync_id = self.db.log_sync_start("incremental")

        try:
            # 同步用户档案（每次都更新）
            self.sync_user_profile()

            # 同步活动
            self.sync_activities(limit=activity_limit, force_refresh=False)

            # 同步每日指标
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            self.sync_daily_metrics(start_date, end_date, force_refresh=False)

            # 记录同步完成
            self.db.log_sync_complete(
                sync_id,
                self.stats["activities_synced"] + self.stats["daily_metrics_synced"],
                end_date,
            )

            self._print_summary()
            return True

        except Exception as e:
            self._log(f"同步失败: {e}", "ERROR")
            self.db.log_sync_complete(sync_id, 0, error=str(e))
            return False

    def sync_full(self, activity_limit: int = 500, days_back: int = 365):
        """
        全量同步（首次使用或需要完整数据时）

        Args:
            activity_limit: 最大活动数量
            days_back: 回溯天数
        """
        self._log("=" * 60, "INFO")
        self._log("📦 开始全量同步", "INFO")
        self._log(f"   活动数量: 最多 {activity_limit} 个", "INFO")
        self._log(f"   日期范围: 最近 {days_back} 天", "INFO")
        self._log("=" * 60, "INFO")

        if not self.init_api():
            return False

        sync_id = self.db.log_sync_start("full")

        try:
            # 同步用户档案
            self.sync_user_profile()

            # 同步体重历史（全量同步时包含）
            self.sync_weight_history(days_back=days_back)

            # 同步活动
            self.sync_activities(limit=activity_limit, force_refresh=False)

            # 同步每日指标
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            self.sync_daily_metrics(start_date, end_date, force_refresh=False)

            # 记录同步完成
            self.db.log_sync_complete(
                sync_id,
                self.stats["activities_synced"] + self.stats["daily_metrics_synced"],
                end_date,
            )

            self._print_summary()
            return True

        except Exception as e:
            self._log(f"同步失败: {e}", "ERROR")
            self.db.log_sync_complete(sync_id, 0, error=str(e))
            return False

    def sync_date_range(
        self,
        start_date: str,
        end_date: str,
        force_refresh: bool = True,
        include_activities: bool = True,
        include_daily: bool = True,
    ):
        """
        同步指定日期范围的数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            force_refresh: 是否强制刷新
            include_activities: 是否包含活动
            include_daily: 是否包含每日指标
        """
        self._log("=" * 60, "INFO")
        self._log(f"📅 同步日期范围: {start_date} ~ {end_date}", "INFO")
        self._log("=" * 60, "INFO")

        if not self.init_api():
            return False

        sync_id = self.db.log_sync_start("date_range")

        try:
            if include_activities:
                # 获取活动并过滤日期范围
                activities = self._api_call(
                    "get_activities_by_date", start_date, end_date, None
                )
                if activities:
                    for activity in activities:
                        activity_id = activity.get("activityId")
                        if force_refresh or not self.db.activity_exists(activity_id):
                            self._sync_single_activity(activity)

            if include_daily:
                self.sync_daily_metrics(
                    start_date, end_date, force_refresh=force_refresh
                )

            self.db.log_sync_complete(
                sync_id,
                self.stats["activities_synced"] + self.stats["daily_metrics_synced"],
                end_date,
            )

            self._print_summary()
            return True

        except Exception as e:
            self._log(f"同步失败: {e}", "ERROR")
            self.db.log_sync_complete(sync_id, 0, error=str(e))
            return False

    def _sync_single_activity(self, activity: dict):
        """同步单个活动"""
        activity_id = activity.get("activityId")
        activity_name = activity.get("activityName", "Unknown")

        self._log(f"同步活动: {activity_name}", "PROGRESS")

        try:
            full_activity = self._api_call("get_activity", activity_id)
            summary_data = full_activity.get("summaryDTO", {}) if full_activity else {}
            metadata_data = (
                full_activity.get("metadataDTO", {}) if full_activity else {}
            )

            self.db.save_activity(
                activity_data=activity,
                summary_data=summary_data,
                metadata_data=metadata_data,
                full_data=full_activity,
            )

            try:
                splits = self._api_call("get_activity_splits", activity_id)
                if splits and "lapDTOs" in splits:
                    self.db.save_activity_laps(activity_id, splits["lapDTOs"])
                    self.stats["laps_synced"] += len(splits["lapDTOs"])
            except:
                pass

            try:
                hr_zones = self._api_call("get_activity_hr_in_timezones", activity_id)
                if hr_zones:
                    self.db.save_activity_hr_zones(activity_id, hr_zones)
            except:
                pass

            self.stats["activities_synced"] += 1

        except Exception as e:
            self._log(f"同步活动失败: {e}", "ERROR")
            self.stats["errors"].append(f"Activity {activity_id}: {e}")

    def _print_summary(self):
        """打印同步摘要"""
        print("\n" + "=" * 60)
        print("📊 同步摘要")
        print("=" * 60)

        print(f"\n👤 用户档案:")
        print(f"   已同步: {'✅' if self.stats['profile_synced'] else '❌'}")
        if self.stats["weight_records_synced"] > 0:
            print(f"   体重记录: {self.stats['weight_records_synced']} 条")

        print(f"\n🏃 活动:")
        print(f"   新同步: {self.stats['activities_synced']} 个")
        print(f"   已跳过: {self.stats['activities_skipped']} 个")
        print(f"   分段记录: {self.stats['laps_synced']} 条")
        print(f"   心率区间: {self.stats['hr_zones_synced']} 条")

        print(f"\n💓 每日指标:")
        print(f"   新同步: {self.stats['daily_metrics_synced']} 条")
        print(f"   已跳过: {self.stats['daily_metrics_skipped']} 条")

        print(f"\n🌐 API 调用: {self.stats['api_calls']} 次")

        if self.stats["errors"]:
            print(f"\n⚠️ 错误 ({len(self.stats['errors'])} 个):")
            for error in self.stats["errors"][:5]:
                print(f"   - {error}")
            if len(self.stats["errors"]) > 5:
                print(f"   ... 以及 {len(self.stats['errors']) - 5} 个其他错误")

        # 数据库统计
        print("\n💾 数据库状态:")
        self.db.print_stats()


def main():
    parser = argparse.ArgumentParser(
        description="Garmin 数据同步引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  uv run python sync_engine.py                    # 增量同步（日常使用）
  uv run python sync_engine.py --full             # 全量同步（首次使用）
  uv run python sync_engine.py --full --days 90   # 同步最近90天
  uv run python sync_engine.py --from 2026-01-01 --to 2026-01-31
  uv run python sync_engine.py --stats            # 只显示统计信息
        """,
    )

    parser.add_argument(
        "--full", action="store_true", help="全量同步（首次使用时推荐）"
    )
    parser.add_argument(
        "--days", type=int, default=365, help="全量同步时回溯的天数 (默认: 365)"
    )
    parser.add_argument(
        "--activities", type=int, default=500, help="全量同步时最大活动数量 (默认: 500)"
    )
    parser.add_argument(
        "--from", dest="from_date", type=str, help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument("--to", dest="to_date", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument(
        "--force-refresh", action="store_true", help="强制刷新已存在的数据"
    )
    parser.add_argument("--stats", action="store_true", help="只显示数据库统计信息")
    parser.add_argument("--quiet", action="store_true", help="减少输出")

    args = parser.parse_args()

    engine = SyncEngine(verbose=not args.quiet)

    if args.stats:
        # 只显示统计
        engine.db.print_stats()
        return

    if args.from_date:
        # 日期范围同步
        end_date = args.to_date or datetime.now().strftime("%Y-%m-%d")
        engine.sync_date_range(
            args.from_date, end_date, force_refresh=args.force_refresh
        )
    elif args.full:
        # 全量同步
        engine.sync_full(activity_limit=args.activities, days_back=args.days)
    else:
        # 增量同步（默认）
        engine.sync_incremental()


if __name__ == "__main__":
    main()
