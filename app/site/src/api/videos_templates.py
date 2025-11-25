from fastapi import APIRouter, HTTPException
from typing import List
from fastapi.params import Query
from sqlalchemy import select
from app.shared.database.core import get_user
from app.shared.database.models import VideoTemplate
from app.shared.database.schemas import TemplateCreate, TikTokTemplate, YouTubeTemplate, VideoTemplateRead
from app.shared.logs.logg import logger
from app.site.src.api.dependensis import SessionDeep
from fastapi.responses import JSONResponse
from app.site.src.utils.ratelimit import rate_limit

router = APIRouter(prefix="/api/video", tags=["Video Templates"])


@rate_limit(max_calls=6, time_frame=10)
@router.get("", response_model=List[VideoTemplateRead], status_code=200)
async def get_video_templates(
        session: SessionDeep,
        user_id: int = Query(...),
):
    """Получаем список объектов Видео Шаблонов"""

    res = await session.execute(
        select(VideoTemplate).where(
            VideoTemplate.user_id == user_id
        ).order_by(VideoTemplate.created_at.desc())
    )

    return res.scalars().all()


@rate_limit(max_calls=2, time_frame=10)
@router.post("", response_model=VideoTemplateRead, status_code=201)
async def create_video_template(
        payload: TemplateCreate,
        session: SessionDeep,
):
    """Создание Видео Шаблона + Сохранеие в json доп.панель с Валидацией их"""

    user = await get_user(
        user_id=payload.user_id
    )

    if not user:
        msg = "Мы не нашли ваш профиль, попробуйте написать /start в боте"
        raise HTTPException(status_code=404, detail=msg)

    if user.max_video_templates <= 0:
        msg = "По вашему тарифу закончились видео-шаблоны"
        raise HTTPException(status_code=403, detail=msg)

    extra_data = payload.extra or {}

    if payload.platform == "tiktok":
        validated = TikTokTemplate(**extra_data)
        extra_final = validated.assemble_extra()

    elif payload.platform == "youtube":
        validated = YouTubeTemplate(**extra_data)
        extra_final = validated.assemble_extra()

    else:
        extra_final = extra_data

    try:
        new_video_template = VideoTemplate(
            user_id=payload.user_id,
            platform=payload.platform,
            title=payload.title,
            description=payload.description,
            tags=payload.tags,
            language=payload.language,
            schedule_time=payload.schedule_time,
            allow_comments=payload.allow_comments,
            allow_duet=payload.allow_duet,
            visibility=payload.visibility,
            extra=extra_final,
        )

        session.add(new_video_template)
        await session.commit()
        await session.refresh(new_video_template)
        return new_video_template

    except Exception as e:
        logger.error(f"Ошибка при создании видео поста для пользователя - {payload.user_id}", exc_info=e)
        await session.rollback()

        msg = "Ошибка при сохранении шаблона"
        raise HTTPException(status_code=500, detail=msg)


@rate_limit(max_calls=6, time_frame=10)
@router.put("/{video_template_id}", response_model=VideoTemplateRead, status_code=200)
async def edit_video_template(
        video_template_id: int,
        payload: TemplateCreate,
        session: SessionDeep
):
    res = await session.execute(
        select(VideoTemplate).where(VideoTemplate.id == video_template_id)
    )

    video_template = res.scalar_one_or_none()

    if not video_template:
        raise HTTPException(status_code=404, detail="Не найден шаблон")

    if video_template.user_id != payload.user_id:
        raise HTTPException(403, detail="Вы не владелец этого шаблона")

    try:
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(video_template, field, value)

        await session.commit()
        await session.refresh(video_template)

        return video_template

    except Exception as e:
        logger.error(msg=f"Ошибка при изменении шаблона - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при изменении шаблона")


@router.delete("/{video_template_id}")
async def delete_video_template(
        video_template_id: int,
        session: SessionDeep,
        user_id: int = Query(...),
):
    res = await session.execute(
        select(VideoTemplate).where(VideoTemplate.id == video_template_id)
    )

    video_template = res.scalar_one_or_none()

    if not video_template:
        raise HTTPException(status_code=404, detail="Не найден шаблон")

    if video_template.user_id != user_id:
        raise HTTPException(403, detail="Вы не владелец этого шаблона")

    try:
        await session.delete(video_template)
        await session.commit()
        return JSONResponse({"status": "deleted", "id": video_template_id})

    except Exception as e:
        logger.error(msg=f"Ошибка при удалении шаблона - {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(status_code=500, detail="Не найден шаблон")

