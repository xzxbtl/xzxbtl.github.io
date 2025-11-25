import os
import asyncio

from aiogram.enums import ParseMode
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from datetime import datetime

from app.shared.broker.broker_service import broker
from app.shared.database.core import setup_database, create_admin_user
from app.shared.logs.logg import logger
from app.bot.handlers import start, templates, postmanager, accounts
from app.bot.commands import getID

load_dotenv(dotenv_path="bot_settings.env")
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

CHAT_LOG_ID = "-1003402496090"


@broker.subscriber("logs_messages")
async def handle_log_messages(message: str):
    await bot.send_message(
        chat_id=CHAT_LOG_ID,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def main():
    logger.info("🤖 Запуск Telegram-бота. Инициализация сервисов...")
    dp = Dispatcher()
    dp.include_routers(start.start_router, templates.templates_router,
                       postmanager.posting_router, accounts.account_router,
                       getID.commands_router)
    dp["started_at"] = datetime.now().strftime("%d-%m-%Y %H:%M")
    logger.debug(f"🕒 Время запуска бота: {dp['started_at']}")

    logger.info("📦 Проверка и создание таблиц базы данных...")
    database_status = await setup_database()

    if not database_status:
        logger.critical("❌ Критическая ошибка: таблицы БД не были созданы.")
        return
    else:
        logger.success("📁 Таблицы базы данных успешно созданы.")

    logger.debug("👤 Попытка создать администратора по умолчанию...")
    try:
        admin_created = await create_admin_user()
        if admin_created:
            logger.success("🔐 Администратор успешно создан.")
        else:
            logger.warning("⚠ Администратор уже существует — пропускаю создание.")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании администратора: {e}", exc_info=True)

    logger.info("🚀 Бот запущен и готов к работе! Начинаю polling...")

    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка polling: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("🛑 Соединение с Telegram закрыто.")


if __name__ == "__main__":
    asyncio.run(main())
