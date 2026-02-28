"""
Garmin 本地数据库查询工具 (MCP Server 集成)

提供基于本地 SQLite 数据库的查询功能，无需每次调用 API。
"""

from fastmcp import FastMCP
import logging

from garmin_coach.db.garmin_db import GarminDatabase

logger = logging.getLogger(__name__)
mcp = FastMCP("garmincn-mcp-local")

# 全局数据库实例
_db = None


def get_db() -> GarminDatabase:
    """获取数据库实例（延迟初始化）"""
    global _db
    if _db is None:
        _db = GarminDatabase()
    return _db


# ==================== 活动查询 ====================


@mcp.tool()
def query_recent_activities(limit: int = 20) -> dict:
    """
    查询最近的活动列表（从本地数据库）

    Args:
        limit: 返回的最大数量，默认20

    Returns:
        活动列表，包含日期、类型、距离、时长等基础信息
    """
    try:
        db = get_db()
        activities = db.get_recent_activities(limit)

        # 格式化输出
        result = []
        for act in activities:
            result.append(
                {
                    "activity_id": act["activity_id"],
                    "date": act["date"],
                    "type": act["activity_type"],
                    "name": act["activity_name"],
                    "distance_km": round(act["distance"] / 1000, 2)
                    if act["distance"]
                    else None,
                    "duration_min": round(act["duration"] / 60, 1)
                    if act["duration"]
                    else None,
                    "avg_hr": act["average_hr"],
                    "calories": act["calories"],
                }
            )

        return {"status": "success", "count": len(result), "data": result}
    except Exception as e:
        logger.error(f"查询活动失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def query_running_activities(limit: int = 20) -> dict:
    """
    查询最近的跑步活动（从本地数据库）

    Args:
        limit: 返回的最大数量，默认20

    Returns:
        跑步活动列表，包含配速、步频、功率等专业指标
    """
    try:
        db = get_db()
        activities = db.get_activities_by_type("running", limit)

        result = []
        for act in activities:
            # 计算配速 (分钟/公里)
            pace_min_per_km = None
            if act["average_speed"] and act["average_speed"] > 0:
                pace_sec = 1000 / act["average_speed"]
                pace_min_per_km = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"

            result.append(
                {
                    "activity_id": act["activity_id"],
                    "date": act["date"],
                    "name": act["activity_name"],
                    "distance_km": round(act["distance"] / 1000, 2)
                    if act["distance"]
                    else None,
                    "duration_min": round(act["duration"] / 60, 1)
                    if act["duration"]
                    else None,
                    "pace_per_km": pace_min_per_km,
                    "avg_hr": act["average_hr"],
                    "max_hr": act["max_hr"],
                    "avg_power": act["average_power"],
                    "avg_cadence": act["average_cadence"],
                    "stride_length_cm": round(act["stride_length"], 1)
                    if act["stride_length"]
                    else None,
                    "vertical_oscillation_cm": round(act["vertical_oscillation"], 1)
                    if act["vertical_oscillation"]
                    else None,
                    "ground_contact_time_ms": round(act["ground_contact_time"], 0)
                    if act["ground_contact_time"]
                    else None,
                    "training_effect": act["training_effect"],
                    "elevation_gain_m": act["elevation_gain"],
                }
            )

        return {"status": "success", "count": len(result), "data": result}
    except Exception as e:
        logger.error(f"查询跑步活动失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def query_activity_details(activity_id: int) -> dict:
    """
    查询单个活动的详细信息（从本地数据库）

    Args:
        activity_id: 活动ID

    Returns:
        活动详情，包含汇总数据、分段数据、心率区间等
    """
    try:
        db = get_db()

        # 获取活动基础信息
        activity = db.get_activity(activity_id)
        if not activity:
            return {
                "status": "error",
                "message": f"活动 {activity_id} 不存在",
                "data": None,
            }

        # 获取分段数据
        laps = db.get_activity_laps(activity_id)

        # 获取心率区间
        hr_zones = db.get_activity_hr_zones(activity_id)

        # 格式化分段数据
        formatted_laps = []
        for lap in laps:
            pace_min_per_km = None
            if lap["average_speed"] and lap["average_speed"] > 0:
                pace_sec = 1000 / lap["average_speed"]
                pace_min_per_km = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"

            formatted_laps.append(
                {
                    "lap": lap["lap_index"],
                    "distance_m": lap["distance"],
                    "duration_sec": lap["duration"],
                    "pace": pace_min_per_km,
                    "avg_hr": lap["average_hr"],
                    "max_hr": lap["max_hr"],
                    "avg_power": lap["average_power"],
                    "cadence": lap["average_cadence"],
                    "elevation_gain": lap["elevation_gain"],
                }
            )

        # 格式化心率区间
        formatted_zones = []
        for zone in hr_zones:
            formatted_zones.append(
                {
                    "zone": zone["zone_number"],
                    "seconds": zone["secs_in_zone"],
                    "minutes": round(zone["secs_in_zone"] / 60, 1)
                    if zone["secs_in_zone"]
                    else 0,
                    "threshold_bpm": zone["zone_low_boundary"],
                }
            )

        return {
            "status": "success",
            "data": {
                "activity_id": activity["activity_id"],
                "date": activity["date"],
                "type": activity["activity_type"],
                "name": activity["activity_name"],
                "summary": {
                    "distance_km": round(activity["distance"] / 1000, 2)
                    if activity["distance"]
                    else None,
                    "duration_min": round(activity["duration"] / 60, 1)
                    if activity["duration"]
                    else None,
                    "avg_hr": activity["average_hr"],
                    "max_hr": activity["max_hr"],
                    "avg_power": activity["average_power"],
                    "avg_cadence": activity["average_cadence"],
                    "stride_length": activity["stride_length"],
                    "vertical_oscillation": activity["vertical_oscillation"],
                    "ground_contact_time": activity["ground_contact_time"],
                    "elevation_gain": activity["elevation_gain"],
                    "training_effect": activity["training_effect"],
                    "calories": activity["calories"],
                },
                "laps": formatted_laps,
                "hr_zones": formatted_zones,
            },
        }
    except Exception as e:
        logger.error(f"查询活动详情失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


# ==================== 每日指标查询 ====================


@mcp.tool()
def query_daily_metrics(date: str, metric_type: str = None) -> dict:
    """
    查询指定日期的健康指标（从本地数据库）

    Args:
        date: 日期 (YYYY-MM-DD)
        metric_type: 可选，指标类型。支持: sleep, heart_rates, stress, hrv,
                     body_battery, spo2, steps, training_readiness 等

    Returns:
        健康指标数据
    """
    try:
        db = get_db()

        if metric_type:
            data = db.get_daily_metric(date, metric_type)
            if data:
                return {
                    "status": "success",
                    "date": date,
                    "type": metric_type,
                    "data": data,
                }
            else:
                return {
                    "status": "error",
                    "message": f"{date} 没有 {metric_type} 数据",
                    "data": None,
                }
        else:
            # 获取所有类型
            metrics = db.get_daily_metrics_range(date, date)
            return {
                "status": "success",
                "date": date,
                "count": len(metrics),
                "data": {m["metric_type"]: m["data"] for m in metrics},
            }
    except Exception as e:
        logger.error(f"查询每日指标失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def query_sleep_trend(days: int = 7) -> dict:
    """
    查询最近N天的睡眠趋势（从本地数据库）

    Args:
        days: 天数，默认7天

    Returns:
        睡眠趋势数据，包含每天的睡眠时长、评分等
    """
    try:
        from datetime import datetime, timedelta

        db = get_db()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        metrics = db.get_daily_metrics_range(start_date, end_date, "sleep")

        result = []
        for m in metrics:
            sleep_data = m["data"]
            if sleep_data:
                # 提取关键睡眠指标
                daily_sleep = sleep_data.get("dailySleepDTO", {})
                result.append(
                    {
                        "date": m["date"],
                        "sleep_time_hours": round(
                            daily_sleep.get("sleepTimeSeconds", 0) / 3600, 1
                        ),
                        "deep_sleep_hours": round(
                            daily_sleep.get("deepSleepSeconds", 0) / 3600, 2
                        ),
                        "light_sleep_hours": round(
                            daily_sleep.get("lightSleepSeconds", 0) / 3600, 2
                        ),
                        "rem_sleep_hours": round(
                            daily_sleep.get("remSleepSeconds", 0) / 3600, 2
                        ),
                        "awake_hours": round(
                            daily_sleep.get("awakeSleepSeconds", 0) / 3600, 2
                        ),
                        "sleep_score": daily_sleep.get("sleepScores", {})
                        .get("overall", {})
                        .get("value"),
                        "avg_stress": daily_sleep.get("avgSleepStress"),
                    }
                )

        # 计算平均值
        if result:
            avg_sleep = sum(r["sleep_time_hours"] for r in result) / len(result)
            avg_score = (
                sum(r["sleep_score"] or 0 for r in result if r["sleep_score"])
                / len([r for r in result if r["sleep_score"]])
                if any(r["sleep_score"] for r in result)
                else None
            )
        else:
            avg_sleep = None
            avg_score = None

        return {
            "status": "success",
            "period": f"{start_date} ~ {end_date}",
            "days": len(result),
            "average_sleep_hours": round(avg_sleep, 1) if avg_sleep else None,
            "average_score": round(avg_score, 0) if avg_score else None,
            "data": result,
        }
    except Exception as e:
        logger.error(f"查询睡眠趋势失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def query_hr_trend(days: int = 7) -> dict:
    """
    查询最近N天的心率趋势（从本地数据库）

    Args:
        days: 天数，默认7天

    Returns:
        心率趋势数据，包含每天的静息心率、最大心率等
    """
    try:
        from datetime import datetime, timedelta

        db = get_db()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        metrics = db.get_daily_metrics_range(start_date, end_date, "heart_rates")

        result = []
        for m in metrics:
            hr_data = m["data"]
            if hr_data:
                result.append(
                    {
                        "date": m["date"],
                        "resting_hr": hr_data.get("restingHeartRate"),
                        "min_hr": hr_data.get("minHeartRate"),
                        "max_hr": hr_data.get("maxHeartRate"),
                        "avg_hr": hr_data.get("averageHeartRate")
                        or hr_data.get("lastSevenDaysAvgRestingHeartRate"),
                    }
                )

        return {
            "status": "success",
            "period": f"{start_date} ~ {end_date}",
            "days": len(result),
            "data": result,
        }
    except Exception as e:
        logger.error(f"查询心率趋势失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


# ==================== 数据库统计 ====================


@mcp.tool()
def query_database_stats() -> dict:
    """
    查询本地数据库统计信息

    Returns:
        数据库中的活动数量、指标数量、日期范围等
    """
    try:
        db = get_db()
        stats = db.get_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        logger.error(f"查询数据库统计失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def execute_custom_query(query: str) -> dict:
    """
    执行自定义 SQL 查询（只读）

    Args:
        query: SQL 查询语句（只支持 SELECT）

    Returns:
        查询结果
    """
    try:
        # 安全检查：只允许 SELECT
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return {"status": "error", "message": "只支持 SELECT 查询", "data": None}

        # 禁止某些危险关键词
        dangerous = [
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "ALTER",
            "CREATE",
            "TRUNCATE",
        ]
        for kw in dangerous:
            if kw in query_upper:
                return {"status": "error", "message": f"不允许使用 {kw}", "data": None}

        db = get_db()
        result = db.execute_query(query)

        return {"status": "success", "count": len(result), "data": result}
    except Exception as e:
        logger.error(f"执行查询失败: {e}")
        return {"status": "error", "message": str(e), "data": None}


# 导出工具
__all__ = [
    "query_recent_activities",
    "query_running_activities",
    "query_activity_details",
    "query_daily_metrics",
    "query_sleep_trend",
    "query_hr_trend",
    "query_database_stats",
    "execute_custom_query",
]
