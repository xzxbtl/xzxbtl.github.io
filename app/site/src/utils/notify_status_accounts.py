import datetime
import httpx
import os
from typing import List, Dict
from enum import Enum
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.config.settings import get_youtube_settings
from app.shared.database.models import YouTubeAccount
from app.shared.logs.logg import logger


load_dotenv(dotenv_path="app/bot/bot_settings.env")
TOKEN = os.getenv('BOT_TOKEN')
youtube_settings = get_youtube_settings()


class NotifyStatusAccounts(str, Enum):
    SUCCESS = (
        "🎉 *Успешная привязка аккаунта!*\n\n"
        "Ваш YouTube аккаунт успешно подключён к системе 🎬\n"
        "Теперь вы можете загружать видео, управлять постами и использовать автопостинг."
    )

    CANCELED = (
        "❌ *Авторизация отменена*\n\n"
        "Вы отменили авторизацию или Google вернул ошибку.\n"
        "Попробуйте выполнить привязку ещё раз."
    )

    ERROR_TOKEN = (
        "⚠️ *Ошибка авторизации*\n\n"
        "Google не прислал код авторизации.\n"
        "Попробуйте пройти авторизацию заново."
    )

    SERVER_ERROR = (
        "🚨 *Ошибка сервера*\n\n"
        "При обработке авторизации произошла ошибка на сервере.\n"
        "Мы уже работаем над её устранением."
    )

    GOOGLE_ERROR = (
        "❌ *Ошибка Google OAuth*\n\n"
        "Google вернул ошибку при попытке авторизации.\n"
        "Пожалуйста, повторите попытку позже."
    )


def escape_md(text: str) -> str:
    to_escape = r"_*[]()~`>#+-=|{}.!"
    for ch in to_escape:
        text = text.replace(ch, f"\\{ch}")
    return text


async def notify_user(user_id: int, message: str):
    safe_text = escape_md(message)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": user_id,
                "text": safe_text,
                "parse_mode": "Markdown"
            }
        )
        if response.status_code != 200:
            logger.error(f"❌ Failed to send message to {user_id}: {response.text}")


async def get_youtube_channel_info(access_token: str):
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "snippet", "mine": "true"}
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, params=params, headers=headers)
        try:
            data = resp.json()
        except Exception as e:
            raise Exception(f"Ошибка разбора JSON: {e}, raw={resp.text}")

    if resp.status_code != 200:
        raise Exception(f"YouTube API вернул ошибку {resp.status_code}: {data}")

    if "items" not in data or not data["items"]:
        raise Exception(f"Каналы не найдены: {data}")

    channel = data["items"][0]
    channel_id = channel["id"]
    channel_name = channel["snippet"]["title"]

    return channel_id, channel_name


async def get_youtube_publish_tokens(user_id: int, session: AsyncSession) -> List[Dict]:
    """
    Обновляет access_token для всех YouTube аккаунтов пользователя (если нужно)
    и возвращает список данных, необходимых для публикации видео:
    [
      {
        "channel_id": str,
        "channel_name": str,
        "access_token": str,
        "refresh_token": str,
        "token_expiry": datetime | None,
        "needs_reauth": bool
      }, ...
    ]
    """
    result = await session.execute(
        select(YouTubeAccount).where(YouTubeAccount.user_id == user_id)
    )
    youtube_accounts = result.scalars().all()

    if not youtube_accounts:
        return []

    now = datetime.datetime.utcnow()
    channels_info: List[Dict] = []

    for account in youtube_accounts:
        needs_reauth = False
        updated = False

        need_refresh = (
            not account.token_expiry
            or account.token_expiry < now
            or not account.access_token
        )

        if need_refresh:
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": youtube_settings.client_id,
                "client_secret": youtube_settings.client_secret,
                "refresh_token": account.refresh_token,
                "grant_type": "refresh_token",
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(token_url, data=data)
                    resp.raise_for_status()
                    tokens = resp.json()

                access_token = tokens.get("access_token")
                expires_in = tokens.get("expires_in", 3600)

                if access_token:
                    account.access_token = access_token
                    account.token_expiry = now + datetime.timedelta(seconds=int(expires_in))
                    updated = True
                else:
                    logger.error(f"No access_token in token response for channel {account.channel_id}: {tokens}")
                    await notify_user(
                        user_id,
                        f"⚠️ Произошла ошибка при обновлении доступа к каналу *{account.channel_name}*.\n"
                        "Пожалуйста, попробуйте подключить канал снова."
                    )
                    needs_reauth = True

            except httpx.HTTPStatusError as e:
                body_text = e.response.text or ""
                try:
                    body_json = e.response.json()
                except Exception:
                    body_json = None

                logger.error(f"HTTP error refreshing token for channel {account.channel_id}: {e.response.status_code} {body_text}")


                err_str = str(body_json) if body_json else body_text

                if body_json and (body_json.get("error") == "invalid_grant" or "invalid_grant" in err_str):
                    await notify_user(
                        user_id,
                        f"⚠️ Не удалось автоматически обновить доступ к YouTube-каналу *{account.channel_name}*.\n"
                        "Похоже, требуется повторная авторизация. Пожалуйста, переподключите канал."
                    )

                    account.token_expiry = None
                    needs_reauth = True
                    updated = True

                elif body_json and (body_json.get("error") == "invalid_client" or "invalid_client" in err_str):
                    await notify_user(
                        user_id,
                        "❌ Сервис временно недоступен: ошибка конфигурации (invalid_client). Повторите попытку позже."
                    )
                else:
                    await notify_user(
                        user_id,
                        f"⚠️ При обновлении доступа к каналу *{account.channel_name}* Google вернул ошибку.\n"
                        "Скорее всего, повторная попытка решит проблему."
                    )

            except httpx.RequestError as e:
                logger.error(f"Network error refreshing token for channel {account.channel_id}: {e}")
                await notify_user(
                    user_id,
                    f"⚠️ Не удалось обновить доступ к каналу *{account.channel_name}* — проблемы с сетью.\n"
                    "Попробуйте снова через некоторое время."
                )

            except Exception as e:
                logger.exception(f"Unexpected error refreshing token for channel {account.channel_id}: {e}")
                await notify_user(
                    user_id,
                    f"⚠️ Произошла внутренняя ошибка при обновлении доступа к каналу *{account.channel_name}*.\n"
                    "Администратор уже оповещён."
                )

            if updated:
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    logger.exception(f"DB commit failed after token refresh for channel {account.channel_id}: {e}")
                    await session.rollback()

        channels_info.append({
            "channel_id": account.channel_id,
            "channel_name": account.channel_name,
            "access_token": account.access_token,
            "refresh_token": account.refresh_token,
            "token_expiry": account.token_expiry,
            "needs_reauth": needs_reauth
        })

    return channels_info