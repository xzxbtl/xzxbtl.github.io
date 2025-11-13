import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from datetime import datetime
from app.shared.database.core import setup_database, create_admin_user
from app.shared.logs.logg import logger
from app.bot.handlers import start
from app.bot.handlers import templates

load_dotenv(dotenv_path="bot_settings.env")
TOKEN = os.getenv("BOT_TOKEN")


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_routers(start.start_router, templates.templates_router)
    dp["started_at"] = datetime.now().strftime("%d-%m-%Y %H:%M")

    database_status = await setup_database()

    if not database_status:
        logger.error("Ошибка при создании таблиц")
        return

    try:
        await create_admin_user()
    except Exception as e:
        logger.error(f"Ошибка при создании админов на старте - {e}", exc_info=True)

    logger.info("Бот запущен и готов к работе!")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
