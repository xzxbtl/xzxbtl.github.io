from fastapi import APIRouter
from app.site.src.api.pages.pages import router as pages_router
from app.site.src.api.posts_templates import router as posts_templates_router
from app.site.src.api.videos_templates import router as videos_templates_router
from app.site.src.api.auth.youtube import youtube_router

main_router = APIRouter()
main_router.include_router(pages_router)
main_router.include_router(posts_templates_router)
main_router.include_router(videos_templates_router)
main_router.include_router(youtube_router)
