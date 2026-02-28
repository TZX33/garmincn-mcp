from garmin_coach.api.garmin_client import GarminService
from fastmcp import FastMCP
import logging

logger = logging.getLogger(__name__)
garmin_service = GarminService()
mcp = FastMCP("garmincn-mcp")


@mcp.tool()
def get_sleep_data(date: str) -> dict:
    """获取指定日期的睡眠数据，日期格式为YYYY-MM-DD"""
    try:
        # 获取睡眠数据
        sleep_data = garmin_service.garminapi.get_sleep_data(date)
        if not sleep_data:
            return {"status": "error", "message": "未获取到睡眠数据", "data": None}
        return {"status": "success", "message": "获取睡眠数据成功", "data": sleep_data}
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取睡眠数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_heart_rate(date: str) -> dict:
    """获取指定日期的心率数据，日期格式为YYYY-MM-DD"""
    try:
        # 获取心率数据
        heart_rate_data = garmin_service.garminapi.get_heart_rates(date)
        if not heart_rate_data:
            return {"status": "error", "message": "未获取到心率数据", "data": None}
        return {
            "status": "success",
            "message": "获取心率数据成功",
            "data": heart_rate_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取心率数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_steps_data(date: str) -> dict:
    """获取指定日期的步数数据，日期格式为YYYY-MM-DD"""
    try:
        # 获取步数数据
        steps_data = garmin_service.garminapi.get_steps_data(date)
        if not steps_data:
            return {"status": "error", "message": "未获取到步数数据", "data": None}
        return {"status": "success", "message": "获取步数数据成功", "data": steps_data}
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取步数数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_body_battery(date: str) -> dict:
    """获取指定日期的身体电量数据，日期格式为YYYY-MM-DD"""
    try:
        # 获取身体电量数据
        body_battery_data = garmin_service.garminapi.get_body_battery(date)
        if not body_battery_data:
            return {"status": "error", "message": "未获取到身体电量数据", "data": None}
        return {
            "status": "success",
            "message": "获取身体电量数据成功",
            "data": body_battery_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取身体电量数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_spo2_data(date: str) -> dict:
    """获取指定日期的血氧饱和度数据，日期格式为YYYY-MM-DD"""
    try:
        # 获取血氧饱和度数据
        # 注意：garminconnect库中获取血氧的方法可能是 get_pulse_ox or get_spo2_data，具体取决于库版本
        # 这里我们先尝试 get_spo2_data，如果不行，可能需要调整
        spo2_data = garmin_service.garminapi.get_spo2_data(date)
        if not spo2_data:
            return {
                "status": "error",
                "message": "未获取到血氧饱和度数据",
                "data": None,
            }
        return {
            "status": "success",
            "message": "获取血氧饱和度数据成功",
            "data": spo2_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取血氧饱和度数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_respiration_data(date: str) -> dict:
    """获取指定日期的呼吸数据，日期格式为YYYY-MM-DD"""
    try:
        # 获取呼吸数据
        respiration_data = garmin_service.garminapi.get_respiration_data(date)
        if not respiration_data:
            return {"status": "error", "message": "未获取到呼吸数据", "data": None}
        return {
            "status": "success",
            "message": "获取呼吸数据成功",
            "data": respiration_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取呼吸数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_activity_data(date: str) -> dict:
    """获取指定日期的活动数据，日期格式为YYYY-MM-DD"""
    try:
        activity_data = garmin_service.garminapi.get_activities_by_date(
            date, date, None
        )  # get_activities_by_date(startdate, enddate, activitytype)
        if not activity_data:
            return {"status": "error", "message": "未获取到活动数据", "data": None}
        return {
            "status": "success",
            "message": "获取活动数据成功",
            "data": activity_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取活动数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_training_readiness_data(date: str) -> dict:
    """获取指定日期的训练准备程度数据，日期格式为YYYY-MM-DD"""
    try:
        training_readiness_data = garmin_service.garminapi.get_training_readiness(date)
        if not training_readiness_data:
            return {
                "status": "error",
                "message": "未获取到训练准备程度数据",
                "data": None,
            }
        return {
            "status": "success",
            "message": "获取训练准备程度数据成功",
            "data": training_readiness_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取训练准备程度数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_floors_data(date: str) -> dict:
    """获取指定日期的楼层数据，日期格式为YYYY-MM-DD"""
    try:
        floors_data = garmin_service.garminapi.get_floors(date)
        if not floors_data:
            return {"status": "error", "message": "未获取到楼层数据", "data": None}
        return {"status": "success", "message": "获取楼层数据成功", "data": floors_data}
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取楼层数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_training_status_data(date: str) -> dict:
    """获取指定日期的训练状态数据，日期格式为YYYY-MM-DD"""
    try:
        training_status_data = garmin_service.garminapi.get_training_status(date)
        if not training_status_data:
            return {"status": "error", "message": "未获取到训练状态数据", "data": None}
        return {
            "status": "success",
            "message": "获取训练状态数据成功",
            "data": training_status_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取训练状态数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_resting_heart_rate_data(date: str) -> dict:
    """获取指定日期的静息心率数据，日期格式为YYYY-MM-DD"""
    try:
        resting_heart_rate_data = garmin_service.garminapi.get_rhr_day(date)
        if not resting_heart_rate_data:
            return {"status": "error", "message": "未获取到静息心率数据", "data": None}
        return {
            "status": "success",
            "message": "获取静息心率数据成功",
            "data": resting_heart_rate_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取静息心率数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_hydration_data(date: str) -> dict:
    """获取指定日期的饮水数据，日期格式为YYYY-MM-DD"""
    try:
        hydration_data = garmin_service.garminapi.get_hydration_data(date)
        if not hydration_data:
            return {"status": "error", "message": "未获取到饮水数据", "data": None}
        return {
            "status": "success",
            "message": "获取饮水数据成功",
            "data": hydration_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取饮水数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_max_metric_data(date: str) -> dict:
    """获取指定日期的最大指标数据 (如最大摄氧量和健身年龄)，日期格式为YYYY-MM-DD"""
    try:
        max_metric_data = garmin_service.garminapi.get_max_metrics(date)
        if not max_metric_data:
            return {"status": "error", "message": "未获取到最大指标数据", "data": None}
        return {
            "status": "success",
            "message": "获取最大指标数据成功",
            "data": max_metric_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取最大指标数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_heart_rate_variability_data(date: str) -> dict:
    """获取指定日期的心率变异性 (HRV) 数据，日期格式为YYYY-MM-DD"""
    try:
        hrv_data = garmin_service.garminapi.get_hrv_data(date)
        if not hrv_data:
            return {
                "status": "error",
                "message": "未获取到心率变异性数据",
                "data": None,
            }
        return {
            "status": "success",
            "message": "获取心率变异性数据成功",
            "data": hrv_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取心率变异性数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_all_day_stress_data(date: str) -> dict:
    """获取指定日期的全天压力数据，日期格式为YYYY-MM-DD"""
    try:
        stress_data = garmin_service.garminapi.get_stress_data(date)
        if not stress_data:
            return {"status": "error", "message": "未获取到全天压力数据", "data": None}
        return {
            "status": "success",
            "message": "获取全天压力数据成功",
            "data": stress_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取全天压力数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_user_summary(date: str) -> dict:
    """获取指定日期的用户摘要数据. 日期格式: YYYY-MM-DD"""
    try:
        # 导入日志模块并初始化
        logger.info(f"获取用户摘要数据：{date}")
        data = garmin_service.garminapi.get_user_summary(date)
        return {"status": "success", "message": "用户摘要数据获取成功", "data": data}
    except Exception as e:
        logger.error(f"获取用户摘要数据失败：{e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def get_body_composition(start_date: str, end_date: str | None) -> dict:
    """获取指定日期范围内的身体成分数据. 日期格式: YYYY-MM-DD. 如果未提供end_date, 则默认为start_date."""
    try:
        logger.info(
            f"获取身体成分数据：{start_date} to {end_date if end_date else start_date}"
        )
        data = garmin_service.garminapi.get_body_composition(start_date, end_date)
        return {"status": "success", "message": "身体成分数据获取成功", "data": data}
    except Exception as e:
        logger.error(f"获取身体成分数据失败：{e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def get_weigh_ins(start_date: str, end_date: str) -> dict:
    """获取指定日期范围内的体重记录数据. 日期格式: YYYY-MM-DD"""
    try:
        logger.info(f"获取体重记录数据：{start_date} to {end_date}")
        data = garmin_service.garminapi.get_weigh_ins(start_date, end_date)
        return {"status": "success", "message": "体重记录数据获取成功", "data": data}
    except Exception as e:
        logger.error(f"获取体重记录数据失败：{e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def get_devices() -> dict:
    """获取用户关联的Garmin设备列表."""
    try:
        logger.info(f"获取设备列表")
        data = garmin_service.garminapi.get_devices()
        return {"status": "success", "message": "设备列表获取成功", "data": data}
    except Exception as e:
        logger.error(f"获取设备列表失败：{e}")
        return {"status": "error", "message": str(e), "data": None}


@mcp.tool()
def get_calories_data(date: str) -> dict:
    """获取指定日期的卡路里数据，日期格式为YYYY-MM-DD"""
    try:
        logger.info(f"获取卡路里数据：{date}")
        # 获取用户摘要数据，其中通常包含卡路里信息
        summary_data = garmin_service.garminapi.get_user_summary(date)
        if not summary_data or "totalKilocalories" not in summary_data:
            return {
                "status": "error",
                "message": "未获取到卡路里数据或数据格式不正确",
                "data": None,
            }
        # 根据实际返回的字段提取卡路里数据，这里假设是 totalKilocalories
        # 以及其他可能的卡路里相关字段如 activeKilocalories, restingKilocalories
        calories_data = {
            "totalKilocalories": summary_data.get("totalKilocalories"),
            "activeKilocalories": summary_data.get("activeKilocalories"),
            "restingKilocalories": summary_data.get("restingKilocalories"),
            "bmrKilocalories": summary_data.get("bmrKilocalories"),
        }
        return {
            "status": "success",
            "message": "获取卡路里数据成功",
            "data": calories_data,
        }
    except Exception as e:
        logger.error(f"获取卡路里数据失败: {e}")
        return {
            "status": "error",
            "message": f"获取卡路里数据失败: {str(e)}",
            "data": None,
        }


@mcp.tool()
def get_daily_intensity_minutes(date: str) -> dict:
    """获取指定日期的高强度活动分钟数. 日期格式: YYYY-MM-DD"""
    try:
        logger.info(f"获取高强度活动分钟数数据：{date}")
        data = garmin_service.garminapi.get_intensity_minutes_data(
            date
        )  # Corrected API call
        if not data:
            return {
                "status": "error",
                "message": "未获取到高强度活动分钟数数据",
                "data": None,
            }
        return {
            "status": "success",
            "message": "高强度活动分钟数数据获取成功",
            "data": data,
        }
    except Exception as e:
        logger.error(f"获取高强度活动分钟数数据失败：{e}")
        return {"status": "error", "message": str(e), "data": None}
