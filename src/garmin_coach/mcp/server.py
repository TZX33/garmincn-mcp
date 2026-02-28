import sys
from fastmcp import FastMCP
from garmin_coach.mcp.tools.garmin_health import garmin_service, mcp


def main():
    # 导入 local_mcp 工具，使其被加载
    import garmin_coach.mcp.tools.garmin_local

    # init garmincn service, login
    if not garmin_service.init_api():
        print("Garmin API initialization failed")
        sys.exit(1)
    print("Garmin API initialized successfully")

    mcp.run()


if __name__ == "__main__":
    main()
