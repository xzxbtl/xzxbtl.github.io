from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, ForeignKey,
    UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


# ============================================================
# USER
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)

    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    balance: Mapped[float] = mapped_column(Integer, default=0)  # можно поменять на Float при желании
    admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Подписка
    subscription_lvl: Mapped[int] = mapped_column(Integer, default=0)
    subscription_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subscription_type_days: Mapped[int] = mapped_column(Integer, default=0)

    # Лимиты
    max_video_accounts: Mapped[int] = mapped_column(Integer, default=1)
    max_tg_accounts: Mapped[int] = mapped_column(Integer, default=2)

    # Связи
    tiktok_accounts: Mapped[List["TikTokAccount"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    youtube_accounts: Mapped[List["YouTubeAccount"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    video_templates: Mapped[List["VideoTemplate"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    tg_groups: Mapped[List["TgGroup"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    posts_templates: Mapped[List["PostsTemplate"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ============================================================
# TikTok ACCOUNT
# ============================================================

class TikTokAccount(Base):
    __tablename__ = "tiktok_accounts"

    __table_args__ = (
        UniqueConstraint("user_id", "account_id", name="uq_user_tiktok_account"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)

    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner: Mapped["User"] = relationship(back_populates="tiktok_accounts")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# YouTube ACCOUNT
# ============================================================

class YouTubeAccount(Base):
    __tablename__ = "youtube_accounts"

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_user_youtube_channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    channel_name: Mapped[str] = mapped_column(String(150), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)

    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner: Mapped["User"] = relationship(back_populates="youtube_accounts")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# VIDEO TEMPLATE
# ============================================================

class VideoTemplate(Base):
    __tablename__ = "video_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # tiktok | youtube | common

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    schedule_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_duet: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    visibility: Mapped[str] = mapped_column(String(50), default="public")

    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner: Mapped["User"] = relationship(back_populates="video_templates")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ============================================================
# TG GROUP
# ============================================================

class TgGroup(Base):
    __tablename__ = "tg_groups"

    __table_args__ = (
        UniqueConstraint("user_id", "tg_channel_id", name="uq_user_group"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tg_link: Mapped[str] = mapped_column(String(255), nullable=False)
    tg_channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner: Mapped["User"] = relationship(back_populates="tg_groups")

    posts: Mapped[List["PostsTemplate"]] = relationship(
        back_populates="tg_group", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# POSTS TEMPLATE
# ============================================================

class PostsTemplate(Base):
    __tablename__ = "posts_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)

    buttons_json: Mapped[dict] = mapped_column(JSON, default=dict)
    schedule_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    tg_group_id: Mapped[int] = mapped_column(
        ForeignKey("tg_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tg_group: Mapped["TgGroup"] = relationship(back_populates="posts")

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner: Mapped["User"] = relationship(back_populates="posts_templates")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
