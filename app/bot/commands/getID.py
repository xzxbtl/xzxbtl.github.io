import html
from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters.command import Command
from aiogram.enums.parse_mode import ParseMode


commands_router = Router(name="commands_router")


@commands_router.message(Command("getid"))
async def get_chat_info(message: Message, bot: Bot):
    chat = message.chat
    title = html.escape(chat.title or "Личный чат")
    chat_id = chat.id
    username = getattr(chat, "username", None)
    link = f"https://t.me/{username}" if username else "—"

    text = (
        f"📋 <b>Информация о чате</b>\n\n"
        f"🏷 <b>Название:</b> {title}\n"
        f"🔗 <b>Ссылка:</b> {html.escape(link)}\n"
        f"🆔 <b>ID чата:</b> <code>{chat_id}</code>"
    )

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML
    )


@commands_router.channel_post(Command("getid"))
async def get_channel_info(channel_post: Message, bot: Bot):
    chat = channel_post.chat
    title = html.escape(chat.title or "Канал")
    chat_id = chat.id
    username = getattr(chat, "username", None)
    link = f"https://t.me/{username}" if username else "—"

    text = (
        f"📢 <b>Информация о канале</b>\n\n"
        f"🏷 <b>Название:</b> {title}\n"
        f"🔗 <b>Ссылка:</b> {html.escape(link)}\n"
        f"🆔 <b>ID канала:</b> <code>{chat_id}</code>"
    )

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML
    )