from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import RateLimitError
from app.models.usage import UsageEvent


class UsageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def check_and_record(self, db: Session, user_id: int | None, event_type: str) -> None:
        if user_id is None:
            return
        limit = (
            self.settings.max_analysis_per_day
            if event_type == "analysis"
            else self.settings.max_scan_per_day
        )
        start = datetime.combine(datetime.now().date(), time.min)
        used = db.scalar(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.user_id == user_id,
                UsageEvent.event_type == event_type,
                UsageEvent.created_at >= start,
            )
        )
        if (used or 0) >= limit:
            label = "analisa" if event_type == "analysis" else "scan"
            raise RateLimitError(f"Batas {label} harian Anda sudah tercapai ({limit} per hari).")
        db.add(UsageEvent(user_id=user_id, event_type=event_type))
        db.commit()

