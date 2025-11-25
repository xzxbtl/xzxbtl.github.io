from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.site.src.api import main_router
from app.shared.database.core import setup_database, create_admin_user
from app.shared.logs.logg import logger
from fastapi.staticfiles import StaticFiles
from app.site.src.shared_path import STATIC_DIR
from app.shared.broker.broker_service import broker


rabbit_broker = broker


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("🚀 Запуск сервера FASTAPI. Инициализация сервисов...")

    logger.debug("🛠 Начало создания таблиц базы данных...")

    try:
        db_status = await setup_database()

        if db_status:
            logger.success("📦 Таблицы базы данных успешно созданы.")

            logger.debug("👤 Попытка создать администратора...")
            admin_created = await create_admin_user()

            if admin_created:
                logger.success("✅ Администратор успешно создан.")
            else:
                logger.warning("⚠ Администратор НЕ был создан (возможно, уже существует).")

            try:
                try:
                    await rabbit_broker.connect()
                    logger.info("🔌 Соединение с RabbitMQ установлено.")
                except Exception as e:
                    logger.error(f"❌ Не удалось подключиться к RabbitMQ: {e}")

                try:
                    await rabbit_broker.publish(
                        "🔥 FASTAPI сервер запущен\n📂 Все таблицы БД инициализированы\n🔐 Администратор создан\n",
                        queue="logs_messages",
                    )
                    logger.info("📨 Сообщение об успешном запуске отправлено в очередь RabbitMQ.")
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке сообщения в RabbitMQ: {e}")

            except Exception as rb_err:
                logger.error(f"❌ Ошибка при отправке сообщения в RabbitMQ: {rb_err}")

        else:
            logger.error("❌ Ошибка: setup_database() вернул отрицательный статус.")

    except Exception as e:
        logger.critical(f"💥 Критическая ошибка при инициализации базы данных: {e}", exc_info=True)

    finally:
        logger.info("🧹 Завершение этапа инициализации. Переход к запуску сервера.")

    yield

    logger.info("🛑 Завершение работы сервера FASTAPI.")

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