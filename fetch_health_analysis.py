#!/usr/bin/env python3
"""
Garmin 综合健康分析脚本
分析心率、压力、HRV、身体电量等指标
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

def main():
    print("=" * 70)
    print("💓 Garmin 综合健康分析报告")
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
    end_date = datetime.now()
    
    print(f"📅 分析日期: {end_date.strftime('%Y-%m-%d')}")
    print()
    
    # ========================
    # 心率数据分析
    # ========================
    print("=" * 70)
    print("❤️ 心率分析 (最近7天)")
    print("=" * 70)
    print()
    
    hr_data_list = []
    for i in range(7):
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            hr_data = fetcher.get_heart_rates(date_str)
            if hr_data:
                resting_hr = hr_data.get('restingHeartRate')
                max_hr = hr_data.get('maxHeartRate')
                min_hr = hr_data.get('minHeartRate')
                
                if resting_hr:
                    hr_data_list.append({
                        'date': date_str,
                        'resting': resting_hr,
                        'max': max_hr,
                        'min': min_hr
                    })
                    print(f"   {date_str}: 静息心率 {resting_hr} bpm, 范围 {min_hr or 'N/A'}-{max_hr or 'N/A'} bpm")
        except Exception as e:
            pass
    
    if hr_data_list:
        avg_resting = sum(d['resting'] for d in hr_data_list) / len(hr_data_list)
        print()
        print(f"   📊 7天平均静息心率: {avg_resting:.0f} bpm")
        
        # 心率评估
        if avg_resting < 50:
            print(f"   💪 评估: 运动员级别！")
        elif avg_resting < 60:
            print(f"   ✅ 评估: 非常健康")
        elif avg_resting < 70:
            print(f"   ✅ 评估: 健康")
        elif avg_resting < 80:
            print(f"   📌 评估: 一般，可通过运动改善")
        else:
            print(f"   ⚠️ 评估: 偏高，建议关注")
    
    # ========================
    # 压力数据分析
    # ========================
    print("\n")
    print("=" * 70)
    print("😰 压力水平分析 (最近7天)")
    print("=" * 70)
    print()
    
    stress_data_list = []
    for i in range(7):
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            stress_data = fetcher.get_stress_data(date_str)
            if stress_data:
                avg_stress = stress_data.get('avgStressLevel')
                max_stress = stress_data.get('maxStressLevel')
                stress_duration = stress_data.get('stressDuration')
                rest_duration = stress_data.get('restStressDuration')
                low_duration = stress_data.get('lowStressDuration')
                medium_duration = stress_data.get('mediumStressDuration')
                high_duration = stress_data.get('highStressDuration')
                
                if avg_stress:
                    stress_data_list.append({
                        'date': date_str,
                        'avg': avg_stress,
                        'max': max_stress,
                        'rest': rest_duration or 0,
                        'low': low_duration or 0,
                        'medium': medium_duration or 0,
                        'high': high_duration or 0
                    })
                    
                    # 压力等级表情
                    if avg_stress < 25:
                        emoji = "😌"
                    elif avg_stress < 50:
                        emoji = "🙂"
                    elif avg_stress < 75:
                        emoji = "😐"
                    else:
                        emoji = "😰"
                    
                    print(f"   {date_str}: 平均 {avg_stress} {emoji}, 最高 {max_stress or 'N/A'}")
        except Exception as e:
            pass
    
    if stress_data_list:
        avg_stress = sum(d['avg'] for d in stress_data_list) / len(stress_data_list)
        avg_high = sum(d['high'] for d in stress_data_list) / len(stress_data_list) / 60
        avg_rest = sum(d['rest'] for d in stress_data_list) / len(stress_data_list) / 60
        
        print()
        print(f"   📊 7天平均压力值: {avg_stress:.0f}/100")
        print(f"   ⏱️ 平均每日高压时间: {avg_high:.0f} 分钟")
        print(f"   😌 平均每日休息时间: {avg_rest:.0f} 分钟")
        
        # 压力分布可视化
        print("\n   📈 压力分布 (最近一天):")
        if stress_data_list:
            latest = stress_data_list[0]
            total = latest['rest'] + latest['low'] + latest['medium'] + latest['high']
            if total > 0:
                rest_pct = latest['rest'] / total * 100
                low_pct = latest['low'] / total * 100
                medium_pct = latest['medium'] / total * 100
                high_pct = latest['high'] / total * 100
                
                print(f"      😌 休息: {rest_pct:>5.1f}% {'█' * int(rest_pct / 3)}")
                print(f"      🟢 低压: {low_pct:>5.1f}% {'█' * int(low_pct / 3)}")
                print(f"      🟡 中压: {medium_pct:>5.1f}% {'█' * int(medium_pct / 3)}")
                print(f"      🔴 高压: {high_pct:>5.1f}% {'█' * int(high_pct / 3)}")
    
    # ========================
    # HRV 分析
    # ========================
    print("\n")
    print("=" * 70)
    print("📈 HRV (心率变异性) 分析")
    print("=" * 70)
    print()
    
    hrv_data_list = []
    for i in range(7):
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            hrv_data = fetcher.get_hrv_data(date_str)
            if hrv_data:
                hrv_summary = hrv_data.get('hrvSummary', {})
                weekly_avg = hrv_summary.get('weeklyAvg')
                last_night = hrv_summary.get('lastNight')
                baseline_low = hrv_summary.get('baselineLow')
                baseline_high = hrv_summary.get('baselineHigh')
                status = hrv_summary.get('status')
                
                if last_night or weekly_avg:
                    hrv_data_list.append({
                        'date': date_str,
                        'last_night': last_night,
                        'weekly_avg': weekly_avg,
                        'baseline_low': baseline_low,
                        'baseline_high': baseline_high,
                        'status': status
                    })
                    
                    status_emoji = {
                        'BALANCED': '✅',
                        'UNBALANCED': '⚠️',
                        'LOW': '📉',
                        'HIGH': '📈'
                    }.get(status, '•')
                    
                    print(f"   {date_str}: 昨晚HRV {last_night or 'N/A'} ms, 周平均 {weekly_avg or 'N/A'} ms {status_emoji}")
        except Exception as e:
            pass
    
    if hrv_data_list:
        valid_hrv = [d['last_night'] for d in hrv_data_list if d['last_night']]
        if valid_hrv:
            avg_hrv = sum(valid_hrv) / len(valid_hrv)
            print()
            print(f"   📊 7天平均HRV: {avg_hrv:.0f} ms")
            
            # HRV评估
            if avg_hrv > 60:
                print(f"   ✅ 评估: HRV很高，身体恢复能力强！")
            elif avg_hrv > 40:
                print(f"   ✅ 评估: HRV正常，身体状态良好")
            elif avg_hrv > 20:
                print(f"   📌 评估: HRV偏低，注意休息和恢复")
            else:
                print(f"   ⚠️ 评估: HRV较低，建议减少压力")
            
            print("\n   💡 HRV知识: HRV越高代表自主神经系统越健康，身体恢复能力越强")
    
    # ========================
    # 身体电量分析
    # ========================
    print("\n")
    print("=" * 70)
    print("🔋 身体电量 (Body Battery) 分析")
    print("=" * 70)
    print()
    
    bb_data_list = []
    for i in range(7):
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            bb_data = fetcher.get_body_battery(date_str)
            if bb_data:
                # 获取当天的身体电量数据
                for item in bb_data:
                    if 'charged' in item or 'drained' in item:
                        charged = item.get('charged', 0)
                        drained = item.get('drained', 0)
                        
                        bb_data_list.append({
                            'date': date_str,
                            'charged': charged,
                            'drained': drained,
                            'net': charged - drained
                        })
                        
                        if charged - drained > 0:
                            emoji = "🔋⬆️"
                        else:
                            emoji = "🪫⬇️"
                        
                        print(f"   {date_str}: 充电 +{charged}, 消耗 -{drained}, 净值 {charged-drained:+d} {emoji}")
                        break
        except Exception as e:
            pass
    
    if bb_data_list:
        avg_charged = sum(d['charged'] for d in bb_data_list) / len(bb_data_list)
        avg_drained = sum(d['drained'] for d in bb_data_list) / len(bb_data_list)
        avg_net = sum(d['net'] for d in bb_data_list) / len(bb_data_list)
        
        print()
        print(f"   📊 7天平均:")
        print(f"      充电量: +{avg_charged:.0f}")
        print(f"      消耗量: -{avg_drained:.0f}")
        print(f"      净值: {avg_net:+.0f}")
        
        if avg_net < 0:
            print(f"\n   ⚠️ 警告: 你的身体电量持续透支！建议增加休息和睡眠")
        elif avg_net < 10:
            print(f"\n   📌 提示: 能量收支接近平衡，注意避免过度劳累")
        else:
            print(f"\n   ✅ 很好: 能量盈余充足，身体恢复良好！")
    
    # ========================
    # 呼吸数据分析
    # ========================
    print("\n")
    print("=" * 70)
    print("🌬️ 呼吸分析")
    print("=" * 70)
    print()
    
    for i in range(3):  # 只查看最近3天
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            resp_data = fetcher.get_respiration_data(date_str)
            if resp_data:
                avg_waking = resp_data.get('avgWakingRespirationValue')
                avg_sleeping = resp_data.get('avgSleepingRespirationValue')
                
                if avg_waking or avg_sleeping:
                    print(f"   {date_str}: 清醒呼吸 {avg_waking or 'N/A'} 次/分, 睡眠呼吸 {avg_sleeping or 'N/A'} 次/分")
        except Exception as e:
            pass
    
    # ========================
    # SpO2 血氧分析
    # ========================
    print("\n")
    print("=" * 70)
    print("🩸 血氧 (SpO2) 分析")
    print("=" * 70)
    print()
    
    spo2_list = []
    for i in range(7):
        date = end_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            spo2_data = fetcher.get_spo2_data(date_str)
            if spo2_data:
                avg_spo2 = spo2_data.get('averageSpO2')
                min_spo2 = spo2_data.get('lowestSpO2')
                
                if avg_spo2:
                    spo2_list.append({
                        'date': date_str,
                        'avg': avg_spo2,
                        'min': min_spo2
                    })
                    
                    if avg_spo2 >= 95:
                        emoji = "✅"
                    elif avg_spo2 >= 90:
                        emoji = "📌"
                    else:
                        emoji = "⚠️"
                    
                    print(f"   {date_str}: 平均 {avg_spo2}%, 最低 {min_spo2 or 'N/A'}% {emoji}")
        except Exception as e:
            pass
    
    if spo2_list:
        avg_spo2 = sum(d['avg'] for d in spo2_list) / len(spo2_list)
        print()
        print(f"   📊 7天平均血氧: {avg_spo2:.1f}%")
        
        if avg_spo2 >= 96:
            print(f"   ✅ 评估: 血氧水平非常好！")
        elif avg_spo2 >= 94:
            print(f"   ✅ 评估: 血氧正常")
        else:
            print(f"   📌 评估: 血氧偏低，建议关注")
    
    # ========================
    # 训练准备程度
    # ========================
    print("\n")
    print("=" * 70)
    print("⚡ 训练准备程度")
    print("=" * 70)
    print()
    
    today = end_date.strftime('%Y-%m-%d')
    try:
        readiness = fetcher.get_training_readiness(today)
        if readiness:
            score = readiness.get('score')
            level = readiness.get('level')
            
            if score:
                # 创建仪表盘
                filled = int(score / 5)
                empty = 20 - filled
                gauge = '█' * filled + '░' * empty
                
                print(f"   当前准备程度: [{gauge}] {score}/100")
                print(f"   等级: {level or 'N/A'}")
                
                factors = readiness.get('sleepScore', {})
                if factors:
                    print(f"\n   影响因素:")
                    print(f"      • 睡眠因素: {factors.get('sleepScoreValue', 'N/A')}")
    except Exception as e:
        pass
    
    # ========================
    # 综合健康评估
    # ========================
    print("\n")
    print("=" * 70)
    print("📋 综合健康评估")
    print("=" * 70)
    print()
    
    health_score = 100
    insights = []
    
    # 基于各项数据评估
    if hr_data_list:
        avg_resting = sum(d['resting'] for d in hr_data_list) / len(hr_data_list)
        if avg_resting < 65:
            insights.append("❤️ 静息心率健康，心血管功能良好")
        elif avg_resting < 75:
            insights.append("❤️ 静息心率正常")
        else:
            insights.append("❤️ 静息心率偏高，建议增加有氧运动")
            health_score -= 10
    
    if stress_data_list:
        avg_stress = sum(d['avg'] for d in stress_data_list) / len(stress_data_list)
        if avg_stress < 35:
            insights.append("😌 压力水平低，身心放松")
        elif avg_stress < 50:
            insights.append("🙂 压力水平适中")
        else:
            insights.append("😰 压力水平较高，建议放松活动")
            health_score -= 15
    
    if hrv_data_list:
        valid_hrv = [d['last_night'] for d in hrv_data_list if d['last_night']]
        if valid_hrv:
            avg_hrv = sum(valid_hrv) / len(valid_hrv)
            if avg_hrv > 50:
                insights.append("📈 HRV良好，自主神经系统健康")
            else:
                insights.append("📉 HRV偏低，身体可能需要更多恢复")
                health_score -= 10
    
    if bb_data_list:
        avg_net = sum(d['net'] for d in bb_data_list) / len(bb_data_list)
        if avg_net > 0:
            insights.append("🔋 能量盈余，身体恢复良好")
        else:
            insights.append("🪫 能量透支，需要增加休息")
            health_score -= 15
    
    print("   🔍 健康洞察:")
    for insight in insights:
        print(f"      {insight}")
    
    # 健康评分
    health_score = max(0, min(100, health_score))
    stars = int(health_score / 20)
    
    print()
    print(f"   ⭐ 综合健康评分: {health_score}/100 {'⭐' * stars}{'☆' * (5-stars)}")
    
    if health_score >= 80:
        print(f"   🏆 状态: 优秀！继续保持良好的生活习惯")
    elif health_score >= 60:
        print(f"   👍 状态: 良好，有改进空间")
    else:
        print(f"   📌 状态: 需要关注，建议调整作息和运动")
    
    print("\n" + "=" * 70)
    print("✅ 健康分析完成")
    print("=" * 70)
    
    # 打印缓存统计
    fetcher.print_stats()

if __name__ == "__main__":
    main()
