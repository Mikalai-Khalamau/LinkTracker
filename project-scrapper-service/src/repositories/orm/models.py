from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY  # ← ВАЖНО: импортируем из postgresql
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class ChatORM(Base):
    __tablename__ = "chats"

    chat_id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    links = relationship(
        "LinkORM",
        secondary="chat_links",
        back_populates="chats",
        lazy="selectin",
    )

    __table_args__ = (Index("idx_chats_chat_id", "chat_id"),)


class LinkORM(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False, index=True)
    tags = Column(ARRAY(String), default=list, server_default="{}")
    filters = Column(ARRAY(String), default=list, server_default="{}")
    last_checked = Column(DateTime(timezone=True))
    last_updated = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    chats = relationship(
        "ChatORM",
        secondary="chat_links",
        back_populates="links",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_links_url", "url"),
        Index("idx_links_last_checked", "last_checked"),
        Index("idx_links_last_updated", "last_updated"),
    )


class ChatLinkORM(Base):
    __tablename__ = "chat_links"

    chat_id = Column(
        BigInteger,
        ForeignKey("chats.chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    link_id = Column(
        Integer,
        ForeignKey("links.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (
        Index("idx_chat_links_chat_id", "chat_id"),
        Index("idx_chat_links_link_id", "link_id"),
    )
