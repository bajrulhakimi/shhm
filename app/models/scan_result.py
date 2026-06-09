from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ScanResult(TimestampMixin, Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    group_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    final_signal: Mapped[str | None] = mapped_column(String(50), index=True)
    confidence_level: Mapped[str | None] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    structured_result: Mapped[dict | None] = mapped_column(JSON)

    user = relationship("User", back_populates="scan_results")
