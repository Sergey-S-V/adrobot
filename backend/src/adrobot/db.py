from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    keitaro_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(Text)


class Stream(Base):
    __tablename__ = "streams"
    __table_args__ = (Index("ix_streams_campaign_position", "campaign_id", "position"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id"))
    keitaro_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(Text)
    schema: Mapped[str] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer, default=0)


class StreamOffer(Base):
    __tablename__ = "stream_offers"
    __table_args__ = (
        UniqueConstraint("stream_id", "keitaro_offer_id", name="uq_stream_offer"),
        UniqueConstraint("stream_id", "allocation_order", name="uq_stream_order"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stream_id: Mapped[UUID] = mapped_column(ForeignKey("streams.id"), index=True)
    keitaro_offer_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(Text)
    base_state: Mapped[str | None] = mapped_column(String(32))
    draft_state: Mapped[str | None] = mapped_column(String(32))
    base_share: Mapped[int] = mapped_column(SmallInteger, default=0)
    draft_share: Mapped[int] = mapped_column(SmallInteger, default=0)
    base_pin_share: Mapped[int | None] = mapped_column(SmallInteger)
    draft_pin_share: Mapped[int | None] = mapped_column(SmallInteger)
    ever_published: Mapped[bool] = mapped_column(default=False)
    allocation_order: Mapped[int] = mapped_column(BigInteger)


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, pool_pre_ping=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def close(self) -> None:
        self.engine.dispose()
