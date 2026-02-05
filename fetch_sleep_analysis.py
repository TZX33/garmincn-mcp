#!/usr/bin/env python3
"""
获取 Garmin 睡眠与运动关联分析脚本
分析30天睡眠趋势以及睡眠与运动的关系
"""

import sys
import os

# 强制使用国际版 Garmin Connect
os.environ['IS_CN'] = 'false'

# 将 GARMIN_EMAIL/PASSWORD 映射到 EMAIL/PASSWORD
if os.environ.get('GARMIN_EMAIL'):
    os.environ['EMAIL'] = os.environ.get('GARMIN_EMAIL')
if os.environ.get('GARMIN_PASSWORD'):
    os.environ['PASSWORD'] = os.environ.get('GARMIN_PASSWORD')

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from mcp_server_garmincn.service.garmincn_service import GarminService
from cache_manager import CacheManager, GarminDataFetcher
import json

def format_duration(seconds):
    """将秒数转换为 小时:分钟 格式"""
    if seconds is None:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h{minutes:02d}m"

def format_duration_short(seconds):
    """将秒数转换为简短格式"""
    if seconds is None:
        return "N/A"
    hours = seconds / 3600
    return f"{hours:.1f}h"

def get_sleep_quality_emoji(score):
    """根据睡眠得分返回表情"""
    if score is None:
        return ""
    if score >= 80:
        return "😴"
    elif score >= 60:
        return "😌"
    elif score >= 40:
        return "😐"
    else:
        return "😫"

def main():
    print("=" * 70)
    print("📊 Garmin 睡眠趋势与运动关联分析")
    print("=" * 70)
    print()
    
    # 初始化 Garmin 服务
    garmin_service = GarminService()
    result = garmin_service.init_api()
    
    if not result:
        print("❌ 无法连接到 Garmin Connect，请检查认证信息")
        return
    
    api = garmin_service.garminapi
    
    # 创建带缓存的数据获取器
    cache_manager = CacheManager()
    fetcher = GarminDataFetcher(api, cache_manager)
    
    # 获取最近30天的日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"📅 分析时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} (30天)")
    print()
    
    # 存储睡眠数据
    all_sleep_data = []
    
    # 获取所有运动活动
    print("🔄 正在获取运动活动数据...")
    try:
        activities = api.get_activities_by_date(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            None
        )
    except:
        activities = []
    
    # 按日期整理运动数据
    activity_by_date = {}
    for activity in (activities or []):
        date_str = activity.get('startTimeLocal', '')[:10]
        if date_str:
            if date_str not in activity_by_date:
                activity_by_date[date_str] = []
            activity_by_date[date_str].append(activity)
    
    print(f"   找到 {len(activities or [])} 个运动活动")
    
    # 获取30天睡眠数据
    print("🔄 正在获取睡眠数据 (使用本地缓存)...")
    
    for i in range(30):
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            # 使用缓存获取器：历史数据从本地读取，近期数据从 API 获取
            sleep_data = fetcher.get_sleep_data(date_str)
            
            if sleep_data:
                daily_info = sleep_data.get('dailySleepDTO', {})
                sleep_time_seconds = daily_info.get('sleepTimeSeconds')
                
                if sleep_time_seconds:
                    sleep_start = daily_info.get('sleepStartTimestampGMT')
                    sleep_end = daily_info.get('sleepEndTimestampGMT')
                    deep_sleep = daily_info.get('deepSleepSeconds') or 0
                    light_sleep = daily_info.get('lightSleepSeconds') or 0
                    rem_sleep = daily_info.get('remSleepSeconds') or 0
                    awake_time = daily_info.get('awakeSleepSeconds') or 0
                    
                    sleep_scores = sleep_data.get('sleepScores', {})
                    overall_score = sleep_scores.get('overall', {}).get('value')
                    
                    # 获取当天运动数据
                    day_activities = activity_by_date.get(date_str, [])
                    total_exercise_duration = sum(a.get('duration', 0) for a in day_activities)
                    total_calories = sum(a.get('calories', 0) for a in day_activities)
                    exercise_types = [a.get('activityType', {}).get('typeKey', 'unknown') for a in day_activities]
                    
                    # 获取前一天的运动数据（睡眠前）
                    prev_date_str = (date - timedelta(days=1)).strftime('%Y-%m-%d')
                    prev_activities = activity_by_date.get(prev_date_str, [])
                    prev_exercise_duration = sum(a.get('duration', 0) for a in prev_activities)
                    
                    all_sleep_data.append({
                        'date': date_str,
                        'weekday': date.strftime('%a'),
                        'total_seconds': sleep_time_seconds,
                        'deep_seconds': deep_sleep,
                        'light_seconds': light_sleep,
                        'rem_seconds': rem_sleep,
                        'awake_seconds': awake_time,
                        'score': overall_score,
                        'start_time': sleep_start,
                        'end_time': sleep_end,
                        'exercise_duration': total_exercise_duration,
                        'exercise_calories': total_calories,
                        'exercise_types': exercise_types,
                        'prev_day_exercise': prev_exercise_duration
                    })
        except Exception as e:
            pass
    
    print(f"   找到 {len(all_sleep_data)} 天的睡眠数据")
    print()
    
    if not all_sleep_data:
        print("⚠️ 未找到任何睡眠数据记录")
        return
    
    # 按日期排序
    all_sleep_data.sort(key=lambda x: x['date'])
    
    # ========================
    # 第一部分：30天睡眠趋势
    # ========================
    print("=" * 70)
    print("📈 30天睡眠趋势分析")
    print("=" * 70)
    print()
    
    # 按周分组
    weeks = {}
    for d in all_sleep_data:
        date = datetime.strptime(d['date'], '%Y-%m-%d')
        week_num = date.isocalendar()[1]
        week_start = date - timedelta(days=date.weekday())
        week_key = f"第{week_num}周 ({week_start.strftime('%m-%d')})"
        
        if week_key not in weeks:
            weeks[week_key] = []
        weeks[week_key].append(d)
    
    print("📊 每周睡眠统计:")
    print("-" * 70)
    print(f"{'周次':<20} {'平均时长':<12} {'平均深睡':<12} {'平均REM':<12} {'记录天数'}")
    print("-" * 70)
    
    for week_key in sorted(weeks.keys()):
        week_data = weeks[week_key]
        avg_sleep = sum(d['total_seconds'] for d in week_data) / len(week_data)
        avg_deep = sum(d['deep_seconds'] for d in week_data) / len(week_data)
        avg_rem = sum(d['rem_seconds'] for d in week_data) / len(week_data)
        
        print(f"{week_key:<20} {format_duration(avg_sleep):<12} {format_duration(avg_deep):<12} {format_duration(avg_rem):<12} {len(week_data)}天")
    
    print("-" * 70)
    
    # 整体30天统计
    total_avg_sleep = sum(d['total_seconds'] for d in all_sleep_data) / len(all_sleep_data)
    total_avg_deep = sum(d['deep_seconds'] for d in all_sleep_data) / len(all_sleep_data)
    total_avg_rem = sum(d['rem_seconds'] for d in all_sleep_data) / len(all_sleep_data)
    
    print(f"{'30天平均':<20} {format_duration(total_avg_sleep):<12} {format_duration(total_avg_deep):<12} {format_duration(total_avg_rem):<12}")
    print()
    
    # 睡眠时长趋势图
    print("\n📊 30天睡眠时长趋势图:")
    print()
    
    max_hours = max(d['total_seconds'] / 3600 for d in all_sleep_data)
    min_hours = min(d['total_seconds'] / 3600 for d in all_sleep_data)
    
    # 分成几行显示
    for i, d in enumerate(all_sleep_data):
        hours = d['total_seconds'] / 3600
        normalized = (hours - min_hours) / (max_hours - min_hours) if max_hours > min_hours else 0.5
        bar_length = int(normalized * 25) + 5
        
        date_short = d['date'][5:]
        weekday = d['weekday']
        emoji = get_sleep_quality_emoji(d.get('score'))
        
        # 根据睡眠时长显示不同颜色/符号
        if hours >= 7.5:
            bar_char = '█'
        elif hours >= 6.5:
            bar_char = '▓'
        elif hours >= 5.5:
            bar_char = '▒'
        else:
            bar_char = '░'
        
        print(f"   {date_short} {weekday} │ {bar_char * bar_length} {hours:.1f}h {emoji}")
    
    # ========================
    # 第二部分：按星期分析
    # ========================
    print("\n")
    print("=" * 70)
    print("📅 按星期睡眠分析")
    print("=" * 70)
    print()
    
    weekday_data = {i: [] for i in range(7)}
    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    for d in all_sleep_data:
        date = datetime.strptime(d['date'], '%Y-%m-%d')
        weekday = date.weekday()
        weekday_data[weekday].append(d)
    
    print(f"{'星期':<8} {'平均睡眠':<12} {'深睡眠比例':<12} {'REM比例':<12} {'样本数'}")
    print("-" * 60)
    
    for i in range(7):
        data = weekday_data[i]
        if data:
            avg_sleep = sum(d['total_seconds'] for d in data) / len(data)
            avg_deep_ratio = sum(d['deep_seconds'] / d['total_seconds'] * 100 for d in data) / len(data)
            avg_rem_ratio = sum(d['rem_seconds'] / d['total_seconds'] * 100 for d in data) / len(data)
            
            bar = '█' * int(avg_sleep / 3600 * 3)
            print(f"{weekday_names[i]:<8} {format_duration(avg_sleep):<12} {avg_deep_ratio:>6.1f}%      {avg_rem_ratio:>6.1f}%      {len(data)}天  {bar}")
        else:
            print(f"{weekday_names[i]:<8} {'无数据':<12}")
    
    # 找出睡眠最好和最差的星期
    weekday_avgs = []
    for i in range(7):
        if weekday_data[i]:
            avg = sum(d['total_seconds'] for d in weekday_data[i]) / len(weekday_data[i])
            weekday_avgs.append((i, avg))
    
    if weekday_avgs:
        best_day = max(weekday_avgs, key=lambda x: x[1])
        worst_day = min(weekday_avgs, key=lambda x: x[1])
        print()
        print(f"✨ 睡眠最佳: {weekday_names[best_day[0]]} (平均 {format_duration(best_day[1])})")
        print(f"😔 睡眠最差: {weekday_names[worst_day[0]]} (平均 {format_duration(worst_day[1])})")
    
    # ========================
    # 第三部分：睡眠与运动关联分析
    # ========================
    print("\n")
    print("=" * 70)
    print("🏃 睡眠与运动关联分析")
    print("=" * 70)
    print()
    
    # 分析前一天运动对睡眠的影响
    exercise_days = [d for d in all_sleep_data if d['prev_day_exercise'] > 0]
    no_exercise_days = [d for d in all_sleep_data if d['prev_day_exercise'] == 0]
    
    print("📊 前一天运动 vs 不运动的睡眠对比:")
    print("-" * 60)
    
    if exercise_days:
        avg_sleep_with_exercise = sum(d['total_seconds'] for d in exercise_days) / len(exercise_days)
        avg_deep_with_exercise = sum(d['deep_seconds'] for d in exercise_days) / len(exercise_days)
        avg_rem_with_exercise = sum(d['rem_seconds'] for d in exercise_days) / len(exercise_days)
        print(f"   前一天有运动: 平均睡眠 {format_duration(avg_sleep_with_exercise)}")
        print(f"                  深睡眠 {format_duration(avg_deep_with_exercise)}, REM {format_duration(avg_rem_with_exercise)}")
        print(f"                  ({len(exercise_days)}天数据)")
    
    if no_exercise_days:
        avg_sleep_no_exercise = sum(d['total_seconds'] for d in no_exercise_days) / len(no_exercise_days)
        avg_deep_no_exercise = sum(d['deep_seconds'] for d in no_exercise_days) / len(no_exercise_days)
        avg_rem_no_exercise = sum(d['rem_seconds'] for d in no_exercise_days) / len(no_exercise_days)
        print(f"   前一天无运动: 平均睡眠 {format_duration(avg_sleep_no_exercise)}")
        print(f"                  深睡眠 {format_duration(avg_deep_no_exercise)}, REM {format_duration(avg_rem_no_exercise)}")
        print(f"                  ({len(no_exercise_days)}天数据)")
    
    if exercise_days and no_exercise_days:
        diff = avg_sleep_with_exercise - avg_sleep_no_exercise
        if diff > 0:
            print(f"\n   💡 发现: 运动后睡眠时间平均多 {abs(diff)/60:.0f} 分钟")
        else:
            print(f"\n   💡 发现: 运动后睡眠时间平均少 {abs(diff)/60:.0f} 分钟")
        
        deep_diff = avg_deep_with_exercise - avg_deep_no_exercise
        if deep_diff > 0:
            print(f"   💡 发现: 运动后深睡眠时间平均多 {abs(deep_diff)/60:.0f} 分钟")
    
    # 按运动时长分组分析
    print("\n📊 按运动时长分组的睡眠质量:")
    print("-" * 60)
    
    # 分组：无运动、轻度(<30min)、中度(30-60min)、高强度(>60min)
    groups = {
        '无运动': [],
        '轻度(<30分钟)': [],
        '中度(30-60分钟)': [],
        '高强度(>60分钟)': []
    }
    
    for d in all_sleep_data:
        exercise_mins = d['prev_day_exercise'] / 60
        if exercise_mins == 0:
            groups['无运动'].append(d)
        elif exercise_mins < 30:
            groups['轻度(<30分钟)'].append(d)
        elif exercise_mins < 60:
            groups['中度(30-60分钟)'].append(d)
        else:
            groups['高强度(>60分钟)'].append(d)
    
    for group_name, data in groups.items():
        if data:
            avg_sleep = sum(d['total_seconds'] for d in data) / len(data)
            avg_deep = sum(d['deep_seconds'] for d in data) / len(data)
            deep_ratio = avg_deep / avg_sleep * 100 if avg_sleep > 0 else 0
            bar = '█' * int(avg_sleep / 3600 * 3)
            print(f"   {group_name:<16}: {format_duration(avg_sleep):<10} (深睡眠{deep_ratio:>5.1f}%) {bar}  [{len(data)}天]")
    
    # 分析运动类型对睡眠的影响
    print("\n📊 不同运动类型后的睡眠表现:")
    print("-" * 60)
    
    exercise_type_sleep = {}
    for d in all_sleep_data:
        # 获取前一天的运动类型
        prev_date_str = (datetime.strptime(d['date'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        prev_activities = activity_by_date.get(prev_date_str, [])
        
        for activity in prev_activities:
            activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
            if activity_type not in exercise_type_sleep:
                exercise_type_sleep[activity_type] = []
            exercise_type_sleep[activity_type].append(d)
    
    if exercise_type_sleep:
        type_names = {
            'running': '🏃 跑步',
            'walking': '🚶 步行',
            'cycling': '🚴 骑行',
            'strength_training': '🏋️ 力量训练',
            'swimming': '🏊 游泳',
            'yoga': '🧘 瑜伽',
            'hiking': '⛰️ 徒步',
            'elliptical': '🏃 椭圆机',
            'indoor_cycling': '🚴 室内骑行'
        }
        
        for exercise_type, data in sorted(exercise_type_sleep.items(), key=lambda x: -len(x[1])):
            if len(data) >= 2:  # 至少2天数据才显示
                avg_sleep = sum(d['total_seconds'] for d in data) / len(data)
                avg_deep = sum(d['deep_seconds'] for d in data) / len(data)
                display_name = type_names.get(exercise_type, exercise_type)
                print(f"   {display_name:<16}: 后睡眠 {format_duration(avg_sleep)}, 深睡眠 {format_duration(avg_deep)}  [{len(data)}天]")
    else:
        print("   暂无足够数据进行分析")
    
    # ========================
    # 第四部分：发现和建议
    # ========================
    print("\n")
    print("=" * 70)
    print("💡 分析发现与个性化建议")
    print("=" * 70)
    print()
    
    findings = []
    recommendations = []
    
    # 分析入睡时间
    start_times = [d['start_time'] for d in all_sleep_data if d['start_time']]
    if start_times:
        def to_hours(ts):
            dt = datetime.fromtimestamp(ts / 1000)
            hour = dt.hour + dt.minute / 60
            if hour < 12:
                hour += 24
            return hour
        
        avg_start_hour = sum(to_hours(t) for t in start_times) / len(start_times)
        if avg_start_hour >= 24:
            avg_start_hour -= 24
        
        if avg_start_hour > 1:  # 凌晨1点后入睡
            findings.append(f"⏰ 平均入睡时间较晚 ({int(avg_start_hour)}:{int((avg_start_hour % 1) * 60):02d})")
            recommendations.append("建议设置睡前提醒，尝试在23:00-24:00入睡")
    
    # 分析睡眠时长变化
    if len(all_sleep_data) >= 7:
        first_week = all_sleep_data[:7]
        last_week = all_sleep_data[-7:]
        
        first_week_avg = sum(d['total_seconds'] for d in first_week) / len(first_week)
        last_week_avg = sum(d['total_seconds'] for d in last_week) / len(last_week)
        
        change = (last_week_avg - first_week_avg) / 60
        if abs(change) > 15:
            if change > 0:
                findings.append(f"📈 近期睡眠时长增加 (较月初多 {change:.0f} 分钟)")
            else:
                findings.append(f"📉 近期睡眠时长减少 (较月初少 {abs(change):.0f} 分钟)")
                recommendations.append("注意保持充足睡眠，避免睡眠债务累积")
    
    # 分析深睡眠比例
    avg_deep_ratio = sum(d['deep_seconds'] / d['total_seconds'] * 100 for d in all_sleep_data) / len(all_sleep_data)
    if avg_deep_ratio < 13:
        findings.append(f"🔵 深睡眠比例偏低 ({avg_deep_ratio:.1f}%，推荐13-23%)")
        recommendations.append("增加白天运动量、避免睡前咖啡因、保持卧室安静黑暗")
    elif avg_deep_ratio > 23:
        findings.append(f"🔵 深睡眠比例充足 ({avg_deep_ratio:.1f}%)")
    
    # 分析REM比例
    avg_rem_ratio = sum(d['rem_seconds'] / d['total_seconds'] * 100 for d in all_sleep_data) / len(all_sleep_data)
    if avg_rem_ratio < 15:
        findings.append(f"🟣 REM睡眠比例偏低 ({avg_rem_ratio:.1f}%，推荐20-25%)")
        recommendations.append("避免睡前饮酒，保持规律的睡眠时间")
    
    # 分析周末效应
    weekend_data = [d for d in all_sleep_data if datetime.strptime(d['date'], '%Y-%m-%d').weekday() >= 5]
    weekday_sleep_data = [d for d in all_sleep_data if datetime.strptime(d['date'], '%Y-%m-%d').weekday() < 5]
    
    if weekend_data and weekday_sleep_data:
        weekend_avg = sum(d['total_seconds'] for d in weekend_data) / len(weekend_data)
        weekday_avg = sum(d['total_seconds'] for d in weekday_sleep_data) / len(weekday_sleep_data)
        diff = (weekend_avg - weekday_avg) / 60
        
        if diff > 60:
            findings.append(f"📅 周末睡眠比工作日多 {diff:.0f} 分钟")
            recommendations.append("可能存在睡眠债务，建议增加工作日睡眠时间")
    
    # 运动效果分析
    if exercise_days and no_exercise_days:
        if avg_sleep_with_exercise > avg_sleep_no_exercise:
            findings.append(f"🏃 运动对睡眠有积极影响 (多 {(avg_sleep_with_exercise - avg_sleep_no_exercise)/60:.0f} 分钟)")
            recommendations.append("继续保持运动习惯，但避免睡前3小时内高强度运动")
    
    # 输出发现
    if findings:
        print("🔍 主要发现:")
        for f in findings:
            print(f"   {f}")
    
    # 输出建议
    if recommendations:
        print("\n📋 个性化建议:")
        for i, r in enumerate(recommendations, 1):
            print(f"   {i}. {r}")
    
    # 生成睡眠质量评级
    print("\n")
    print("=" * 70)
    print("⭐ 30天睡眠质量评级")
    print("=" * 70)
    print()
    
    # 计算综合得分
    score = 100
    
    # 睡眠时长评分（7-8小时最佳）
    avg_hours = total_avg_sleep / 3600
    if avg_hours < 6:
        score -= 25
    elif avg_hours < 7:
        score -= 10
    elif avg_hours > 9:
        score -= 5
    
    # 深睡眠比例评分
    if avg_deep_ratio < 13:
        score -= 15
    elif avg_deep_ratio < 16:
        score -= 5
    
    # REM评分
    if avg_rem_ratio < 15:
        score -= 10
    elif avg_rem_ratio < 20:
        score -= 5
    
    # 规律性评分（标准差）
    sleep_hours_list = [d['total_seconds'] / 3600 for d in all_sleep_data]
    if len(sleep_hours_list) > 1:
        mean = sum(sleep_hours_list) / len(sleep_hours_list)
        variance = sum((x - mean) ** 2 for x in sleep_hours_list) / len(sleep_hours_list)
        std_dev = variance ** 0.5
        if std_dev > 1.5:
            score -= 15
        elif std_dev > 1:
            score -= 8
    
    score = max(0, min(100, score))
    
    # 显示星级
    stars = int(score / 20)
    star_display = '⭐' * stars + '☆' * (5 - stars)
    
    if score >= 80:
        grade = "优秀"
        grade_emoji = "🏆"
    elif score >= 60:
        grade = "良好"
        grade_emoji = "👍"
    elif score >= 40:
        grade = "一般"
        grade_emoji = "📌"
    else:
        grade = "需改进"
        grade_emoji = "⚠️"
    
    print(f"   综合评分: {score}/100  {star_display}")
    print(f"   评级: {grade} {grade_emoji}")
    print()
    print(f"   评分详情:")
    print(f"   • 平均睡眠时长: {format_duration(total_avg_sleep)} (推荐7-8小时)")
    print(f"   • 深睡眠比例: {avg_deep_ratio:.1f}% (推荐13-23%)")
    print(f"   • REM睡眠比例: {avg_rem_ratio:.1f}% (推荐20-25%)")
    if len(sleep_hours_list) > 1:
        print(f"   • 睡眠规律性: 标准差 {std_dev:.2f}小时 (越小越规律)")
    
    print("\n" + "=" * 70)
    print("✅ 分析完成")
    print("=" * 70)
    
    # 打印缓存统计
    fetcher.print_stats()

if __name__ == "__main__":
    main()
