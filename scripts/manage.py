import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.group_service import GroupService


async def main() -> None:
    parser = argparse.ArgumentParser(description="AI Stock Analyzer maintenance commands")
    parser.add_argument("command", choices=["validate-groups", "sync-groups"])
    args = parser.parse_args()
    service = GroupService()
    if args.command == "validate-groups":
        groups = service.load_groups()
        service._validate_groups(groups)
        print(json.dumps({name: len(data["stocks"]) for name, data in groups.items()}, indent=2))
    elif not await service.sync_remote_groups():
        raise SystemExit("STOCK_GROUPS_REMOTE_URL belum dikonfigurasi.")


if __name__ == "__main__":
    asyncio.run(main())
