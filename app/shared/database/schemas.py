from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field


# ======================================================
# USER
# ======================================================

class UserBase(BaseModel):
    user_id: int = Field(..., title="User ID")
    username: str = Field("Инкогнито", title="Username")
    balance: float = Field(0, title="Balance")
    admin: bool = Field(False, title="Admin")

    subscription_lvl: int = Field(0, title="Subscription Level")
    subscription_expires: Optional[datetime] = Field(None, title="Subscription Expiry")
    subscription_type_days: int = Field(0, title="Subscription Period (days)")

    max_video_accounts: int = Field(1, title="Max Video Accounts")
    max_tg_accounts: int = Field(2, title="Max TG Groups")


class UserCreate(UserBase):
    id: Optional[int] = Field(None, ge=1)


# ======================================================
# ACCOUNTS
# ======================================================

class TikTokBase(BaseModel):
    account_name: str
    account_id: str
    access_token: str
    refresh_token: str
    token_expiry: Optional[str] = None


class TikTokCreate(TikTokBase):
    id: Optional[int] = None
    user_id: int


class YouTubeBase(BaseModel):
    channel_name: str
    channel_id: str
    access_token: str
    refresh_token: str
    token_expiry: Optional[str] = None


class YouTubeCreate(YouTubeBase):
    id: Optional[int] = None
    user_id: int


# ======================================================
# VIDEO TEMPLATE BASE
# ======================================================

class TemplateBase(BaseModel):
    title: str = Field(..., title="Video Title")
    description: str = Field(..., title="Description")
    tags: List[str] = Field(default_factory=list, title="Tags")
    language: str = Field("ru", title="Language")
    schedule_time: Optional[datetime] = Field(None, title="Schedule Time")
    allow_comments: bool = Field(True, title="Allow Comments")
    allow_duet: bool = Field(True, title="Allow Duet/Remix")
    visibility: str = Field("public", title="Visibility")

    # Все доп. поля ТИКТОК/ЮТУБ складываются сюда
    extra: Dict[str, Any] = Field(default_factory=dict)


class TemplateCreate(TemplateBase):
    id: Optional[int] = None
    platform: Literal["tiktok", "youtube", "common"]
    user_id: int


# ======================================================
# TIKTOK TEMPLATE (расширенная версия)
# ======================================================

class TikTokTemplate(TemplateBase):
    sound_id: Optional[str] = Field(None, title="Sound ID")
    cover_time: Optional[float] = Field(None, title="Cover Time (sec)")
    enable_auto_captions: bool = Field(True, title="Auto Captions")
    category: Optional[str] = Field(None, title="Category")

    def assemble_extra(self):
        return {
            "sound_id": self.sound_id,
            "cover_time": self.cover_time,
            "enable_auto_captions": self.enable_auto_captions,
            "category": self.category
        }


class TikTokTemplateCreate(TikTokTemplate):
    id: Optional[int] = None
    user_id: Optional[int] = None


# ======================================================
# YOUTUBE TEMPLATE (расширенная версия)
# ======================================================

class YouTubeTemplate(TemplateBase):
    category_id: Optional[int] = Field(22, title="YouTube Category ID")
    privacy_status: str = Field("public", title="Privacy Status")
    made_for_kids: bool = Field(False, title="Made For Kids")
    license: str = Field("youtube", title="License")
    allow_embedding: bool = Field(True, title="Allow Embedding")
    publish_as_short: bool = Field(True, title="Publish as Short")

    def assemble_extra(self):
        return {
            "category_id": self.category_id,
            "privacy_status": self.privacy_status,
            "made_for_kids": self.made_for_kids,
            "license": self.license,
            "allow_embedding": self.allow_embedding,
            "publish_as_short": self.publish_as_short
        }


class YoutubeTemplateCreate(YouTubeTemplate):
    id: Optional[int] = None
    user_id: Optional[int] = None


# ======================================================
# TG GROUP
# ======================================================

class TgGroup(BaseModel):
    tg_link: str
    tg_channel_id: str
    title: Optional[str] = None


class TgGroupCreate(TgGroup):
    id: Optional[int] = None


# ======================================================
# TG POST TEMPLATE
# ======================================================

class PostsTemplateBase(BaseModel):
    title: str
    text: str
    image_url: Optional[str] = None
    buttons_json: Optional[dict] = None
    schedule_time: Optional[datetime] = None
    tg_group_id: int


class PostsTemplateCreate(PostsTemplateBase):
    id: Optional[int] = None
