#!/usr/bin/env python3
"""
获取 Garmin 睡眠数据分析脚本
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
import json

def format_duration(seconds):
    """将秒数转换为 小时:分钟 格式"""
    if seconds is None:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}小时{minutes}分钟"

def format_time_of_day(timestamp_ms):
    """将毫秒时间戳转换为时间格式"""
    if timestamp_ms is None:
        return "N/A"
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%H:%M")
    except:
        return "N/A"

def get_sleep_quality_emoji(score):
    """根据睡眠得分返回表情"""
    if score is None:
        return "❓"
    if score >= 80:
        return "😴💤"  # 优秀
    elif score >= 60:
        return "😌"    # 良好
    elif score >= 40:
        return "😐"    # 一般
    else:
        return "😫"    # 较差

def get_sleep_quality_text(score):
    """根据睡眠得分返回质量描述"""
    if score is None:
        return "无数据"
    if score >= 80:
        return "优秀"
    elif score >= 60:
        return "良好"
    elif score >= 40:
        return "一般"
    else:
        return "较差"

def main():
    print("=" * 60)
    print("😴 Garmin 睡眠数据分析报告")
    print("=" * 60)
    print()
    
    # 初始化 Garmin 服务
    garmin_service = GarminService()
    result = garmin_service.init_api()
    
    if not result:
        print("❌ 无法连接到 Garmin Connect，请检查认证信息")
        return
    
    api = garmin_service.garminapi
    
    # 获取最近7天的日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"📅 分析时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    print()
    
    # 存储睡眠数据用于汇总分析
    all_sleep_data = []
    
    print("=" * 60)
    print("📊 每日睡眠详情")
    print("=" * 60)
    
    # 逐天获取睡眠数据
    for i in range(7):
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            sleep_data = api.get_sleep_data(date_str)
            
            if sleep_data:
                daily_info = sleep_data.get('dailySleepDTO', {})
                
                sleep_time_seconds = daily_info.get('sleepTimeSeconds')
                sleep_start = daily_info.get('sleepStartTimestampGMT')
                sleep_end = daily_info.get('sleepEndTimestampGMT')
                deep_sleep = daily_info.get('deepSleepSeconds')
                light_sleep = daily_info.get('lightSleepSeconds')
                rem_sleep = daily_info.get('remSleepSeconds')
                awake_time = daily_info.get('awakeSleepSeconds')
                
                # 获取睡眠得分
                sleep_scores = sleep_data.get('sleepScores', {})
                overall_score = sleep_scores.get('overall', {}).get('value')
                quality_score = sleep_scores.get('qualityOfSleep', {}).get('qualityOfSleepValue')
                recovery_score = sleep_scores.get('recoveryScore', {}).get('value')
                
                # 如果有数据，添加到汇总列表
                if sleep_time_seconds:
                    all_sleep_data.append({
                        'date': date_str,
                        'total_seconds': sleep_time_seconds,
                        'deep_seconds': deep_sleep or 0,
                        'light_seconds': light_sleep or 0,
                        'rem_seconds': rem_sleep or 0,
                        'awake_seconds': awake_time or 0,
                        'score': overall_score,
                        'quality_score': quality_score,
                        'recovery_score': recovery_score,
                        'start_time': sleep_start,
                        'end_time': sleep_end
                    })
                
                # 打印每日睡眠详情
                emoji = get_sleep_quality_emoji(overall_score)
                quality_text = get_sleep_quality_text(overall_score)
                
                print(f"\n🌙 {date_str} ({date.strftime('%A')[:3]})")
                print("-" * 50)
                
                if sleep_time_seconds:
                    print(f"   睡眠时长: {format_duration(sleep_time_seconds)} {emoji} ({quality_text})")
                    print(f"   入睡时间: {format_time_of_day(sleep_start)}")
                    print(f"   起床时间: {format_time_of_day(sleep_end)}")
                    print()
                    
                    # 睡眠阶段分布
                    if deep_sleep or light_sleep or rem_sleep:
                        print("   📈 睡眠阶段分布:")
                        total = (deep_sleep or 0) + (light_sleep or 0) + (rem_sleep or 0) + (awake_time or 0)
                        if total > 0:
                            deep_pct = ((deep_sleep or 0) / total) * 100
                            light_pct = ((light_sleep or 0) / total) * 100
                            rem_pct = ((rem_sleep or 0) / total) * 100
                            awake_pct = ((awake_time or 0) / total) * 100
                            
                            # 创建进度条
                            bar_length = 30
                            deep_bar = int(deep_pct / 100 * bar_length)
                            light_bar = int(light_pct / 100 * bar_length)
                            rem_bar = int(rem_pct / 100 * bar_length)
                            
                            print(f"      🟦 深睡眠: {format_duration(deep_sleep):<12} ({deep_pct:>5.1f}%) {'█' * deep_bar}")
                            print(f"      🟩 浅睡眠: {format_duration(light_sleep):<12} ({light_pct:>5.1f}%) {'█' * light_bar}")
                            print(f"      🟪 REM睡眠: {format_duration(rem_sleep):<12} ({rem_pct:>5.1f}%) {'█' * rem_bar}")
                            if awake_time and awake_time > 0:
                                print(f"      ⬜ 清醒时间: {format_duration(awake_time):<12} ({awake_pct:>5.1f}%)")
                    
                    # 睡眠得分
                    if overall_score or quality_score or recovery_score:
                        print()
                        print("   🎯 睡眠评分:")
                        if overall_score:
                            print(f"      综合得分: {overall_score}/100")
                        if quality_score:
                            print(f"      睡眠质量: {quality_score}/100")
                        if recovery_score:
                            print(f"      恢复得分: {recovery_score}/100")
                else:
                    print("   ⚠️ 无睡眠数据记录")
                    
        except Exception as e:
            print(f"\n🌙 {date_str}")
            print("-" * 50)
            print(f"   ❌ 获取数据失败: {e}")
    
    # 汇总分析
    if all_sleep_data:
        print("\n")
        print("=" * 60)
        print("📈 一周睡眠汇总分析")
        print("=" * 60)
        
        # 计算平均值
        avg_sleep = sum(d['total_seconds'] for d in all_sleep_data) / len(all_sleep_data)
        avg_deep = sum(d['deep_seconds'] for d in all_sleep_data) / len(all_sleep_data)
        avg_light = sum(d['light_seconds'] for d in all_sleep_data) / len(all_sleep_data)
        avg_rem = sum(d['rem_seconds'] for d in all_sleep_data) / len(all_sleep_data)
        
        scores = [d['score'] for d in all_sleep_data if d['score']]
        avg_score = sum(scores) / len(scores) if scores else None
        
        print(f"\n📊 平均睡眠时长: {format_duration(avg_sleep)}")
        print(f"   平均深睡眠:   {format_duration(avg_deep)}")
        print(f"   平均浅睡眠:   {format_duration(avg_light)}")
        print(f"   平均REM睡眠: {format_duration(avg_rem)}")
        
        if avg_score:
            print(f"\n🎯 平均睡眠得分: {avg_score:.1f}/100 {get_sleep_quality_emoji(avg_score)} ({get_sleep_quality_text(avg_score)})")
        
        # 找出最好和最差的睡眠
        if len(all_sleep_data) > 1:
            best_sleep = max(all_sleep_data, key=lambda x: x['total_seconds'])
            worst_sleep = min(all_sleep_data, key=lambda x: x['total_seconds'])
            
            print(f"\n✨ 最佳睡眠: {best_sleep['date']} ({format_duration(best_sleep['total_seconds'])})")
            print(f"😔 最差睡眠: {worst_sleep['date']} ({format_duration(worst_sleep['total_seconds'])})")
        
        # 计算入睡时间统计
        start_times = [d['start_time'] for d in all_sleep_data if d['start_time']]
        if start_times:
            # 转换为小时数（考虑跨天情况）
            def to_hours(ts):
                dt = datetime.fromtimestamp(ts / 1000)
                hour = dt.hour + dt.minute / 60
                # 如果小于12点，认为是凌晨，加24小时
                if hour < 12:
                    hour += 24
                return hour
            
            avg_start_hour = sum(to_hours(t) for t in start_times) / len(start_times)
            # 转回正常时间
            if avg_start_hour >= 24:
                avg_start_hour -= 24
            avg_start_hours = int(avg_start_hour)
            avg_start_mins = int((avg_start_hour - avg_start_hours) * 60)
            
            print(f"\n⏰ 平均入睡时间: {avg_start_hours:02d}:{avg_start_mins:02d}")
        
        end_times = [d['end_time'] for d in all_sleep_data if d['end_time']]
        if end_times:
            avg_end = sum(datetime.fromtimestamp(t / 1000).hour + datetime.fromtimestamp(t / 1000).minute / 60 for t in end_times) / len(end_times)
            avg_end_hours = int(avg_end)
            avg_end_mins = int((avg_end - avg_end_hours) * 60)
            print(f"⏰ 平均起床时间: {avg_end_hours:02d}:{avg_end_mins:02d}")
        
        # 睡眠建议
        print("\n")
        print("=" * 60)
        print("💡 睡眠建议")
        print("=" * 60)
        print()
        
        recommendations = []
        
        # 根据睡眠时长给建议
        if avg_sleep < 6 * 3600:  # 少于6小时
            recommendations.append("⚠️ 平均睡眠时长不足6小时，建议增加睡眠时间至7-8小时")
        elif avg_sleep < 7 * 3600:
            recommendations.append("📌 平均睡眠时长略低于推荐值，建议尝试提早入睡")
        else:
            recommendations.append("✅ 平均睡眠时长良好，继续保持！")
        
        # 根据深睡眠比例给建议
        deep_ratio = avg_deep / avg_sleep if avg_sleep > 0 else 0
        if deep_ratio < 0.13:  # 深睡眠应占13-23%
            recommendations.append("📌 深睡眠比例偏低，建议：规律运动、减少咖啡因摄入、保持卧室安静黑暗")
        elif deep_ratio > 0.23:
            recommendations.append("✅ 深睡眠比例充足，说明身体恢复良好！")
        else:
            recommendations.append("✅ 深睡眠比例正常")
        
        # 根据REM睡眠给建议
        rem_ratio = avg_rem / avg_sleep if avg_sleep > 0 else 0
        if rem_ratio < 0.15:  # REM应占20-25%
            recommendations.append("📌 REM睡眠偏少，可能影响记忆和情绪。建议避免睡前饮酒")
        
        # 根据平均得分给建议
        if avg_score:
            if avg_score < 50:
                recommendations.append("⚠️ 整体睡眠质量较差，建议：保持规律作息、限制睡前屏幕使用")
            elif avg_score < 70:
                recommendations.append("📌 睡眠质量有提升空间，可以尝试冥想或放松练习")
        
        for rec in recommendations:
            print(f"   {rec}")
        
        # 一周趋势图
        print("\n")
        print("=" * 60)
        print("📊 一周睡眠时长趋势")
        print("=" * 60)
        print()
        
        # 按日期排序
        sorted_data = sorted(all_sleep_data, key=lambda x: x['date'])
        
        max_hours = max(d['total_seconds'] / 3600 for d in sorted_data)
        
        for d in sorted_data:
            hours = d['total_seconds'] / 3600
            bar_length = int((hours / max_hours) * 30) if max_hours > 0 else 0
            date_short = d['date'][5:]  # 只显示月-日
            emoji = get_sleep_quality_emoji(d.get('score'))
            print(f"   {date_short} │ {'█' * bar_length} {hours:.1f}h {emoji}")
    
    else:
        print("\n⚠️ 未找到任何睡眠数据记录")
    
    print("\n" + "=" * 60)
    print("✅ 睡眠分析完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
