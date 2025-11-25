import re
from typing import Union
from aiogram import Bot, Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.enums import ParseMode
from sqlalchemy import select, and_
from app.bot.handlers.start import MainMenu
from app.shared.config.settings import get_youtube_settings
from app.shared.database.core import (get_user, get_tg_groups_count,
                                      get_current_video_accounts_count, get_current_max_videos_accounts,
                                      get_current_max_posts_accounts, check_tg_groups_exist, model_from_schema,
                                      get_session, add_tg_group_db)
from app.shared.database.models import TikTokAccount, YouTubeAccount, TgGroup
from app.shared.database.schemas import TgGroupCreate
from app.shared.logs.logg import logger


account_router = Router(name="account_router")
youtube_settings = get_youtube_settings()
TELEGRAPH_ARTICLE_URL = "https://telegra.ph/Kak-privyazat-Telegram-kanal-ili-gruppu-dlya-avtopostinga-11-20"


class TGGroupStates:
    waiting_for_name = "waiting_for_name"
    waiting_for_link = "waiting_for_link"
    waiting_for_chat_id = "waiting_for_chat_id"


class AccountsMenu:
    @staticmethod
    async def started_accounts_menu(type_call: Union[Message, CallbackQuery]):
        user_id = type_call.from_user.id
        username = type_call.from_user.username

        if isinstance(type_call, CallbackQuery):
            send_func = type_call.message.edit_text
        else:
            send_func = type_call.answer

        user = await get_user(user_id)

        max_videos_accounts = user.max_video_accounts
        max_posts_accounts = user.max_tg_accounts

        current_videos = await get_current_video_accounts_count(user_id)
        current_posts = await get_tg_groups_count(user_id)

        available_videos = max_videos_accounts - current_videos
        available_posts = max_posts_accounts - current_posts

        msg = (
            "👤 *Управление аккаунтами*\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"

            "Добавьте *новый* аккаунт, выбрав *нужный тип* ниже.\n\n"

            "🎥 *Видео-аккаунты (TikTok / YouTube)*\n"
            f"• Текущее количество:  *{current_videos}/{max_videos_accounts}*\n"
            f"• Свободно слотов: *{available_videos}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "💬 *Telegram-группы*\n"
            f"• Текущее количество:  *{current_posts}/{max_posts_accounts}*\n"
            f"• Свободно слотов: *{available_posts}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "👇 *Выберите тип аккаунта для добавления:*"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🎵 TikTok", callback_data="manage_tiktok_accounts"),
            InlineKeyboardButton(text="🔥 YouTube", callback_data="manage_youtube_accounts"),
            width=2
        )
        builder.row(
            InlineKeyboardButton(text="💬 Telegram", callback_data="manage_tg_accounts")
        )
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main_menu")
        )

        await send_func(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )

        if isinstance(type_call, CallbackQuery):
            await type_call.answer()

    @staticmethod
    async def tiktok_accounts_menu(call: CallbackQuery):
        user_id = call.from_user.id

        async with get_session() as session:
            result = await session.execute(
                select(TikTokAccount).where(TikTokAccount.user_id == user_id)
            )
            accounts = result.scalars().all()

            msg = (
                "🎵 *TikTok аккаунты*\n"
                "━━━━━━━━━━━━━━\n"
                "Выберите аккаунт или добавьте новый."
            )

            builder = InlineKeyboardBuilder()

            if accounts:
                for acc in accounts:
                    builder.row(
                        InlineKeyboardButton(
                            text=f"{acc.account_name}",
                            callback_data=f"tiktok_account:{acc.id}"
                        ),
                        width=2
                    )
            else:
                builder.row(
                    InlineKeyboardButton(text="Нет подключённых аккаунтов", callback_data="none")
                )

            builder.row(
                InlineKeyboardButton(text="➕ Добавить TikTok", callback_data="add_tiktok_account")
            )
            builder.row(
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_accounts_menu")
            )

            await call.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=builder.as_markup())
            await call.answer()

    @staticmethod
    async def youtube_accounts_menu(call: CallbackQuery):
        user_id = call.from_user.id

        async with get_session() as session:
            result = await session.execute(
                select(YouTubeAccount).where(YouTubeAccount.user_id == user_id)
            )
            accounts = result.scalars().all()

            msg = (
                "🔥 *YouTube аккаунты*\n"
                "━━━━━━━━━━━━━━\n"
                "Нажмите на канал, чтобы управлять им.\n"
                "Можете добавить новый."
            )

            builder = InlineKeyboardBuilder()

            if accounts:
                for acc in accounts:
                    builder.row(
                        InlineKeyboardButton(
                            text=f"{acc.channel_name}",
                            callback_data=f"youtube_account:{acc.id}"
                        ),
                        width=2
                    )
            else:
                builder.row(
                    InlineKeyboardButton(text="Нет YouTube каналов", callback_data="none")
                )

            builder.row(
                InlineKeyboardButton(text="➕ Добавить YouTube", callback_data="add_youtube_account")
            )
            builder.row(
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_accounts_menu")
            )

            await call.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=builder.as_markup())
            await call.answer()

    @staticmethod
    async def tg_groups_menu(call: CallbackQuery):
        user_id = call.from_user.id

        async with get_session() as session:
            result = await session.execute(
                select(TgGroup).where(TgGroup.user_id == user_id)
            )
            tg_groups = result.scalars().all()

            builder = InlineKeyboardBuilder()

            if tg_groups:
                for group in tg_groups:
                    builder.row(
                        InlineKeyboardButton(
                            text=group.tg_link,
                            callback_data=f"tg_group:{group.id}"
                        ),
                        width=2
                    )
            else:
                builder.row(
                    InlineKeyboardButton(text="Нет TG каналов", callback_data="none")
                )

            builder.row(
                InlineKeyboardButton(text="➕ Добавить TG", callback_data="add_tg_group")
            )
            builder.row(
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_accounts_menu")
            )

            await call.message.edit_text(
                "💬 *Ваши Telegram группы*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=builder.as_markup()
            )
            await call.answer()


# КНОПКА С ГЛАВНОГО МЕНЮ

@account_router.callback_query(F.data.in_(["start_account_menu", "back_to_accounts_menu"]))
async def send_started_account_menu(callback_query: CallbackQuery):
    await AccountsMenu.started_accounts_menu(callback_query)


# Обработка кнопок с аккаунтами

@account_router.callback_query(F.data.startswith("tiktok_acc:"))
async def tiktok_account_manage(call: CallbackQuery):
    acc_id = int(call.data.split(":")[1])
    user_id = call.from_user.id

    async for session in get_session():
        result = await session.execute(
            select(TikTokAccount).where(
                and_(
                    TikTokAccount.id == acc_id,
                    TikTokAccount.user_id == user_id
                )
            )
        )
        account = result.scalars().first()

        if not account:
            await call.message.edit_text(
                "❌ Этот TikTok аккаунт не найден или не принадлежит вам.",
                parse_mode=ParseMode.MARKDOWN
            )
            await call.answer()
            return

        msg = (
            "🎵 *Управление TikTok аккаунтом*\n\n"
            f"*Название аккаунта:* {account.account_name}\n"
            f"*ID аккаунта:* {account.account_id}\n"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🗑 Удалить аккаунт",
                callback_data=f"tiktok_delete:{acc_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="menu_tiktok"
            )
        )

        await call.message.edit_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )
        await call.answer()


@account_router.callback_query(F.data.startswith("tg_group:"))
async def tg_group_manage(call: CallbackQuery):
    group_id = int(call.data.split(":")[1])
    user_id = call.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(TgGroup).where(
                and_(
                    TgGroup.id == group_id,
                    TgGroup.user_id == user_id
                )
            )
        )
        group = result.scalars().first()

        if not group:
            await call.message.edit_text(
                "❌ Эта группа не найдена или не принадлежит вам.",
                parse_mode=ParseMode.MARKDOWN
            )
            await call.answer()
            return

        msg = (
            "💬 *Управление Telegram группой*\n\n"
            f"*Название группы:* {group.title or 'Без названия'}\n"
            f"*Ссылка:* {group.tg_link}\n"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🗑 Удалить группу",
                callback_data=f"tg_delete:{group_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="menu_tg"
            )
        )

        await call.message.edit_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )
        await call.answer()


@account_router.callback_query(F.data.startswith("menu_"))
async def main_menu_handler(call: CallbackQuery):
    service = call.data.split("_")[1]

    if service == "tg":
        await AccountsMenu.tg_groups_menu(call)
    elif service == "youtube":
        await AccountsMenu.youtube_accounts_menu(call)
    elif service == "tiktok":
        await AccountsMenu.tiktok_accounts_menu(call)
    else:
        await call.message.answer("❌ Неизвестный сервис")
        await AccountsMenu.started_accounts_menu(call)

    await call.answer()


@account_router.callback_query(F.data.startswith("youtube_account:"))
async def youtube_account_manage(call: CallbackQuery):
    acc_id = int(call.data.split(":")[1])
    user_id = call.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(YouTubeAccount).where(
                and_(
                    YouTubeAccount.id == acc_id,
                    YouTubeAccount.user_id == user_id
                )
            )
        )
        account = result.scalars().first()

        if not account:
            await call.message.edit_text(
                "❌ Этот аккаунт не найден или не принадлежит вам.",
                parse_mode=ParseMode.MARKDOWN
            )
            await call.answer()
            await AccountsMenu.youtube_accounts_menu(call)
            return

        msg = (
            "🔥 *Управление YouTube аккаунтом*\n\n"
            f"*Название канала:* {account.channel_name}\n"
            f"*ID канала:* `{account.channel_id}`\n"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🗑 Удалить аккаунт",
                callback_data=f"youtube_delete:{acc_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="menu_youtube"
            )
        )

        await call.message.edit_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )
        await call.answer()


@account_router.callback_query(F.data.startswith(("youtube_delete:", "tiktok_delete:", "tg_delete:")))
async def delete_account_handler(call: CallbackQuery):
    service, acc_id = call.data.split(":")
    acc_id = int(acc_id)
    text = ""

    async with get_session() as session:
        if service == "youtube_delete":
            account = await session.get(YouTubeAccount, acc_id)
        elif service == "tiktok_delete":
            account = await session.get(TikTokAccount, acc_id)
        elif service == "tg_delete":
            account = await session.get(TgGroup, acc_id)
        else:
            account = None

        if account:
            await session.delete(account)
            await session.commit()
            text = f"✅ Аккаунт {acc_id} успешно удалён."
        else:
            text = f"❌ Аккаунт {acc_id} не найден."

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"menu_{service.split('_')[0]}")
    )

    await call.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup()
    )
    await call.answer()


# ОБЩЕЕ МЕНЮ

@account_router.callback_query(F.data == "manage_tiktok_accounts")
async def manage_tiktok_accounts_menu(call: CallbackQuery):
    await AccountsMenu.tiktok_accounts_menu(call)
    await call.answer()


@account_router.callback_query(F.data == "manage_youtube_accounts")
async def manage_youtube_accounts_menu(call: CallbackQuery):
    await AccountsMenu.youtube_accounts_menu(call)
    await call.answer()


@account_router.callback_query(F.data == "manage_tg_accounts")
async def manage_youtube_accounts_menu(call: CallbackQuery):
    await AccountsMenu.tg_groups_menu(call)
    await call.answer()


# ТИК-ТОК АВТОРИЗАЦИЯ

@account_router.callback_query(F.data == "add_tiktok_account")
async def add_tiktok_account(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    available = await get_current_max_videos_accounts(user_id)

    if available > 0:
        auth_url = f"https://yourdomain.com/tiktok/auth?tg_id={user_id}"

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔐 Авторизовать TikTok", url=auth_url)
        )
        builder.row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="menu_tiktok")
        )

        await callback_query.message.edit_text(
            "Для привязки TikTok аккаунта нажмите кнопку ниже:",
            reply_markup=builder.as_markup()
        )

    else:
        # ЛИБО ПОСЛЕ СОСТАВЛЕНИЕ ТАРИФ-СТРАНИЦЫ КНОПКУ НА ГЛАВНОЕ МЕНЮ И КНОПКУ НА ТАРИФЫ
        await callback_query.message.answer(
            text="Ваш *лимит* на добавление видео аккаунтов *исчерпан* \n"
                 "Возвращаем вас в *главное меню...*",
            parse_mode=ParseMode.MARKDOWN
        )
        await MainMenu.send_main_menu(callback_query)
        return


@account_router.callback_query(F.data == "add_youtube_account")
async def add_tiktok_account(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    available = await get_current_max_videos_accounts(user_id)

    if available > 0:

        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={youtube_settings.client_id}"
            f"&redirect_uri={youtube_settings.redirect_uri}"
            "&response_type=code"
            "&scope=https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"
            "&access_type=offline"
            "&prompt=consent"
            f"&state={user_id}"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔐 Авторизовать YouTube", url=auth_url)
        )
        builder.row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="menu_youtube")
        )

        await callback_query.message.edit_text(
            "Для привязки Youtube аккаунта нажмите кнопку ниже:",
            reply_markup=builder.as_markup()
        )

    else:
        # ЛИБО ПОСЛЕ СОСТАВЛЕНИЕ ТАРИФ-СТРАНИЦЫ КНОПКУ НА ГЛАВНОЕ МЕНЮ И КНОПКУ НА ТАРИФЫ
        await callback_query.message.answer(
            text="Ваш *лимит* на добавление видео аккаунтов *исчерпан* \n"
                 "Возвращаем вас в *главное меню...*",
            parse_mode=ParseMode.MARKDOWN
        )
        await MainMenu.send_main_menu(callback_query)
        return


# ДОБАВЛЕНИЕ ТГ ГРУППЫ/КАНАЛА

@account_router.callback_query(F.data == "add_tg_group")
async def add_tg_group(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    available = await get_current_max_posts_accounts(user_id)

    if available <= 0:
        await callback_query.message.answer(
            text="Ваш *лимит* на добавление текстовых аккаунтов *исчерпан* \n"
                 "Возвращаем вас в *главное меню...*",
            parse_mode=ParseMode.MARKDOWN
        )
        await MainMenu.send_main_menu(callback_query)
        return

    await callback_query.message.answer(
        f"📘 <b>Перед привязкой группы ознакомьтесь с инструкцией:</b>\n\n"
        f"{TELEGRAPH_ARTICLE_URL}",
        parse_mode=ParseMode.HTML
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu_tg")
    )

    await callback_query.message.answer(
        "🌐 <b>Добавление новой TG-группы</b>\n\n"
        "Введите название TG-группы:",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )

    await state.set_state(TGGroupStates.waiting_for_name)


@account_router.message(StateFilter(TGGroupStates.waiting_for_name))
async def tg_add_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()

    if not name:
        await message.answer("Название не может быть пустым. Введите названиеTG-группы.")
        return

    await state.update_data(tg_name=name)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_accounts_menu"))

    await message.answer(
        "🌐 <b>Добавление TG-группы</b>\n\n"
        "Введите ссылку на группу/канал (пример: https://t.me/channelname)\n",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )

    await state.set_state(TGGroupStates.waiting_for_link)


@account_router.message(StateFilter(TGGroupStates.waiting_for_link))
async def tg_add_link(message: Message, state: FSMContext):
    link = (message.text or "").strip()

    if link == "-":
        link = None

    await state.update_data(tg_link=link)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_accounts_menu"))

    await message.answer(
        "🌐 <b>Добавление TG-группы</b>\n\n"
        "Введите числовой ID группы/канала (пример: -1001234567890)",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )

    await state.set_state(TGGroupStates.waiting_for_chat_id)


@account_router.message(StateFilter(TGGroupStates.waiting_for_chat_id))
async def tg_add_chat_id(message: Message, state: FSMContext):
    chat_id_raw = (message.text or "").strip()
    data = await state.get_data()

    tg_name = data.get("tg_name")
    tg_link = data.get("tg_link")

    if not re.fullmatch(r"-?\d+", chat_id_raw):
        await message.answer("Неверный формат. Введите числовой ID.")
        await AccountsMenu.started_accounts_menu(message)

    tg_group_id = str(chat_id_raw)

    tg_group_schema = TgGroupCreate(
        tg_link=tg_link,
        tg_channel_id=tg_group_id,
        title=tg_name,
        user_id=message.from_user.id
    )

    existing = await check_tg_groups_exist(user_id=message.from_user.id, channel_id=tg_group_id)

    if existing:
        msg = (
            "⚠️ *Этот TG-канал уже привязан*\n\n"
            f"Канал: *{tg_link}*\n"
            f"ID: `{tg_group_id}`\n\n"
            "Вы не можете добавить один и тот же канал дважды."
        )
        logger.warning(f"Duplicate TG channel bind attempt. TG_NAME={tg_link}, TG_ID={tg_group_id}")

        await state.clear()
        await message.answer(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        await AccountsMenu.started_accounts_menu(message)
        return

    else:
        try:
            tg_account_model = model_from_schema(
                schema_obj=tg_group_schema,
                model_cls=TgGroup
            )

        except Exception as e:
            msg = f"❌ Ошибка конвертации данных: {e}"
            logger.exception(f"Model conversion failed. TG_ID={tg_group_id}, error={e}")
            await message.answer(
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            await AccountsMenu.started_accounts_menu(message)
            return

        try:
            await add_tg_group_db(tg_account_model)
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")
            await state.clear()
            await AccountsMenu.started_accounts_menu(message)
            return

        success_msg = (
            "🎉 *TG канал успешно привязана!*\n\n"
            f"Канал: {tg_link}\n"
            f"ID: `{tg_group_id}`\n\n"
            "Теперь вы можете загружать видео 🎬"
        )
        await message.answer(
            text=success_msg,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        logger.info(f"TG channel linked: TG_ID={tg_group_id}, TG_NAME={tg_link}")
        await state.clear()
        await AccountsMenu.started_accounts_menu(message)


# Просто обработка на пустой клик
@account_router.callback_query(F.data == "none")
async def none_click_button(callback_query: CallbackQuery):
    await callback_query.answer(
        "Упс... Пусто :("
    )
