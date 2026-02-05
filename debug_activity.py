
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from mcp_server_garmincn.service.garmincn_service import GarminService

def debug_act():
    garmin_service = GarminService()
    if not garmin_service.init_api():
        return
    api = garmin_service.garminapi
    
    act_id = 21761882047
    
    print(f"--- Debugging Activity {act_id} ---")
    
    # Check splits
    try:
        splits = api.get_activity_splits(act_id)
        print("\n[Splits Keys]:", splits.keys() if splits else "None")
        if splits:
            print(json.dumps(splits, indent=2))
    except Exception as e:
        print("Error getting splits:", e)

    # Check HR Zones
    try:
        # Time in zones might be a different endpoint
        # Some libraries map `get_activity_hr_in_timezones`
        zones = api.get_activity_hr_in_timezones(act_id)
        print("\n[HR Zones]:", json.dumps(zones, indent=2) if zones else "None")
    except Exception as e:
        print("Error getting HR zones:", e)

if __name__ == "__main__":
    debug_act()
