import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.services.group_service import GroupService
from app.services.maintenance_service import cleanup_old_scan_jobs

logger = logging.getLogger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="Asia/Jakarta")
    scheduler.add_job(
        cleanup_old_scan_jobs,
        "cron",
        hour=3,
        minute=20,
        id="cleanup-old-scan-jobs",
        replace_existing=True,
    )
    if settings.enable_scheduled_group_sync and settings.stock_groups_remote_url:
        scheduler.add_job(
            GroupService().sync_remote_groups,
            "cron",
            hour=3,
            minute=0,
            id="sync-stock-groups",
            replace_existing=True,
        )
    return scheduler
