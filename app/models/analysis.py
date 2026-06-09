from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Analysis(TimestampMixin, Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    stock_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ai_result: Mapped[str] = mapped_column(Text, nullable=False)
    final_signal: Mapped[str | None] = mapped_column(String(50), index=True)
    confidence_level: Mapped[str | None] = mapped_column(String(20))

    user = relationship("User", back_populates="analyses")
