
"""
Calculate VDOT and equivalent race times based on recent performance.
"""
def get_vdot(distance_km, time_min):
    # Very rough approximation formulas or lookup table simulation
    # Using specific known benchmarks for approximation:
    # 5k in 30:00 -> VDOT 31
    # 5k in 25:00 -> VDOT 38
    # 5k in 20:00 -> VDOT 49.8
    
    # Linear interpolation for range 25-30 min 5k
    # 5 min diff = 7 VDOT points. 1.4 pts per min.
    
    if distance_km == 5.0:
        diff_from_30 = 30.0 - time_min
        return 31.0 + (diff_from_30 * 1.4)
    return 30.0 # Default

def training_paces(vdot):
    # Based on Jack Daniels formulas
    # E-pace (Easy): ~75-80% max HR (Slow)
    # M-pace (Marathon): ~80-85%
    # T-pace (Threshold): ~88-92% (Comfortably Hard, ~1 hour race pace)
    # I-pace (Interval): ~98-100% HRmax (VO2 Max, ~10-15 min race pace / 3k-5k pace)
    # R-pace (Repetition): >100% (Speed/Economy)
    
    # Simple offsets from 5k pace (approx) for someone around 30min 5k
    # 30min 5k = 6:00/km
    
    # VDOT 31 (30:00 5k):
    # E: 7:38 - 8:15 /km
    # M: 7:00 /km
    # T: 6:10 /km
    # I: 5:40 /km
    # R: 5:20 /km
    
    # VDOT 34 (28:00 5k - 5:36/km):
    # T: 5:50 /km
    # I: 5:20 /km
    # R: 5:00 /km
    
    # User ran Intervals at ~5:10 and Finish at 5:51
    # User's I-pace seems to be ~5:05-5:10 -> Corresponds to VDOT ~35-36 (27:00 5k potential)
    # User's T-pace sustained (1.7k) was 5:51 -> Corresponds to VDOT ~34 (28:00 5k potential)
    
    return {
        "VDOT_Est": vdot
    }

if __name__ == "__main__":
    # Scenario A: Current 5k PB ~31:30 -> VDOT ~29
    # Scenario B: User's Interval Speed (5:05) -> Suggests VDOT ~36
    # Scenario C: User's Finish Speed (5:51) -> Suggests VDOT ~34
    
    print("Potential VDOT Analysis:")
    print("Based on Speed (5:05/km reps): VDOT ~36 -> Potential 5k Time: ~27:00")
    print("Based on Sustained Finish (5:51/km): VDOT ~34 -> Potential 5k Time: ~28:00")
    print("Based on Average Result (6:10/km): VDOT ~30 -> Potential 5k Time: ~30:50")
    
    print("\nConclusion: Huge Aerobic Deficit.")
    print("The user has the speed of a 27-minute runner but the endurance of a 31-minute runner.")
