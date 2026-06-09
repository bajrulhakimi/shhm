from sqlalchemy import BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Stock(TimestampMixin, Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(255))
    market_cap: Mapped[int | None] = mapped_column(BigInteger)


class StockGroup(TimestampMixin, Base):
    __tablename__ = "stock_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    items = relationship("StockGroupItem", back_populates="group", cascade="all, delete-orphan")


class StockGroupItem(TimestampMixin, Base):
    __tablename__ = "stock_group_items"
    __table_args__ = (UniqueConstraint("stock_group_id", "stock_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_group_id: Mapped[int] = mapped_column(ForeignKey("stock_groups.id", ondelete="CASCADE"))
    stock_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    group = relationship("StockGroup", back_populates="items")

