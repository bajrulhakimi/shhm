import json
import logging
from functools import lru_cache
from pathlib import Path

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.database import SessionLocal
from app.exceptions import AppError, ExternalServiceError, RetryableExternalError
from app.models.stock import StockGroup, StockGroupItem

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _load_groups(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


class GroupService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def load_groups(self) -> dict[str, dict]:
        return _load_groups(self.settings.stock_groups_file)

    def get_codes(self, group_name: str) -> list[str]:
        groups = self.load_groups()
        key = group_name.upper()
        if key == "ALL":
            return sorted({code for group in groups.values() for code in group["stocks"]})
        if key not in groups:
            raise AppError(f"Grup saham {group_name} tidak ditemukan.")
        return groups[key]["stocks"]

    def find_groups_for_stock(self, code: str) -> list[str]:
        return [name for name, group in self.load_groups().items() if code in group["stocks"]]

    def seed_database(self, db: Session) -> None:
        groups = self.load_groups()
        for name, payload in groups.items():
            group = db.scalar(select(StockGroup).where(StockGroup.name == name))
            if not group:
                group = StockGroup(name=name, description=payload.get("description"))
                db.add(group)
                db.flush()
            else:
                group.description = payload.get("description")
                db.execute(delete(StockGroupItem).where(StockGroupItem.stock_group_id == group.id))
            for code in payload["stocks"]:
                db.add(StockGroupItem(stock_group_id=group.id, stock_code=code))
        db.commit()

    async def sync_remote_groups(self) -> bool:
        if not self.settings.stock_groups_remote_url:
            return False
        retrying = AsyncRetrying(
            retry=retry_if_exception_type(RetryableExternalError),
            stop=stop_after_attempt(self.settings.external_request_max_attempts),
            wait=wait_exponential(
                multiplier=self.settings.external_request_backoff_seconds,
                max=30,
            ),
            reraise=True,
        )
        try:
            async for attempt in retrying:
                with attempt:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.get(self.settings.stock_groups_remote_url)
                    if response.status_code == 429 or response.status_code >= 500:
                        raise RetryableExternalError("Sumber grup saham sementara tidak tersedia.")
                    response.raise_for_status()
                    groups = response.json()
        except (httpx.HTTPError, ValueError, RetryableExternalError) as exc:
            raise ExternalServiceError("Grup saham remote belum berhasil disinkronkan.") from exc
        self._validate_groups(groups)
        temporary = self.settings.stock_groups_file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(groups, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.settings.stock_groups_file)
        _load_groups.cache_clear()
        with SessionLocal() as db:
            self.seed_database(db)
        logger.info("Stock groups synchronized from remote source")
        return True

    @staticmethod
    def _validate_groups(groups: dict) -> None:
        if not isinstance(groups, dict) or not groups:
            raise ValueError("Data grup saham remote harus berupa object yang tidak kosong.")
        for name, payload in groups.items():
            stocks = payload.get("stocks") if isinstance(payload, dict) else None
            if not name or not isinstance(stocks, list) or not stocks:
                raise ValueError(f"Grup {name!r} tidak valid.")
            if any(not isinstance(code, str) or not code.isalnum() for code in stocks):
                raise ValueError(f"Kode saham pada grup {name} tidak valid.")
