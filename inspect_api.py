
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server_garmincn.service.garmincn_service import GarminService

def inspect_garmin():
    garmin_service = GarminService()
    if garmin_service.init_api():
        print("Login successful")
        print("Methods in garmin object:")
        print(dir(garmin_service.garminapi))
    else:
        print("Login failed")

if __name__ == "__main__":
    inspect_garmin()
