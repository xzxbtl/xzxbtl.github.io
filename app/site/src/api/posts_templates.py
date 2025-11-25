from fastapi import APIRouter, Request, Response, HTTPException
from typing import List
from fastapi.params import Query
from sqlalchemy import select
from app.shared.database.core import get_user
from app.shared.database.models import PostsTemplate
from app.shared.database.schemas import PostsTemplateCreate, PostsTemplateRead
from app.shared.logs.logg import logger
from app.site.src.api.dependensis import SessionDeep
from fastapi.responses import JSONResponse
from app.site.src.utils.ratelimit import rate_limit

router = APIRouter(prefix="/api/posts", tags=["Posts Templates"])


@rate_limit(max_calls=6, time_frame=10)
@router.get("", response_model=List[PostsTemplateRead], status_code=200)
async def get_post_templates(
        session: SessionDeep,
        user_id: int = Query(...),
):
    """
    Получаем список пост-шаблонов пользователя.
    JS: GET /api/posts?user_id=USER_ID
    """
    res = await session.execute(
        select(PostsTemplate)
        .where(PostsTemplate.user_id == user_id)
        .order_by(PostsTemplate.created_at.desc())
    )
    return res.scalars().all()


@rate_limit(max_calls=2, time_frame=10)
@router.post("", response_model=PostsTemplateRead, status_code=201)
async def create_tg_posts(
        payload: PostsTemplateCreate,
        session: SessionDeep,
):
    """Создание текстового шаблона"""

    user = await get_user(
        user_id=payload.user_id
    )

    if not user:
        msg = "Мы не нашли ваш профиль, попробуйте написать /start в боте"
        raise HTTPException(status_code=404, detail=msg)

    if user.max_tg_templates <= 0:
        msg = "По вашему тарифу закончились тг-шаблоны"
        raise HTTPException(status_code=403, detail=msg)

    media_url = payload.image_url
    media_type = "photo" if media_url else "text"

    try:
        new_post = PostsTemplate(
            title=payload.title,
            text=payload.text,
            media_url=media_url,
            media_type=media_type,
            buttons_json=payload.buttons_json or {},
            schedule_time=payload.schedule_time,
            user_id=user.user_id,
        )

        session.add(new_post)
        await session.commit()
        await session.refresh(new_post)
        return new_post

    except Exception as e:
        logger.error(
            f"Ошибка при создании пост-шаблона для пользователя {user.user_id}",
            exc_info=e,
        )
        await session.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при сохранении шаблона")


@rate_limit(max_calls=6, time_frame=10)
@router.put("/{template_id}", response_model=PostsTemplateRead, status_code=200)
async def edit_post_template(
        template_id: int,
        payload: PostsTemplateCreate,
        session: SessionDeep,
):
    """
    Обновление пост-шаблона.
    JS: PUT /api/posts/{id}?user_id=USER_ID
    """

    res = await session.execute(
        select(PostsTemplate).where(PostsTemplate.id == template_id)
    )
    post_template = res.scalar_one_or_none()

    if not post_template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    if post_template.user_id != payload.user_id:
        raise HTTPException(status_code=403, detail="Вы не владелец этого шаблона")

    try:
        update_data = payload.dict(exclude_unset=True)

        if "image_url" in update_data:
            media_url = update_data.pop("image_url")
            post_template.media_url = media_url
            post_template.media_type = "photo" if media_url else "text"

        for field, value in update_data.items():
            if hasattr(post_template, field):
                setattr(post_template, field, value)

        await session.commit()
        await session.refresh(post_template)
        return post_template

    except Exception as e:
        logger.error(
            msg=f"Ошибка при изменении пост-шаблона id={template_id} - {e}",
            exc_info=True,
        )
        await session.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при изменении шаблона")


@router.delete("/{template_id}")
async def delete_post_template(
        template_id: int,
        session: SessionDeep,
        user_id: int = Query(...),
):
    """
    Удаление пост-шаблона.
    JS: DELETE /api/posts/{id}?user_id=USER_ID
    """

    res = await session.execute(
        select(PostsTemplate).where(PostsTemplate.id == template_id)
    )
    post_template = res.scalar_one_or_none()

    if not post_template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    if post_template.user_id != user_id:
        raise HTTPException(status_code=403, detail="Вы не владелец этого шаблона")

    try:
        await session.delete(post_template)
        await session.commit()
        return JSONResponse({"status": "deleted", "id": template_id})

    except Exception as e:
        logger.error(
            msg=f"Ошибка при удалении пост-шаблона id={template_id} - {e}",
            exc_info=True,
        )
        await session.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при удалении шаблона")
