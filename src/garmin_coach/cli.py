import argparse
import sys
from garmin_coach.sync.sync_engine import SyncEngine
from garmin_coach.mcp.server import main as mcp_main


def main():
    parser = argparse.ArgumentParser(
        description="Garmin Coach 统一命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  garmin-coach sync                    # 增量同步数据
  garmin-coach sync --full             # 全量同步数据
  garmin-coach stats                   # 查看本地数据库统计
  garmin-coach serve                   # 启动 MCP 服务器
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="同步 Garmin 数据到本地数据库")
    sync_parser.add_argument(
        "--full", action="store_true", help="全量同步（首次使用时推荐）"
    )
    sync_parser.add_argument(
        "--days", type=int, default=365, help="全量同步时回溯的天数 (默认: 365)"
    )
    sync_parser.add_argument(
        "--activities", type=int, default=500, help="全量同步时最大活动数量 (默认: 500)"
    )
    sync_parser.add_argument(
        "--from", dest="from_date", type=str, help="开始日期 (YYYY-MM-DD)"
    )
    sync_parser.add_argument(
        "--to", dest="to_date", type=str, help="结束日期 (YYYY-MM-DD)"
    )
    sync_parser.add_argument(
        "--force-refresh", action="store_true", help="强制刷新已存在的数据"
    )
    sync_parser.add_argument("--quiet", action="store_true", help="减少输出")

    # Stats command
    subparsers.add_parser("stats", help="显示数据库统计信息")

    # Serve command
    subparsers.add_parser("serve", help="启动 FastMCP 服务器")

    args = parser.parse_args()

    if args.command == "serve":
        mcp_main()
    elif args.command == "stats":
        engine = SyncEngine(verbose=True)
        engine.db.print_stats()
    elif args.command == "sync":
        engine = SyncEngine(verbose=not args.quiet)

        if args.from_date:
            from datetime import datetime

            end_date = args.to_date or datetime.now().strftime("%Y-%m-%d")
            engine.sync_date_range(
                args.from_date, end_date, force_refresh=args.force_refresh
            )
        elif args.full:
            engine.sync_full(activity_limit=args.activities, days_back=args.days)
        else:
            engine.sync_incremental()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
