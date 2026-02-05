#!/usr/bin/env python3
"""
获取 Garmin 跑步数据和目标分析脚本
"""

import sys
import os

# 强制使用国际版 Garmin Connect（非中国版）
os.environ['IS_CN'] = 'false'

# 将 GARMIN_EMAIL/PASSWORD 映射到 EMAIL/PASSWORD（GarminService 使用的变量名）
if os.environ.get('GARMIN_EMAIL'):
    os.environ['EMAIL'] = os.environ.get('GARMIN_EMAIL')
if os.environ.get('GARMIN_PASSWORD'):
    os.environ['PASSWORD'] = os.environ.get('GARMIN_PASSWORD')

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from mcp_server_garmincn.service.garmincn_service import GarminService
import json

def format_time(seconds):
    """将秒数转换为 HH:MM:SS 格式"""
    if seconds is None:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def format_pace(speed_mps):
    """将速度(m/s)转换为配速(分:秒/公里)"""
    if speed_mps is None or speed_mps == 0:
        return "N/A"
    pace_seconds_per_km = 1000 / speed_mps
    minutes = int(pace_seconds_per_km // 60)
    seconds = int(pace_seconds_per_km % 60)
    return f"{minutes}'{seconds:02d}\""

def main():
    print("=" * 60)
    print("🏃 Garmin 运动数据分析报告")
    print("=" * 60)
    print()
    
    # 初始化 Garmin 服务
    garmin_service = GarminService()
    result = garmin_service.init_api()
    
    if not result:
        print("❌ 无法连接到 Garmin Connect，请检查认证信息")
        return
    
    api = garmin_service.garminapi
    
    # 获取最近90天的日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    print(f"📅 分析时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    print()
    
    # 获取所有活动（不限类型）
    print("📊 正在获取所有活动数据...")
    try:
        all_activities = api.get_activities_by_date(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            None  # 获取所有类型活动
        )
        
        # 先获取最近100个活动作为备选
        recent_activities = api.get_activities(0, 100)
        
        # 合并并去重
        activity_ids = set()
        activities = []
        
        for activity in (all_activities or []) + (recent_activities or []):
            aid = activity.get('activityId')
            if aid and aid not in activity_ids:
                activity_ids.add(aid)
                activities.append(activity)
        
        if not activities:
            print("⚠️ 没有找到任何活动记录")
        else:
            # 按类型分组
            activities_by_type = {}
            running_activities = []
            
            for activity in activities:
                activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
                if activity_type not in activities_by_type:
                    activities_by_type[activity_type] = []
                activities_by_type[activity_type].append(activity)
                
                # 筛选跑步活动
                if 'running' in activity_type.lower() or 'run' in activity_type.lower():
                    running_activities.append(activity)
            
            print(f"\n📋 活动类型统计:")
            print("-" * 40)
            for atype, alist in sorted(activities_by_type.items(), key=lambda x: -len(x[1])):
                print(f"   • {atype}: {len(alist)} 次")
            
            # 分析跑步活动
            if running_activities:
                print(f"\n\n🏃 跑步活动详情 (共 {len(running_activities)} 次):\n")
                print("-" * 90)
                print(f"{'日期':<12} {'活动名称':<25} {'距离(km)':<10} {'时间':<12} {'配速':<10} {'心率':<8}")
                print("-" * 90)
                
                total_distance = 0
                total_duration = 0
                total_calories = 0
                paces = []
                
                # 按日期排序（最新的在前）
                running_activities.sort(key=lambda x: x.get('startTimeLocal', ''), reverse=True)
                
                for activity in running_activities[:20]:  # 显示最近20次
                    date = activity.get('startTimeLocal', 'N/A')[:10]
                    name = (activity.get('activityName', 'N/A') or 'N/A')[:23]
                    distance = (activity.get('distance') or 0) / 1000  # 转换为公里
                    duration = activity.get('duration') or 0
                    avg_speed = activity.get('averageSpeed') or 0
                    avg_hr = activity.get('averageHR') or 'N/A'
                    calories = activity.get('calories') or 0
                    
                    total_distance += distance
                    total_duration += duration
                    total_calories += calories
                    if avg_speed > 0:
                        paces.append(1000 / avg_speed)  # 秒/公里
                    
                    print(f"{date:<12} {name:<25} {distance:<10.2f} {format_time(duration):<12} {format_pace(avg_speed):<10} {avg_hr}")
                
                print("-" * 90)
                
                if len(running_activities) > 20:
                    print(f"   ... 还有 {len(running_activities) - 20} 次跑步活动未显示")
                
                # 计算所有跑步活动的汇总
                all_distance = sum((a.get('distance') or 0) / 1000 for a in running_activities)
                all_duration = sum(a.get('duration') or 0 for a in running_activities)
                
                print(f"\n📈 跑步汇总:")
                print(f"   • 总距离: {all_distance:.2f} 公里")
                print(f"   • 总时间: {format_time(all_duration)}")
                print(f"   • 平均每次: {all_distance/len(running_activities):.2f} 公里")
                if paces:
                    avg_pace = sum(paces) / len(paces)
                    print(f"   • 平均配速: {int(avg_pace // 60)}'{int(avg_pace % 60):02d}\"/km")
                
                # 计算周跑量趋势
                weeks_data = {}
                for activity in running_activities:
                    date_str = activity.get('startTimeLocal', '')[:10]
                    if date_str:
                        date = datetime.strptime(date_str, '%Y-%m-%d')
                        week_start = date - timedelta(days=date.weekday())
                        week_key = week_start.strftime('%Y-%m-%d')
                        if week_key not in weeks_data:
                            weeks_data[week_key] = {'distance': 0, 'count': 0}
                        weeks_data[week_key]['distance'] += (activity.get('distance') or 0) / 1000
                        weeks_data[week_key]['count'] += 1
                
                if weeks_data:
                    print(f"\n📊 周跑量趋势:")
                    for week, data in sorted(weeks_data.items(), reverse=True)[:8]:
                        bars = '█' * int(data['distance'] / 2)
                        print(f"   {week}: {data['distance']:>6.1f} km ({data['count']}次) {bars}")
            else:
                print("\n⚠️ 没有找到跑步活动记录")
                
    except Exception as e:
        import traceback
        print(f"❌ 获取活动数据失败: {e}")
        traceback.print_exc()
    
    # 获取用户目标
    print("\n" + "=" * 60)
    print("🎯 用户目标信息")
    print("=" * 60)
    
    try:
        # 获取今天的用户摘要（包含目标信息）
        today = datetime.now().strftime('%Y-%m-%d')
        user_summary = api.get_user_summary(today)
        
        if user_summary:
            print(f"\n📋 每日目标:")
            step_goal = user_summary.get('dailyStepGoal')
            current_steps = user_summary.get('totalSteps')
            intensity_goal = user_summary.get('intensityMinutesGoal')
            mod_intensity = user_summary.get('moderateIntensityMinutes') or 0
            vig_intensity = user_summary.get('vigorousIntensityMinutes') or 0
            
            print(f"   • 步数目标: {step_goal if step_goal else 'N/A'} 步")
            print(f"   • 当前步数: {current_steps if current_steps else 'N/A'} 步")
            if step_goal and current_steps:
                progress = (current_steps / step_goal) * 100
                print(f"   • 步数完成度: {progress:.1f}%")
            print(f"   • 高强度活动分钟目标: {intensity_goal if intensity_goal else 'N/A'} 分钟")
            print(f"   • 当前高强度活动分钟: {mod_intensity + vig_intensity} 分钟")
            
            # 输出完整的用户摘要用于调试
            print(f"\n📄 完整用户摘要数据:")
            for key, value in user_summary.items():
                if value is not None:
                    print(f"   • {key}: {value}")
            
    except Exception as e:
        print(f"获取用户摘要失败: {e}")
    
    # 获取用户个人资料和目标
    print("\n" + "=" * 60)
    print("👤 用户个人资料")
    print("=" * 60)
    try:
        user_profile = api.get_user_settings()
        if user_profile:
            print(f"\n📝 用户设置:")
            for key, value in user_profile.items():
                if value is not None and key not in ['id', 'userId']:
                    print(f"   • {key}: {value}")
    except Exception as e:
        print(f"获取用户设置失败: {e}")
    
    # 获取训练状态
    print("\n" + "=" * 60)
    print("💪 训练状态分析")
    print("=" * 60)
    
    try:
        training_status = api.get_training_status(today)
        if training_status:
            print(f"\n📊 训练状态:")
            training_data = training_status[0] if isinstance(training_status, list) else training_status
            print(f"   • VO2Max 跑步: {training_data.get('vo2MaxValue', 'N/A')}")
            
            load_balance = training_data.get('trainingLoadBalance', {})
            if load_balance:
                print(f"   • 训练负荷: {load_balance.get('currentValue', 'N/A')}")
            
            print(f"   • 训练状态: {training_data.get('trainingStatusPhrase', 'N/A')}")
            
            # 输出完整训练状态数据
            print(f"\n📄 完整训练状态数据:")
            for key, value in training_data.items():
                if value is not None:
                    print(f"   • {key}: {value}")
            
    except Exception as e:
        print(f"获取训练状态失败: {e}")
    
    # 获取最大指标（VO2Max等）
    try:
        max_metrics = api.get_max_metrics(today)
        if max_metrics:
            print(f"\n📈 最大指标:")
            metrics = max_metrics[0] if isinstance(max_metrics, list) else max_metrics
            generic = metrics.get('generic', {})
            running = metrics.get('running', {})
            cycling = metrics.get('cycling', {})
            
            if generic:
                print(f"   • 通用 VO2Max: {generic.get('vo2MaxPreciseValue', 'N/A')}")
                print(f"   • 健身年龄: {generic.get('fitnessAge', 'N/A')} 岁")
            if running:
                print(f"   • 跑步 VO2Max: {running.get('vo2MaxPreciseValue', 'N/A')}")
            if cycling:
                print(f"   • 骑行 VO2Max: {cycling.get('vo2MaxPreciseValue', 'N/A')}")
            
    except Exception as e:
        print(f"获取最大指标失败: {e}")
    
    # 获取训练准备程度
    try:
        training_readiness = api.get_training_readiness(today)
        if training_readiness:
            print(f"\n⚡ 训练准备程度:")
            print(f"   • 准备程度得分: {training_readiness.get('score', 'N/A')}")
            print(f"   • 准备程度等级: {training_readiness.get('level', 'N/A')}")
            
    except Exception as e:
        print(f"获取训练准备程度失败: {e}")
    
    # 获取个人记录
    print("\n" + "=" * 60)
    print("🏆 个人最佳记录")
    print("=" * 60)
    try:
        personal_records = api.get_personal_record()
        if personal_records:
            print(f"\n🏅 跑步个人记录:")
            for record in personal_records:
                type_id = record.get('typeId')
                value = record.get('value')
                set_on = record.get('prStartTimeGmtFormatted', 'N/A')[:10] if record.get('prStartTimeGmtFormatted') else 'N/A'
                
                # 解析记录类型
                if type_id == 1:
                    print(f"   • 最快1公里: {format_time(value)} (设立于 {set_on})")
                elif type_id == 2:
                    print(f"   • 最快1英里: {format_time(value)} (设立于 {set_on})")
                elif type_id == 3:
                    print(f"   • 最快5公里: {format_time(value)} (设立于 {set_on})")
                elif type_id == 4:
                    print(f"   • 最快10公里: {format_time(value)} (设立于 {set_on})")
                elif type_id == 5:
                    print(f"   • 最快半马: {format_time(value)} (设立于 {set_on})")
                elif type_id == 6:
                    print(f"   • 最快全马: {format_time(value)} (设立于 {set_on})")
                elif type_id == 7:
                    print(f"   • 最长跑步距离: {value/1000:.2f} km (设立于 {set_on})")
    except Exception as e:
        print(f"获取个人记录失败: {e}")
    
    # 获取用户目标（如果有专门的API）
    print("\n" + "=" * 60)
    print("🎯 训练目标")
    print("=" * 60)
    try:
        # 尝试获取用户目标
        goals = api.get_goals("all")
        if goals:
            print(f"\n📌 用户设定的目标:")
            for goal in goals:
                print(f"\n   目标: {goal.get('goalTypeName', 'N/A')}")
                print(f"   • 状态: {goal.get('goalStatus', 'N/A')}")
                print(f"   • 目标值: {goal.get('goalValue', 'N/A')}")
                print(f"   • 当前进度: {goal.get('progressValue', 'N/A')}")
                print(f"   • 开始日期: {goal.get('startDate', 'N/A')}")
                print(f"   • 结束日期: {goal.get('endDate', 'N/A')}")
    except Exception as e:
        print(f"获取用户目标失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 数据获取完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
