from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from typing import Union

from app.shared.database.core import get_user, create_or_update_user, get_current_max_videos_accounts, \
    get_current_max_posts_accounts
from app.shared.logs.logg import logger
from app.bot.utils.formatter_menu import formatted_status, formatted_time_sub

start_router = Router(name="StartRouter")


class MainMenu:
    @staticmethod
    async def send_main_menu(type_call: Union[Message, CallbackQuery]):
        user_id = type_call.from_user.id
        username = type_call.from_user.username

        if isinstance(type_call, CallbackQuery):
            send_func = type_call.message.edit_text
        else:
            send_func = type_call.answer

        user = await get_user(user_id)

        if not user:
            logger.warning(f"⚠️ Пользователь {username} не найден в базе")
            return await send_func("Ошибка: пользователь не найден. Попробуй снова позже.")

        user_admin = user.admin
        user_sub_lvl = user.subscription_lvl
        user_sub_expire = user.subscription_expires
        user_balance = user.balance
        user_max_video_accounts = await get_current_max_videos_accounts(user_id)
        user_max_posts_accounts = await get_current_max_posts_accounts(user_id)

        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(text="💥 Запостить", callback_data="start_posting_menu")
        )
        builder.row(
            InlineKeyboardButton(text="📁 Шаблоны", callback_data="templates_menu"),
            InlineKeyboardButton(text="👤 Аккаунты", callback_data="start_account_menu"),
            width=2
        )
        builder.row(
            InlineKeyboardButton(text="💳 Подписка", callback_data="tarrifs_menu"),
            InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="balance_add"),
            width=2
        )
        builder.row(
            InlineKeyboardButton(text="📞 Поддержка", url="https://t.me/qxzxbtlqq"),
            InlineKeyboardButton(text="📘 Инструкция", url="https://example.com/guide"),
            width=2
        )

        if user.admin:
            builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_menu"))

        text = (
            f"💎 *Ваш профиль*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 `{user_id}`\n"
            f"💰 *{int(user_balance):,} ₽*\n"
            f"🏷️ *{formatted_status(user_admin, user_sub_lvl)}*\n"
            f"🎫 {formatted_time_sub(user_sub_expire)}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎥 *Видео:* `{user_max_video_accounts}`   💬 *Посты:* `{user_max_posts_accounts}`"
        )

        await send_func(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

        if isinstance(type_call, CallbackQuery):
            await type_call.answer()


@start_router.message(CommandStart())
async def start_menu(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    await create_or_update_user(user_id, username)
    await MainMenu.send_main_menu(message)
