import httpx
import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.shared.config.settings import get_youtube_settings
from app.shared.database.models import YouTubeAccount
from app.shared.database.schemas import YouTubeCreate
from app.shared.logs.logg import logger
from app.site.src.api.dependensis import SessionDeep
from app.site.src.utils.notify_status_accounts import notify_user, NotifyStatusAccounts, get_youtube_channel_info
from app.shared.database.core import model_from_schema

youtube_router = APIRouter(tags=["OAuth"])
youtube_settings = get_youtube_settings()


@youtube_router.get("/youtube/callback")
async def youtube_add_account_callback(
        request: Request,
        session: SessionDeep
):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    try:
        state = int(state)
    except Exception:
        logger.error("Invalid 'state' param in callback")
        return JSONResponse(
            {"error": "Некорректный параметр state"},
            status_code=400
        )

    # ----------- Ошибка, полученная от Google ----------
    if error:
        msg = NotifyStatusAccounts.CANCELED.value
        logger.warning(f"YouTube OAuth canceled by user. TG_ID={state}")
        await notify_user(state, msg)

        return JSONResponse(
            {"error": msg},
            status_code=400
        )

    # ----------- Нет кода авторизации ----------
    if not code:
        msg = NotifyStatusAccounts.ERROR_TOKEN.value
        logger.error(f"YouTube OAuth returned no code. TG_ID={state}")
        await notify_user(state, msg)

        return JSONResponse(
            {"error": msg},
            status_code=400
        )

    # ---------- Обмен кода на токены ----------
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": f"{youtube_settings.client_id}",
        "client_secret": f"{youtube_settings.client_secret}",
        "redirect_uri": f"{youtube_settings.redirect_uri}",
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            google_response = await client.post(token_url, data=data)
            tokens = google_response.json()
            logger.info(f"Tokens received: {tokens}")

    except Exception as e:
        msg = NotifyStatusAccounts.SERVER_ERROR.value
        logger.exception(f"Google token exchange FAILED. TG_ID={state}, error={e}")
        await notify_user(state, msg)

        return JSONResponse(
            {"error": msg},
            status_code=500
        )

    # ---------- Google вернул ошибку ----------
    if "error" in tokens:
        msg = NotifyStatusAccounts.GOOGLE_ERROR.value
        logger.error(f"Google OAuth error TG_ID={state}: {tokens}")
        await notify_user(state, msg)

        return JSONResponse(
            {"error": msg},
            status_code=400
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)

    expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

    try:
        channel_id, channel_name = await get_youtube_channel_info(access_token)
    except Exception as err:
        msg = f"❌ Не удалось получить данные канала: {err}"
        logger.exception(f"Failed to load YouTube channel info. TG_ID={state}. Error={err}")
        await notify_user(state, msg)

        return JSONResponse({"error": msg}, status_code=400)

    # ---------- Формируем pydantic-схему ----------
    youtube_account_schema = YouTubeCreate(
        channel_name=channel_name,
        channel_id=channel_id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=expires_at,
        user_id=state
    )

    # ---------- Проверяем, есть ли уже этот канал у пользователя ----------
    existing = await session.execute(
        select(YouTubeAccount).where(
            YouTubeAccount.user_id == state,
            YouTubeAccount.channel_id == channel_id
        )
    )
    existing_account = existing.scalar_one_or_none()

    if existing_account:
        msg = (
            "⚠️ *Этот YouTube-канал уже привязан*\n\n"
            f"Канал: *{channel_name}*\n"
            f"ID: `{channel_id}`\n\n"
            "Вы не можете добавить один и тот же канал дважды."
        )
        logger.warning(f"Duplicate YT channel bind attempt. TG_ID={state}, channel_id={channel_id}")

        await notify_user(state, msg)

        return JSONResponse(
            {"error": "Этот канал уже привязан ранее."},
            status_code=409
        )
    try:
        youtube_account_model = model_from_schema(
            schema_obj=youtube_account_schema,
            model_cls=YouTubeAccount
        )
    except Exception as e:
        msg = f"❌ Ошибка конвертации данных: {e}"
        logger.exception(f"Model conversion failed. TG_ID={state}, error={e}")

        await notify_user(state, msg)
        return JSONResponse({"error": msg}, status_code=500)

    try:
        session.add(youtube_account_model)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()

        msg = f"❌ Ошибка сохранения в базе данных:\n`{str(e)}`"
        logger.exception(f"DB commit failed. TG_ID={state}, error={e}")

        await notify_user(state, msg)

        return JSONResponse(
            {"error": "Ошибка сохранения в базе данных."},
            status_code=500
        )

    # ---------- УСПЕШНО ----------
    success_msg = (
        "🎉 *YouTube аккаунт успешно привязан!*\n\n"
        f"Канал: *{channel_name}*\n"
        f"ID: `{channel_id}`\n\n"
        "Теперь вы можете загружать видео 🎬"
    )

    logger.info(f"YouTube account linked: TG_ID={state}, channel_id={channel_id}")

    await notify_user(state, success_msg)

    return JSONResponse(
        {
            "status": "success",
            "message": "YouTube аккаунт успешно привязан",
            "channel_name": channel_name,
            "channel_id": channel_id
        }
    )


