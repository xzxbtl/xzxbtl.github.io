import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.shared.database.config import get_settings
from app.shared.database.models import Base, User, TgGroup
from app.shared.database.schemas import UserCreate
from app.shared.logs.logg import logger

if sys.platform.startswith('win') and os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

settings = get_settings()

async_engine = create_async_engine(settings.DataBase_URL_psycopg, echo=False, pool_size=20, max_overflow=50)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

ADMIN_IDS = [745409469]


def model_from_schema(schema_obj, model_cls):
    return model_cls(**schema_obj.dict(exclude_unset=True))


async def setup_database():
    async with async_engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            return True
        except Exception as e:
            logger.error(f"Database creation failed: {e}", exc_info=True)
    return logger.info("Base Table Created")


async def create_admin_user() -> bool:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.user_id == ADMIN_IDS[0]))
        existing_admin = res.scalar_one_or_none()

        if existing_admin:
            return True

        user_create = UserCreate(
            user_id=ADMIN_IDS[0],
            username="@qxzxbtlqq",
            balance=999999,
            admin=True,

            subscription_lvl=3,
            subscription_expires=datetime.utcnow() + timedelta(days=3650),
            subscription_type_days=9999,

            max_video_accounts=9999,
            max_tg_accounts=9999,

            max_tg_templates=9999,
            max_video_templates=9999,
        )

        try:
            user = model_from_schema(user_create, User)

            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info(f"✅ Создан администратор: {user.username}")
            return True

        except Exception as e:
            logger.error(f"Database creation failed: {e}", exc_info=True)
            return False


async def create_or_update_user(user_id: int, username: str = None, balance: int = 0, admin: bool = False) -> bool:
    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(select(User).where(User.user_id == user_id))
            existing_user = res.scalar_one_or_none()

            if existing_user:
                if username and existing_user.username != username:
                    existing_user.username = username
                    await session.commit()
                return True

            user_create = UserCreate(
                user_id=user_id,
                username=username,
                balance=balance,
                admin=admin
            )

            user = model_from_schema(user_create, User)

            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info(f"✅ Создан пользователь: {user.username} UserID: {user.user_id} Номер: {user.id}")
            return True

        except Exception as e:
            logger.error(f"User creation or updating failed: {e}", exc_info=True)
            return False


async def get_user(user_id: int):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.user_id == user_id))
        user = res.scalar_one_or_none()

        if user:
            return user

        else:
            return None


async def get_user_with_video_templates(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.tiktok_accounts),
                selectinload(User.youtube_accounts),
                selectinload(User.video_templates),
            )
            .where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_current_video_accounts_count(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.tiktok_accounts),
                selectinload(User.youtube_accounts)
            )
            .where(User.user_id == user_id)
        )

        user = result.scalar_one_or_none()
        if not user:
            return 0

        return len(user.tiktok_accounts) + len(user.youtube_accounts)


async def get_tg_groups_count(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.tg_groups))
            .where(User.user_id == user_id)
        )

        user = result.scalar_one_or_none()
        return len(user.tg_groups) if user else 0


async def get_user_with_posts_templates(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.tg_groups),
                selectinload(User.posts_templates)
            )
            .where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_current_max_videos_accounts(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.tiktok_accounts), selectinload(User.youtube_accounts))
            .where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"⚠️ Пользователь {user_id} не найден в базе")
            return 1

        tiktok_count = len(user.tiktok_accounts)
        youtube_count = len(user.youtube_accounts)
        total_accounts = tiktok_count + youtube_count

        available = max(user.max_video_accounts - total_accounts, 0)

        logger.info(
            f"👤 User {user_id} | TikTok: {tiktok_count}, YouTube: {youtube_count}, "
            f"Max: {user.max_video_accounts}, Available: {available}"
        )

        return available


async def get_current_max_posts_accounts(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.tg_groups))
            .where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"⚠️ Пользователь {user_id} не найден в базе")
            return 0

        tg_count = len(user.tg_groups)
        available = max(user.max_tg_accounts - tg_count, 0)

        logger.info(
            f"👤 User {user_id} | TG Groups: {tg_count}, Max: {user.max_tg_accounts}, Available: {available}"
        )

        return available


async def get_videos_accounts(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.tiktok_accounts),
                selectinload(User.youtube_accounts)
            )
            .where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.tiktok_accounts, user.youtube_accounts


async def check_tg_groups_exist(user_id: int, channel_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(TgGroup).where(
                TgGroup.user_id == user_id,
                TgGroup.tg_channel_id == channel_id
            )
        )
        existing_account = existing.scalar_one_or_none()

        if existing_account:
            return True
        return False


async def add_tg_group_db(schema_obj):
    async with AsyncSessionLocal() as session:
        try:
            session.add(schema_obj)
            await session.commit()
        except Exception as e:
            logger.exception(f"DB saving error: {e}")
            await session.rollback()
            raise RuntimeError(f"Ошибка сохранения TG-группы: {e}")

    return schema_obj


@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
