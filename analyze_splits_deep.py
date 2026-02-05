
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
    
    print(f"\nTarget Activity ID: {act_id}")
    
    # 1. Get Details (for Laps)
    details = api.get_activity_details(act_id)
    laps = details.get('lapDTOs', [])
    
    # 2. Get HR Zones
    zones = api.get_activity_hr_in_timezones(act_id)
    
    # Process Laps
    print("\n🏁 Lap Breakdown:")
    print(f"   {'#':<3} | {'Dist(km)':<8} | {'Pace':<8} | {'AvgHR':<6} | {'MaxHR':<6} | {'Elev':<6}")
    print("   " + "-"*55)
    
    total_dist = 0
    main_laps = []
    
    for lap in laps:
        idx = lap.get('lapIndex')
        dist = lap.get('distance', 0)
        dur = lap.get('duration', 0)
        speed = lap.get('averageSpeed', 0)
        hr = lap.get('averageHR', 0)
        max_hr = lap.get('maxHR', 0)
        elev = lap.get('elevationGain', 0)
        
        # Filter insignificant laps (e.g. paused or very short rest steps < 50m unless high HR)
        if dist < 50 and dur < 30:
            continue
            
        pace = format_pace(speed)
        dist_km = dist / 1000
        
        print(f"   {idx:<3} | {dist_km:<8.2f} | {pace:<8} | {hr:<6.0f} | {max_hr:<6.0f} | {elev:<6.1f}")
        
        total_dist += dist
        if dist > 400: # Consider 'main' running laps as > 400m
            main_laps.append({
                'pace_sec': 1000/speed if speed > 0 else 0,
                'hr': hr,
                'dist': dist
            })

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
            
    # "Did I try my best?" Analysis
    print("\n🤔 Effort Analysis:")
    
    # Check finish
    if laps:
        last_lap = laps[-1]
        last_hr_max = last_lap.get('maxHR', 0)
        last_speed = last_lap.get('averageSpeed', 0)
        
        # Compare last lap pace to avg
        avg_speed = details.get('summaryDTO', {}).get('averageSpeed', 0)
        
        print(f"   🔥 Peak Heart Rate: {last_hr_max} bpm")
        if last_hr_max > 190:
             print("      -> You hit >190 bpm! This is likely your true maximum effort.")
             print("      -> 'Emptying the tank' confirmed.")
        elif last_hr_max > 180:
             print("      -> High effort finish, but maybe not 100% all-out sprint.")
        else:
             print("      -> Controlled finish.")
             
        if zones:
            z3 = next((z for z in zones if z['zoneNumber'] == 3), {'secsInZone':0})
            z4 = next((z for z in zones if z['zoneNumber'] == 4), {'secsInZone':0})
            z5 = next((z for z in zones if z['zoneNumber'] == 5), {'secsInZone':0})
            
            hard_time_pct = ((z4['secsInZone'] + z5['secsInZone']) / total_time) * 100
            print(f"   🏋️ Time in Hard Zones (Z4+Z5): {hard_time_pct:.1f}%")
            
            if hard_time_pct < 10:
                print("      -> Most of the run was Aerobic/Tempo (Zone 3).")
                print("      -> You had the CARDIO capacity to go faster/harder, but your legs or pacing might have held back.")
            else:
                 print("      -> You spent significant time in the 'pain cave'. Good effort.")

if __name__ == "__main__":
    analyze()
