
"""
Analyze running data to help adjust goals.
"""
import sys
import os
from datetime import datetime
import statistics

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from mcp_server_garmincn.service.garmincn_service import GarminService

def format_duration(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"

def format_pace(speed_mps):
    if speed_mps == 0:
        return "0:00"
    pace_per_km = 1000 / speed_mps
    minutes = int(pace_per_km // 60)
    seconds = int(pace_per_km % 60)
    return f"{minutes}:{seconds:02}"

def main():
    print("=" * 70)
    print("🏃 Garmin Running Goal Analysis")
    print("=" * 70)
    
    garmin_service = GarminService()
    if not garmin_service.init_api():
        print("Failed to login.")
        return

    api = garmin_service.garminapi
    
    # 1. Fetch Race Predictions
    try:
        print("\n🔮 Race Predictions:")
        predictions = api.get_race_predictions()
        # The structure might vary, let's try to print safe
        if predictions:
             for pred in predictions.get('racePredictions', []):
                 type_key = pred.get('raceId') # e.g. '5K', '10K'
                 time_s = pred.get('time')
                 print(f"   - {type_key}: {format_duration(time_s)}")
    except Exception as e:
        print(f"   Failed to fetch predictions: {e}")

    # 2. Fetch Training Status
    try:
        print("\n📈 Training Status:")
        # Use today's date
        today = datetime.now().strftime('%Y-%m-%d')
        status = api.get_training_status(today)
        if status:
            print(f"   - Status: {status.get('trainingStatus')}")
            print(f"   - VO2Max: {status.get('vo2MaxPreciseValue')}")
    except Exception as e:
        print(f"   Failed to fetch training status: {e}")
        
    # 3. Fetch Recent Running Activities
    print("\n👟 Recent Runs (Last 20 activities filtered for running):")
    try:
        activities = api.get_activities(0, 20) # 0 start, 20 limit
        
        running_activities = []
        for act in activities:
            # Check activity type, usually 'running' or 'treadmill_running'
            # activityType.typeKey
            act_type = act.get('activityType', {}).get('typeKey')
            if 'running' in act_type:
                running_activities.append(act)
        
        if not running_activities:
            print("   No running activities found in last 20 activities.")
        
        paces = []
        distances = []
        
        print(f"   {'Date':<12} | {'Dist (km)':<10} | {'Time':<10} | {'Pace (/km)':<10} | {'Avg HR':<8}")
        print("   " + "-"*60)
        
        for run in running_activities[:10]: # Check last 10 runs
            start_time = run.get('startTimeLocal')[:10]
            distance_m = run.get('distance', 0)
            duration_s = run.get('duration', 0)
            avg_speed = run.get('averageSpeed', 0) # m/s (not pace)
            avg_hr = run.get('averageHR', 0)
            
            dist_km = distance_m / 1000
            pace_str = format_pace(avg_speed)
            
            # Filter for meaningful runs (> 1km) for stats
            if dist_km > 1:
                paces.append(avg_speed)
                distances.append(dist_km)
            
            print(f"   {start_time:<12} | {dist_km:<10.2f} | {format_duration(duration_s):<10} | {pace_str:<10} | {avg_hr:<8}")

        # Analysis
        if paces:
            avg_recent_pace_mps = statistics.mean(paces)
            avg_recent_dist_km = statistics.mean(distances)
            
            print("\n📊 Analysis of Recent Runs:")
            print(f"   - Average Distance: {avg_recent_dist_km:.2f} km")
            print(f"   - Average Pace: {format_pace(avg_recent_pace_mps)} /km")
            
            # Goal Comparison
            # Goal: 5km in 30:00 -> 6:00 /km pace
            goal_pace_mps = 1000 / (6 * 60) # 1000m / 360s = 2.77 m/s
            
            print(f"\n🎯 Goal Check (5km in 30:00 -> 6:00/km):")
            if avg_recent_pace_mps >= goal_pace_mps:
                print("   ✅ Your recent average pace is FASTER than your goal pace.")
                print("      You might want to set a more challenging goal (e.g., 28:00 or 29:00).")
            else:
                diff_per_km = (1000/avg_recent_pace_mps) - (1000/goal_pace_mps)
                print(f"   ⚠️ Your recent average pace is {format_pace(avg_recent_pace_mps)}/km.")
                print(f"      To reach 30:00, you need to improve by roughly {diff_per_km:.0f} seconds per km.")
                print("      This goal is challenging but achievable with consistent training.")

    except Exception as e:
        print(f"   Failed to fetch activities: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
