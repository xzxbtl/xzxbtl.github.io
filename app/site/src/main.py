from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.site.src.api import main_router
from app.shared.database.core import setup_database, create_admin_user
from app.shared.logs.logg import logger
from fastapi.staticfiles import StaticFiles

from app.site.src.shared_path import STATIC_DIR


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.debug(msg="Создание таблиц базы данных...")
    try:
        db_status = await setup_database()
        if db_status:
            if await create_admin_user():
                logger.info(msg="Таблицы базы данных созданы.")
    except Exception as e:
        logger.error(msg=f"База данных не создалась {e}", exc_info=True)

    yield

app = FastAPI(lifespan=lifespan,
              title="FullSite FastAPI",
              description="""
              Полностью рабочий сайт, написанный на чистом JS и FastAPI.

              ### Основные технологии:
              - **Backend**: FastAPI
              - **База данных**: SQLAlchemy 3
              - **Кэширование**: Redis (async)
              - **Очереди сообщений**: RabbitMQ
              - **Frontend**: Чистый JavaScript

              ### Контакты автора:
              - **Автор проекта**: xzxbtl
              - **Telegram**: [qxzxbtlqq](https://t.me/qxzxbtlqq)
              """,
              version="1.0.0",
              contact={
                  "name": "xzxbtl",
                  "url": "https://github.com/xzxbtl",
              },
              license_info={
                  "name": "xxxBTL License",
              })


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(main_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)