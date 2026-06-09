import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import AppError
from app.models.stock import StockGroup, StockGroupItem


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
