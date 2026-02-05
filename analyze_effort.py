
"""
Deep dive into running effort based on splits and HR zones.
"""
import sys
import os
import statistics

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from mcp_server_garmincn.service.garmincn_service import GarminService

def format_duration(seconds):
    if not seconds: return "N/A"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"

def format_pace(speed_mps):
    if not speed_mps or speed_mps == 0:
        return "N/A"
    pace_per_km = 1000 / speed_mps
    minutes = int(pace_per_km // 60)
    seconds = int(pace_per_km % 60)
    return f"{minutes}:{seconds:02}"

def analyze_effort():
    print("=" * 70)
    print("🕵️ Deep Dive: Running Effort & Splits Analysis")
    print("=" * 70)
    
    garmin_service = GarminService()
    if not garmin_service.init_api():
        print("Failed to login.")
        return

    api = garmin_service.garminapi
    
    # 1. Find the specific recent best run (The 5.10km run on Feb 4th)
    activities = api.get_activities(0, 5) # Get last 5
    target_activity = None
    
    print("\n🔍 Scanning recent activities...")
    for act in activities:
        # Check if running and date matches roughly (Feb 4th)
        act_type = act.get('activityType', {}).get('typeKey')
        date = act.get('startTimeLocal')[:10]
        dist = act.get('distance', 0) / 1000.0
        
        print(f"   Found: {date} - {act_type} - {dist:.2f}km")
        
        # We are looking for the ~5km run on 2026-02-04
        if 'running' in act_type and date == '2026-02-04' and dist > 4.5:
            target_activity = act
            break
            
    if not target_activity:
        print("⚠️ Could not find the specific 5km run on Feb 4th. Analyzing the most recent run > 3km instead.")
        for act in activities:
             dist = act.get('distance', 0) / 1000.0
             if 'running' in act.get('activityType', {}).get('typeKey') and dist > 3.0:
                 target_activity = act
                 break
    
    if target_activity:
        act_id = target_activity.get('activityId')
        name = target_activity.get('activityName')
        date = target_activity.get('startTimeLocal')
        print(f"\n🎯 Analyzing Target Activity: {name} ({date})")
        print(f"   ID: {act_id}")
        
        # 2. Get Splits
        print("\n📏 Split Analysis:")
        splits = api.get_activity_splits(act_id)
        # Splits usually returned as list of dicts
        
        split_paces = []
        split_hrs = []
        
        if splits:
            print(f"   {'Km':<4} | {'Pace':<10} | {'Elev Gain':<10} | {'Avg HR':<8} | {'Max HR':<8}")
            print("   " + "-"*55)
            
            for split in splits.get('activitySplits', []):
                distance = split.get('distance', 0) # meters
                num = int(distance / 1000) if distance else 0
                if num == 0: continue # Skip the partial first split if it behaves weirdly, typically start at 1
                
                # Garmin returns splits usually by 1km if auto-lap is on. 
                # Sometimes splits are just user laps. Assuming 1km auto-laps for now.
                # Actually, 'split' might be the summary. 'activitySplits' is the list.
                # Let's rely on 'distance' to label them.
                
                duration = split.get('duration', 0)
                speed = split.get('averageSpeed', 0)
                pace = format_pace(speed)
                hr = split.get('averageHR', 0)
                max_hr = split.get('maxHR', 0)
                elev = split.get('elevationGain', 0)
                
                split_paces.append(speed)
                split_hrs.append(hr)
                
                print(f"   {num:<4} | {pace:<10} | {elev:<10.1f} | {hr:<8} | {max_hr:<8}")
                
            # Effort Curve Analysis based on splits
            if len(split_paces) >= 2:
                first_half = split_paces[:len(split_paces)//2]
                second_half = split_paces[len(split_paces)//2:]
                
                avg_first = statistics.mean(first_half)
                avg_second = statistics.mean(second_half)
                
                print("\n   🧠 Pace Strategy Analysis:")
                if avg_second > avg_first * 1.02: # 2% faster
                    print("   🚀 NEGATIVE SPLIT (Accelerating): You ran the second half faster.")
                    print("      Interpretation: You likely had reserved energy. You didn't 'die'.")
                elif avg_first > avg_second * 1.02:
                    print("   📉 POSITIVE SPLIT (Slowing down): You slowed down in the second half.")
                    print("      Interpretation: Potential accumulation of fatigue. You might have started too fast.")
                else:
                    print("   ⚖️ EVEN SPLIT: Very consistent pacing.")
        else:
            print("   No split data available.")
            
        # 3. HR Zones Analysis
        # Note: API method for time in zones might be `get_activity_hr_in_timezones`
        # But inspect_api showed it exists? Let's try.
        # Sometimes it's embedded in activity details.
        
        print("\n💓 Heart Rate Analysis:")
        avg_hr = target_activity.get('averageHR')
        max_hr = target_activity.get('maxHR')
        
        print(f"   - Avg HR: {avg_hr} bpm")
        print(f"   - Max HR: {max_hr} bpm")
        
        # Try to guess user's max HR based on age/formulas or highest observed if not available
        # But generally, 154 avg is usually Zone 3 or 4 for most people.
        # Let's calculate Heart Rate Reserve (HRR) usage if we knew Resting HR.
        # Let's assume a generic Max HR estimate if we can't find specific zones.
        # Rough calc: If user is ~30yo, Max=190. 154 is ~81%. That's Tempo/Threshold.
        
        if avg_hr and avg_hr > 170:
            print("      ⚠️ High Intensity! This average is quite high, suggesting near-maximum effort.")
        elif avg_hr and avg_hr < 145:
            print("      🟢 Aerobic Zone likely. This suggests you were mostly comfortable.")
            
        # 4. Final Verdict on "Did I try my best?"
        print("\n🤔 Final Verdict on Effort:")
        if split_paces:
             # Look at the last km
             last_pace = split_paces[-1]
             avg_pace = statistics.mean(split_paces)
             
             if last_pace > avg_pace: # Faster than average
                 print("   ✅ You sped up at the end.")
                 if avg_hr < 160: # Arbitrary threshold, context dependent
                     print("      Combined with moderate HR, this suggests you **DID NOT** go 100% all-out.")
                     print("      You definitely have untapped potential for a 5k.")
                 else:
                     print("      Strong finish despite high HR. Good mental toughness, but maybe 90-95% effort.")
             else:
                 print("   ⚠️ You slowed down at the end.")
                 print("      This usually indicates high fatigue. You likely pushed close to your current limit.")
        
    else:
        print("No suitable activity found for detailed analysis.")

if __name__ == "__main__":
    analyze_effort()
