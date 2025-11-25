from fastapi import APIRouter, Request
from fastapi.params import Query
from fastapi.responses import HTMLResponse
from app.site.src.shared_path import templates

router = APIRouter(tags=["FrontEnd 🌐"])


@router.get("/miniapp", response_class=HTMLResponse)
async def miniapp_home(
        request: Request,
        mode: str = Query("video", regex="^(video|posts)$"),
        user_id: int = Query(...)
):
    if mode == "video":
        return templates.TemplateResponse(
            "video_templates.html",
            {"request": request, "user_id": user_id}
        )

    elif mode == "posts":
        return templates.TemplateResponse(
            "posts_templates.html",
            {"request": request, "user_id": user_id}
        )


@router.get("/error", response_class=HTMLResponse)
async def error_page(request: Request, msg: str = "Неизвестная ошибка"):
    return templates.TemplateResponse(
        "errors.html",
        {"request": request, "message": msg}
    )
