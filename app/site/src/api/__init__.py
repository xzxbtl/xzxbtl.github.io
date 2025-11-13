from fastapi import APIRouter
from app.site.src.api.pages.pages import router as pages_router

main_router = APIRouter()
main_router.include_router(pages_router)
