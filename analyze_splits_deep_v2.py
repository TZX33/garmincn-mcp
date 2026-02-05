
"""
Deep analysis of splits/laps for the specific run.
"""
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from mcp_server_garmincn.service.garmincn_service import GarminService

def format_pace(speed_mps):
    if not speed_mps or speed_mps == 0:
        return "-"
    pace_per_km = 1000 / speed_mps
    minutes = int(pace_per_km // 60)
    seconds = int(pace_per_km % 60)
    return f"{minutes}:{seconds:02}"

def analyze():
    print("=" * 70)
    print("🏃 Garmin Deep Split Analysis")
    print("=" * 70)
    
    garmin_service = GarminService()
    if not garmin_service.init_api():
        return
    api = garmin_service.garminapi
    
    # We know the specific activity ID from debug
    act_id = 21761882047
    
    # 1. Get Splits (using the method we verified works)
    laps = api.get_activity_splits(act_id)
    # Verify it's a list
    if isinstance(laps, dict):
         laps = laps.get('activitySplits', [])
    
    # 2. Get HR Zones
    zones = api.get_activity_hr_in_timezones(act_id)
    
    # Process Laps
    print("\n🏁 Lap Breakdown:")
    print(f"   {'#':<3} | {'Dist(km)':<8} | {'Pace':<8} | {'AvgHR':<6} | {'MaxHR':<6} | {'Type':<10}")
    print("   " + "-"*60)
    
    total_dist = 0
    
    # We want to identify the "main" part of the run vs warmup
    for lap in laps:
        idx = lap.get('lapIndex', 0)
        dist = lap.get('distance', 0)
        dur = lap.get('duration', 0)
        speed = lap.get('averageSpeed', 0)
        hr = lap.get('averageHR', 0)
        max_hr = lap.get('maxHR', 0)
        itype = lap.get('intensityType', 'ACTIVE')
        
        # Filter insignificant
        if dist < 50:
             continue
             
        pace = format_pace(speed)
        dist_km = dist / 1000
        
        print(f"   {idx:<3} | {dist_km:<8.2f} | {pace:<8} | {hr:<6.0f} | {max_hr:<6.0f} | {itype:<10}")

    # Process Zones
    print("\n💓 Heart Rate Zones Distribution:")
    total_time = sum(z.get('secsInZone', 0) for z in zones) if zones else 0
    
    if zones and total_time > 0:
        for z in zones:
            num = z.get('zoneNumber')
            secs = z.get('secsInZone', 0)
            low = z.get('zoneLowBoundary')
            pct = (secs / total_time) * 100
            bar = "█" * int(pct / 5)
            print(f"   Zone {num} (>{low} bpm): {pct:5.1f}% {bar}")
            
    # Conclusions
    if laps:
         last_lap = laps[-1]
         print(f"\n🔥 Finish Max HR: {last_lap.get('maxHR', 0)} bpm")

if __name__ == "__main__":
    analyze()
