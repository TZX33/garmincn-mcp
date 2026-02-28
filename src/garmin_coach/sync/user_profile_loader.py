#!/usr/bin/env python3
"""
用户档案加载器

从 SQLite 数据库加载用户档案，并计算派生字段（年龄、心率区间等）。

使用方法：
    from user_profile_loader import load_user_profile

    profile = load_user_profile()
    print(f"年龄: {profile['age']}")
    print(f"最大心率: {profile['max_hr']}")
"""

from datetime import datetime
from typing import Dict, Optional

from garmin_coach.db.garmin_db import GarminDatabase


def load_user_profile() -> Dict:
    """
    加载用户档案

    Returns:
        用户档案字典，包含：
        - display_name: 显示名称
        - gender: 性别
        - birth_date: 出生日期
        - age: 年龄（计算得出）
        - height_cm: 身高（厘米）
        - weight_kg: 体重（千克）
        - resting_hr: 静息心率
        - max_hr: 最大心率（实测或估算）
        - lactate_threshold_hr: 乳酸阈心率
        - hr_zones: 心率区间
        - source: 数据来源 ('database', 'default')
    """
    profile = None
    source = "default"
    db = None

    # 尝试从数据库加载用户档案
    try:
        db = GarminDatabase()
        profile = db.get_user_profile()
        if profile:
            source = "database"
    except Exception as e:
        print(f"⚠️ 从数据库加载档案失败: {e}")

    # 如果没有用户档案，使用默认值
    if profile is None:
        profile = _get_default_profile()
        source = "default"

    # 如果没有静息心率，尝试从睡眠数据中提取
    if not profile.get("resting_hr") and db:
        resting_hr = _get_resting_hr_from_sleep(db)
        if resting_hr:
            profile["resting_hr"] = resting_hr
            profile["resting_hr_source"] = "sleep_data"

    # 确保必要的计算字段存在
    profile = _enrich_profile(profile)
    profile["source"] = source

    return profile


def _get_resting_hr_from_sleep(db: GarminDatabase, days: int = 7) -> Optional[int]:
    """
    从最近的睡眠数据中提取静息心率平均值

    Args:
        db: 数据库实例
        days: 回溯天数

    Returns:
        平均静息心率，如果没有数据则返回 None
    """
    from datetime import timedelta

    today = datetime.now()
    resting_hrs = []

    for i in range(days):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            sleep_data = db.get_daily_metric(date_str, "sleep")
            if sleep_data and sleep_data.get("restingHeartRate"):
                resting_hrs.append(sleep_data["restingHeartRate"])
        except Exception:
            pass

    if resting_hrs:
        return int(sum(resting_hrs) / len(resting_hrs))
    return None


def _get_default_profile() -> Dict:
    """返回默认档案（用于无数据时）"""
    return {
        "display_name": "Runner",
        "gender": None,
        "birth_date": None,
        "height_cm": None,
        "weight_kg": None,
        "resting_hr": 60,  # 默认静息心率
        "max_hr_measured": None,
        "lactate_threshold_hr": None,
        "ftp_watts": None,
    }


def _enrich_profile(profile: Dict) -> Dict:
    """
    丰富档案数据，添加计算字段
    """
    result = dict(profile)

    # 计算年龄
    if result.get("birth_date") and not result.get("age"):
        try:
            birth = datetime.strptime(result["birth_date"], "%Y-%m-%d")
            today = datetime.now()
            age = today.year - birth.year
            if (today.month, today.day) < (birth.month, birth.day):
                age -= 1
            result["age"] = age
        except ValueError:
            pass

    # 确定最大心率
    if result.get("max_hr_measured"):
        result["max_hr"] = result["max_hr_measured"]
        result["max_hr_source"] = "measured"
    elif result.get("age"):
        # 使用 Tanaka 公式: 208 - 0.7 * age (比 220-age 更准确)
        result["max_hr"] = int(208 - 0.7 * result["age"])
        result["max_hr_source"] = "estimated (Tanaka)"
    else:
        # 无年龄数据时的默认值
        result["max_hr"] = 190
        result["max_hr_source"] = "default"

    # 估算乳酸阈心率（如果没有实测值）
    if not result.get("lactate_threshold_hr") and result.get("max_hr"):
        # 通常 LTHR ≈ 85-90% 最大心率
        result["lactate_threshold_hr_estimated"] = int(result["max_hr"] * 0.87)

    # 计算心率区间
    if result.get("max_hr"):
        resting = result.get("resting_hr")
        if resting:
            # 使用 Karvonen 公式（更精确）
            result["hr_zones"] = _calculate_hr_zones_karvonen(result["max_hr"], resting)
            result["hr_zone_method"] = "Karvonen"
        else:
            # 使用简单的最大心率百分比方法
            result["hr_zones"] = _calculate_hr_zones_percentage(result["max_hr"])
            result["hr_zone_method"] = "MaxHR%"

    return result


def _calculate_hr_zones_karvonen(max_hr: int, resting_hr: int) -> Dict:
    """
    使用 Karvonen 公式计算心率区间（更精确）

    Zone = resting_hr + (max_hr - resting_hr) * percentage
    """
    hrr = max_hr - resting_hr  # Heart Rate Reserve

    zones = {
        "zone1": {
            "name": "Recovery",
            "min": resting_hr + int(hrr * 0.50),
            "max": resting_hr + int(hrr * 0.60),
            "description": "恢复区，轻松有氧",
        },
        "zone2": {
            "name": "Aerobic",
            "min": resting_hr + int(hrr * 0.60),
            "max": resting_hr + int(hrr * 0.70),
            "description": "有氧区，长距离训练",
        },
        "zone3": {
            "name": "Tempo",
            "min": resting_hr + int(hrr * 0.70),
            "max": resting_hr + int(hrr * 0.80),
            "description": "节奏区，马拉松配速",
        },
        "zone4": {
            "name": "Threshold",
            "min": resting_hr + int(hrr * 0.80),
            "max": resting_hr + int(hrr * 0.90),
            "description": "阈值区，乳酸阈训练",
        },
        "zone5": {
            "name": "VO2max",
            "min": resting_hr + int(hrr * 0.90),
            "max": max_hr,
            "description": "最大摄氧量区，间歇训练",
        },
    }

    return zones


def _calculate_hr_zones_percentage(max_hr: int) -> Dict:
    """
    使用最大心率百分比计算心率区间（简单方法，没有静息心率时使用）
    """
    zones = {
        "zone1": {
            "name": "Recovery",
            "min": int(max_hr * 0.50),
            "max": int(max_hr * 0.60),
            "description": "恢复区，轻松有氧",
        },
        "zone2": {
            "name": "Aerobic",
            "min": int(max_hr * 0.60),
            "max": int(max_hr * 0.70),
            "description": "有氧区，长距离训练",
        },
        "zone3": {
            "name": "Tempo",
            "min": int(max_hr * 0.70),
            "max": int(max_hr * 0.80),
            "description": "节奏区，马拉松配速",
        },
        "zone4": {
            "name": "Threshold",
            "min": int(max_hr * 0.80),
            "max": int(max_hr * 0.90),
            "description": "阈值区，乳酸阈训练",
        },
        "zone5": {
            "name": "VO2max",
            "min": int(max_hr * 0.90),
            "max": max_hr,
            "description": "最大摄氧量区，间歇训练",
        },
    }

    return zones


def print_profile(profile: Dict = None) -> None:
    """打印用户档案摘要"""
    if profile is None:
        profile = load_user_profile()

    print("\n" + "=" * 50)
    print("👤 用户档案")
    print("=" * 50)

    print(f"\n📋 基本信息:")
    print(f"   名称: {profile.get('display_name', 'N/A')}")
    print(f"   性别: {profile.get('gender', 'N/A')}")
    print(f"   年龄: {profile.get('age', 'N/A')}")
    print(f"   身高: {profile.get('height_cm', 'N/A')} cm")
    print(f"   体重: {profile.get('weight_kg', 'N/A')} kg")

    print(f"\n❤️ 心率设置:")
    resting_hr = profile.get("resting_hr", "N/A")
    resting_hr_source = profile.get("resting_hr_source", "")
    if resting_hr_source:
        print(f"   静息心率: {resting_hr} bpm ({resting_hr_source})")
    else:
        print(f"   静息心率: {resting_hr} bpm")
    print(
        f"   最大心率: {profile.get('max_hr', 'N/A')} bpm ({profile.get('max_hr_source', 'N/A')})"
    )
    if profile.get("lactate_threshold_hr"):
        print(f"   乳酸阈心率: {profile.get('lactate_threshold_hr')} bpm")
    elif profile.get("lactate_threshold_hr_estimated"):
        print(
            f"   乳酸阈心率: ~{profile.get('lactate_threshold_hr_estimated')} bpm (估算)"
        )

    if profile.get("hr_zones"):
        method = profile.get("hr_zone_method", "Unknown")
        print(f"\n📊 心率区间 ({method}):")
        for zone_key, zone in profile["hr_zones"].items():
            print(
                f"   {zone_key.upper()}: {zone['min']}-{zone['max']} bpm ({zone['name']})"
            )

    print(f"\n📡 数据来源: {profile.get('source', 'N/A')}")


if __name__ == "__main__":
    profile = load_user_profile()
    print_profile(profile)
