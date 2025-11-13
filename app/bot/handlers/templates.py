from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, WebAppInfo
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.bot.handlers.start import MainMenu

templates_router = Router(name="templates_router")


class TemplatesMenu:
    @staticmethod
    async def templates_choose_menu(type_call: CallbackQuery):
        user_id = type_call.from_user.id

        text = (
            f"🧩 *Меню шаблонов*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📁 Выберите тип шаблонов:\n\n"
            f"🎥 *Видео* — для TikTok / YouTube Shorts\n"
            f"💬 *Посты* — для Telegram-групп или каналов\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔙 Вернуться в главное меню — *Назад*"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🎥 Видео",
                web_app=WebAppInfo(url=f"https://xzxbtl.github.io/miniapp?mode=video&user_id={user_id}")
            ),
            InlineKeyboardButton(
                text="💬 Посты",
                web_app=WebAppInfo(url=f"https://xzxbtl.github.io/miniapp?mode=posts&user_id={user_id}")
            )
        )
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main_menu")
        )

        await type_call.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.MARKDOWN
        )
        await type_call.answer()


@templates_router.callback_query(F.data == "templates_menu")
async def templates_menu_callback(callback_query: CallbackQuery):
    await TemplatesMenu.templates_choose_menu(callback_query)


@templates_router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback_query: CallbackQuery):
    await MainMenu.send_main_menu(callback_query)