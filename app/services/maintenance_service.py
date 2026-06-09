from datetime import datetime, timedelta

from sqlalchemy import delete

from app.config import get_settings
from app.database import SessionLocal
from app.models.scan_job import ScanJob


def cleanup_old_scan_jobs() -> None:
    settings = get_settings()
    cutoff = datetime.now() - timedelta(days=settings.scan_job_retention_days)
    with SessionLocal() as db:
        db.execute(
            delete(ScanJob).where(
                ScanJob.finished_at.is_not(None),
                ScanJob.finished_at < cutoff,
            )
        )
        db.commit()
