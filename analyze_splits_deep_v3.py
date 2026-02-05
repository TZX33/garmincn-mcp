
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
    
    act_id = 21761882047
    
    # Get Splits
    data = api.get_activity_splits(act_id)
    
    laps = []
    if isinstance(data, list):
        laps = data
    elif isinstance(data, dict):
        # Try common keys
        if 'lapDTOs' in data:
            laps = data['lapDTOs']
        elif 'activitySplits' in data:
            laps = data['activitySplits']
        else:
            print(f"DEBUG: Keys in splits data: {list(data.keys())}")
            # Recursively search for a list that looks like laps?
            # No, let's just create a fallback
    
    # Get HR Zones
    zones = api.get_activity_hr_in_timezones(act_id)
    
    # Process Laps
    print("\n🏁 Lap Breakdown:")
    print(f"   {'#':<3} | {'Dist(km)':<8} | {'Pace':<8} | {'AvgHR':<6} | {'MaxHR':<6} | {'Type':<10}")
    print("   " + "-"*60)
    
    for lap in laps:
        idx = lap.get('lapIndex', 0)
        dist = lap.get('distance', 0)
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

if __name__ == "__main__":
    analyze()
