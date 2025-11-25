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
    balance: Mapped[float] = mapped_column(Integer, default=0)
    admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Подписка
    subscription_lvl: Mapped[int] = mapped_column(Integer, default=0)
    subscription_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subscription_type_days: Mapped[int] = mapped_column(Integer, default=0)

    # Лимиты на аккаунты
    max_video_accounts: Mapped[int] = mapped_column(Integer, default=0)
    max_tg_accounts: Mapped[int] = mapped_column(Integer, default=2)

    # Лимиты на шаблоны
    max_tg_templates: Mapped[int] = mapped_column(Integer, default=2)
    max_video_templates: Mapped[int] = mapped_column(Integer, default=2)

    # Связи
    tiktok_accounts: Mapped[List["TikTokAccount"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    # Аккаунты Ютуб + клиенты для видео

    youtube_accounts: Mapped[List["YouTubeAccount"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    youtube_projects: Mapped[List["YouTubeProject"]] = relationship(
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
        ForeignKey("users.user_id", ondelete="CASCADE"),
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
        ForeignKey("users.user_id", ondelete="CASCADE"),
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
    platform: Mapped[str] = mapped_column(String(20), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    schedule_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_duet: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    visibility: Mapped[str] = mapped_column(String(50), default="public")

    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
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
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner: Mapped["User"] = relationship(back_populates="tg_groups")

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
    schedule_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner: Mapped["User"] = relationship(back_populates="posts_templates")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class YouTubeProject(Base):
    __tablename__ = "youtube_projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    quota: Mapped[int] = mapped_column(Integer, default=10000)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active / blocked / used

    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="youtube_projects")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

