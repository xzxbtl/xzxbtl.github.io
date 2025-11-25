import json
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.enums import ParseMode
from sqlalchemy import select
from app.shared.database.core import (get_videos_accounts, get_user_with_video_templates,
                                      get_user_with_posts_templates, get_session)
from app.shared.database.models import PostsTemplate, TgGroup, YouTubeAccount, TikTokAccount

posting_router = Router(name="posting_router")


class TgPostRate:
    def __init__(self):
        self.time_per_post = {}


tg_rate = TgPostRate()


class PostingTGStates(StatesGroup):
    waiting_for_media = State()
    waiting_for_text = State()
    waiting_for_buttons = State()
    waiting_for_schedule = State()
    confirmation = State()


async def send_post_to_group(bot: Bot, chat_id: str | int, media_list: list, text: str = "", buttons=None):
    if not media_list:
        await bot.send_message(chat_id, text=text or " ", reply_markup=buttons)
        return

    media_list_sorted = media_list
    input_media = []

    for i, m in enumerate(media_list_sorted):
        source = m.get("file_id")
        if not source:
            continue

        if m["type"] == "photo":
            media = InputMediaPhoto(media=source)
        elif m["type"] == "video":
            media = InputMediaVideo(media=source)
        elif m["type"] == "document":
            media = InputMediaDocument(media=source)
        else:
            continue

        if i == 0 and text and m["type"] != "document":
            media.caption = text
        input_media.append(media)

    if not input_media:
        await bot.send_message(chat_id, text=text or " ", reply_markup=buttons)
        return

    if len(input_media) == 1:
        first = input_media[0]
        if isinstance(first, InputMediaPhoto):
            await bot.send_photo(chat_id, photo=first.media, caption=getattr(first, "caption", None) or text,
                                 reply_markup=buttons)
        elif isinstance(first, InputMediaVideo):
            await bot.send_video(chat_id, video=first.media, caption=getattr(first, "caption", None) or text,
                                 reply_markup=buttons)
        else:
            await bot.send_document(chat_id, document=first.media, caption=text if text else None,
                                    reply_markup=buttons)
    else:
        await bot.send_media_group(chat_id, media=input_media)

        if buttons:
            message_text = "📎 Дополнительная информация к посту"
            await bot.send_message(
                chat_id,
                text=message_text,
                reply_markup=buttons
            )


def skip_cancel_keyboard(skip_cb="tg_next",
                         skip_text="➡️ Далее",
                         cancel_cb="tg_cancel", cancel_text="❌ Отмена"):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=cancel_text, callback_data=cancel_cb),
        InlineKeyboardButton(text=skip_text, callback_data=skip_cb),
    ).adjust(2)
    return builder.as_markup()


def join_accounts(accounts):
    if not accounts:
        return "— Нет привязанных аккаунтов"

    lines = []
    for account in accounts:
        if isinstance(account, YouTubeAccount):
            prefix = "🎬"
            account_param = account.channel_name
        elif isinstance(account, TikTokAccount):
            prefix = "🎵"
            account_param = account.account_name
        elif isinstance(account, TgGroup):
            prefix = "💬"
            account_param = account.title or account.tg_link
        else:
            prefix = "•"
            account_param = "Неизвестный аккаунт"

        lines.append(f"{prefix} {account_param}")

    return "\n".join(lines)


def join_templates(templates, type_templates: str = "video"):
    if not templates:
        return "— Шаблонов пока нет"
    if type_templates == "video":
        return "\n".join([
            f"• *{tpl.title}* — {tpl.language.upper()} ({tpl.visibility})"
            for tpl in templates
        ])
    else:
        return "\n".join([
            f"• *{tpl.title}*"
            for tpl in templates
        ])


class MainMenuPosting:
    @staticmethod
    async def send_main_posting_menu(callback_query: CallbackQuery):
        msg = (
            "⚡️ *Главное меню публикаций*\n"
            "Выберите *тип контента*, который *хотите запостить:*"
        )

        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="🎥 Видео",
                callback_data="main_video_post_menu"
            ),
            InlineKeyboardButton(
                text="💬 Посты",
                callback_data="main_tg_post_menu"
            ),
            width=2
        )
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main_menu"
            )
        )

        await callback_query.message.edit_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )
        await callback_query.answer()


class MainVideoPosting:
    @staticmethod
    async def send_main_video_posting_menu(callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        tiktok_accounts, youtube_accounts = await get_videos_accounts(user_id)

        tiktok_list = "\n".join([f"• {acc.account_name}" for acc in tiktok_accounts]) \
            if tiktok_accounts else "— Нет привязанных аккаунтов"

        youtube_list = "\n".join([f"• {acc.account_name}" for acc in youtube_accounts]) \
            if youtube_accounts else "— Нет привязанных аккаунтов"

        msg = (
            "🎬 *Меню видеопубликаций*\n\n"
            "Выберите, на какие аккаунты будет отправлен пост.\n"
            "Сообщение автоматически разойдётся по всем вашим привязанным аккаунтам.\n\n"
            "🎵 *TikTok аккаунты:*\n"
            f"{tiktok_list}\n\n"
            "🔥 *YouTube аккаунты:*\n"
            f"{youtube_list}"
        )

        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="🚀 Все аккаунты", callback_data="all_post_menu"
            )
        )

        builder.row(
            InlineKeyboardButton(text="🎵 TikTok аккаунты", callback_data="tik_tok_menu"),
            InlineKeyboardButton(text="🔥 YouTube аккаунты", callback_data="youtube_menu"),
            width=2
        )

        builder.row(
            InlineKeyboardButton(text="◀️ назад", callback_data="back_to_main_post_menu")
        )

        await callback_query.message.edit_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )
        await callback_query.answer()


# ДЛЯ ТИК-ТОКА ОТДЕЛЬНОЕ ПОСТИНГ МЕНЮ С ВЫБОРОМ ШАБЛОНОВ

class TikTokPosting:
    @staticmethod
    async def tiktok_posting_menu(callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        user = await get_user_with_video_templates(user_id)

        tik_tok_accounts = user.tiktok_accounts
        tik_tok_templates = [
            template for template in user.video_templates
            if template.platform == "tiktok"
        ]

        msg = (
            "🎵 *TikTok публикации*\n\n"
            "Выберите шаблон для публикации видео.\n"
            "Все настройки будут применены автоматически.\n\n"
            "👤 *Ваши TikTok аккаунты:*\n"
            f"{join_accounts(tik_tok_accounts)}\n\n"
            "📄 *Доступные TikTok шаблоны:*\n"
            f"{join_templates(tik_tok_templates)}"
        )

        builder = InlineKeyboardBuilder()

        for tpl in tik_tok_templates:
            builder.row(
                InlineKeyboardButton(
                    text=f"🎥 {tpl.title}",
                    callback_data=f"start_posting_tiktok_with_video_{tpl.id}"
                ),
                width=2
            )

        builder.row(
            InlineKeyboardButton(
                text="Без шаблона",
                callback_data="start_posting_tiktok_without_template"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main_posting_menu"
            )
        )

        await callback_query.message.edit_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )
        await callback_query.answer()


# ДЛЯ ЮТУБА ОТДЕЛЬНОЕ ПОСТИНГ МЕНЮ С ВЫБОРОМ ШАБЛОНОВ
class YouTubePosting:
    @staticmethod
    async def send_youtube_posting_menu(callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        user = await get_user_with_video_templates(user_id)

        youtube_accounts = user.youtube_accounts
        youtube_templates = [
            template for template in user.video_templates
            if template.platform == "youtube"
        ]

        msg = (
            "🔥 *YouTube публикации*\n\n"
            "Выберите шаблон для публикации видео.\n"
            "Все настройки будут применены автоматически.\n\n"
            "👤 *Ваши YouTube аккаунты:*\n"
            f"{join_accounts(youtube_accounts)}\n\n"
            "📄 *Доступные YouTube шаблоны:*\n"
            f"{join_templates(youtube_templates)}"
        )

        builder = InlineKeyboardBuilder()

        for tpl in youtube_templates:
            builder.row(
                InlineKeyboardButton(
                    text=f"🎥 {tpl.title}",
                    callback_data=f"start_posting_youtube_with_video_{tpl.id}"
                ),
                width=2
            )

        builder.row(
            InlineKeyboardButton(
                text="Без шаблона",
                callback_data="start_posting_youtube_without_template")
        )

        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main_posting_menu"
            )
        )

        await callback_query.message.edit_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )
        await callback_query.answer()


# ДЛЯ ВСЕХ АККАУНТОВ (ВЫБОР ОБЩЕГО ШАБЛОНА)


class BasePostingMenu:
    @staticmethod
    async def send_all_posting_menu(callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        user = await get_user_with_video_templates(user_id)

        youtube_accounts = user.youtube_accounts
        tik_tok_accounts = user.tiktok_accounts
        all_base_templates = [
            template for template in user.video_templates
            if template.platform == "common"
        ]

        msg = (
            "📰 *Общие публикации*\n\n"
            "Выберите шаблон для публикации видео.\n"
            "Все настройки будут применены автоматически.\n\n"
            "👤 *Ваши YouTube аккаунты:*\n"
            f"{join_accounts(youtube_accounts)}\n\n"
            "👤 *Ваши TikTok аккаунты:*\n"
            f"{join_accounts(tik_tok_accounts)}\n\n"
            "📄 *Доступные Общие шаблоны:*\n"
            f"{join_templates(all_base_templates)}"
        )

        builder = InlineKeyboardBuilder()

        for tpl in all_base_templates:
            builder.row(
                InlineKeyboardButton(
                    text=f"🎥 {tpl.title}",
                    callback_data=f"start_posting_base_with_video_{tpl.id}"
                ),
                width=2
            )

        builder.row(
            InlineKeyboardButton(
                text="Без шаблона",
                callback_data="start_posting_videos_without_template"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main_posting_menu"
            )
        )

        await callback_query.message.edit_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )
        await callback_query.answer()


class TelegramPostingMenu:
    @staticmethod
    async def send_tg_posting_menu(callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        user = await get_user_with_posts_templates(user_id)

        tg_accounts = user.tg_groups
        tg_templates = [
            template for template in user.posts_templates
        ]

        msg = (
            "🔥 *TG публикации*\n\n"
            "Выберите шаблон для публикации поста.\n"
            "Все настройки будут применены автоматически.\n\n"
            "👤 *Ваши ТГ группы/аккаунты:*\n"
            f"{join_accounts(tg_accounts)}\n\n"
            "📄 *Доступные TG шаблоны:*\n"
            f"{join_templates(tg_templates, type_templates="posts")}"
        )

        builder = InlineKeyboardBuilder()

        for tpl in tg_templates:
            builder.row(
                InlineKeyboardButton(
                    text=f"📰 {tpl.title}",
                    callback_data=f"start_posting_tg_{tpl.id}"
                ),
                width=2
            )

        builder.row(
            InlineKeyboardButton(
                text="Без шаблона",
                callback_data="start_posting_tg_without_template"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main_post_menu"
            )
        )

        await callback_query.message.edit_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )
        await callback_query.answer()


# КНОПКИ НАЗАД

@posting_router.callback_query(F.data == "back_to_main_post_menu")
async def send_to_main_post_menu(callback_query: CallbackQuery):
    await MainMenuPosting.send_main_posting_menu(callback_query)


@posting_router.callback_query(F.data == "back_to_main_posting_menu")
async def send_to_main_posting_menu(callback_query: CallbackQuery):
    await MainVideoPosting.send_main_video_posting_menu(callback_query)


@posting_router.callback_query(F.data == "start_posting_menu")
async def send_posts_menu(callback_query: CallbackQuery):
    await MainMenuPosting.send_main_posting_menu(callback_query)


# ТИКТОК ОБРАБОТКА КАЛЛБЕКОВ


@posting_router.callback_query(F.data == "main_video_post_menu")
async def send_main_video_posting_menu(callback_query: CallbackQuery):
    await MainVideoPosting.send_main_video_posting_menu(callback_query)


@posting_router.callback_query(F.data == "tik_tok_menu")
async def send_tik_tok_menu(callback_query: CallbackQuery):
    await TikTokPosting.tiktok_posting_menu(callback_query)


# ЮТУБ ОБРАБОТКА КАЛЛБЕКОВ

@posting_router.callback_query(F.data == "youtube_menu")
async def send_youtube_menu(callback_query: CallbackQuery):
    await YouTubePosting.send_youtube_posting_menu(callback_query)


# ОБРАБОТКА ОБЩИХ ШАБЛОНОВ КАЛЛБЕКОВ

@posting_router.callback_query(F.data == "all_post_menu")
async def send_all_post_menu(callback_query: CallbackQuery):
    await BasePostingMenu.send_all_posting_menu(callback_query)


# ОБРАБОТКА ШАБЛОНОВ ТГ КАЛЛБЕКОВ
@posting_router.callback_query(F.data == "main_tg_post_menu")
async def send_tg_menu(callback_query: CallbackQuery):
    # Лимит чтобы не было спама постами
    current_time = datetime.now()
    last_time_tg_request = tg_rate.time_per_post.get(callback_query.from_user.id)

    if last_time_tg_request is not None:
        time_difference = current_time - last_time_tg_request
        cooldown_time = timedelta(seconds=60)
        if time_difference < cooldown_time:
            remaining_time = cooldown_time - time_difference
            remaining_seconds = remaining_time.total_seconds()

            await callback_query.message.answer(
                text=(
                    "⏳ *Вы слишком часто отправляете посты!*\n"
                    f"Подождите ещё: *{int(remaining_seconds)} сек.*\n"
                    "Прежде чем отправить снова."
                ),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            await callback_query.answer()
            return

    tg_rate.time_per_post[callback_query.from_user.id] = current_time
    await TelegramPostingMenu.send_tg_posting_menu(callback_query)


# ОБРАБОТКА ТГ ОТПРАВКИ В ГРУППЫ

@posting_router.callback_query(F.data.startswith("start_posting_tg"))
async def start_posting_tg(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data
    user_id = call.from_user.id

    if data.endswith("without_template"):
        await state.update_data(template_id=None, media_list=[], text="", buttons=[])
        await call.message.answer(
            "📝 *Отправьте текст поста* или нажмите '➡️ Далее', чтобы пропустить:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=skip_cancel_keyboard(skip_cb="tg_next_text")
        )
        await state.set_state(PostingTGStates.waiting_for_text)
    else:
        template_id = int(data.split("_")[-1])
        async with get_session() as session:
            result = await session.execute(
                select(PostsTemplate).where(
                    PostsTemplate.id == template_id,
                    PostsTemplate.user_id == user_id
                )
            )
            tpl = result.scalar_one_or_none()

        if not tpl:
            await call.message.answer("❌ Шаблон не найден")
            return

        media_list = []
        if tpl.media_url:
            media_list.append({"url": tpl.media_url, "type": tpl.media_type})

        await state.update_data(
            template_id=tpl.id,
            media_list=media_list,
            text=tpl.text or "",
            buttons=tpl.buttons_json or {}
        )

        await call.message.answer(
            "📎 *Дополнительно отправьте фото/видео для поста* или нажмите "
            "'➡️ Далее', чтобы использовать только медиа из шаблона:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=skip_cancel_keyboard(skip_cb="tg_next_media")
        )
        await state.set_state(PostingTGStates.waiting_for_media)


@posting_router.message(StateFilter(PostingTGStates.waiting_for_text))
async def get_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text or "")
    await message.answer(
        "🖼️ *Текст сохранен.*\nТеперь отправьте медиафайлы (фото/видео) или нажмите '➡️ Далее', чтобы пропустить:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=skip_cancel_keyboard(skip_cb="tg_next_media")
    )
    await state.set_state(PostingTGStates.waiting_for_media)


@posting_router.message(StateFilter(PostingTGStates.waiting_for_media), F.photo | F.video | F.document)
async def get_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("media_list", [])

    if message.photo:
        fid = message.photo[-1].file_id
        mtype = "photo"
    elif message.video:
        fid = message.video.file_id
        mtype = "video"
    elif message.document:
        fid = message.document.file_id
        mtype = "document"
    else:
        await message.answer("❌ Не удалось распознать медиа. Отправьте фото, видео или документ.")
        return

    entry = {
        "type": mtype,
        "file_id": fid,
    }
    media_list.append(entry)
    await state.update_data(media_list=media_list)

    current_index = len(media_list)
    display_index = current_index

    await message.answer(
        f"✅ Медиа: *{display_index}* добавлено\n"
        "Можно отправить ещё или нажмите '➡️ Далее', чтобы перейти к кнопкам:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=skip_cancel_keyboard(skip_cb="tg_next_buttons")
    )


@posting_router.callback_query(F.data.startswith("tg_next_buttons"))
async def ask_buttons(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(
        "🔘 *Добавление кнопок к посту*\nПришлите JSON-массив кнопок или нажмите '➡️ Далее', чтобы пропустить:\n"
        "Пример: [{'text': 'Ссылка', 'url': 'https://example.com'}]",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=skip_cancel_keyboard(skip_cb="tg_next_schedule")
    )
    await state.set_state(PostingTGStates.waiting_for_buttons)


@posting_router.message(StateFilter(PostingTGStates.waiting_for_buttons))
async def get_buttons(message: Message, state: FSMContext):
    try:
        buttons = json.loads(message.text)
        if not isinstance(buttons, list):
            raise ValueError
        await state.update_data(buttons={"buttons": buttons})
        await message.answer(
            "✅ Кнопки сохранены. Нажмите '➡️ Далее', чтобы продолжить:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=skip_cancel_keyboard(skip_cb="tg_next_schedule")
        )
        await state.set_state(PostingTGStates.waiting_for_schedule)
    except Exception:
        await message.answer(
            "❌ Неверный формат JSON. Попробуйте снова или нажмите '➡️ Далее', чтобы пропустить."
        )


@posting_router.callback_query(F.data.startswith("tg_next_schedule"))
async def ask_schedule(call: CallbackQuery, state: FSMContext):
    await call.answer()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="tg_cancel"),
        InlineKeyboardButton(text="⏰ Сейчас", callback_data="tg_schedule_now"),
    )
    await call.message.answer(
        "📅 Выберите время публикации поста:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PostingTGStates.waiting_for_schedule)


async def send_confirmation(message, state: FSMContext):
    data = await state.get_data()
    preview_text = data.get("text", "")
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data="confirm_post_no"),
        InlineKeyboardButton(text="✅ Да, публиковать", callback_data="confirm_post_yes"),
    )
    await message.answer(
        f"🔎 Проверьте пост перед публикацией:\n\n{preview_text or 'Без текста'}",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PostingTGStates.confirmation)


@posting_router.callback_query(F.data.startswith("tg_schedule_"))
async def process_schedule(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.data.endswith("now"):
        await state.update_data(schedule_time=None)
    await send_confirmation(call.message, state)


@posting_router.callback_query(F.data.startswith("confirm_post_"))
async def handle_confirmation(call: CallbackQuery, state: FSMContext, bot: Bot):
    await call.answer()

    data = await state.get_data()
    media_list = data.get("media_list", [])
    text = data.get("text", "")
    buttons_data = data.get("buttons", {})

    buttons = None

    if buttons_data:
        builder = InlineKeyboardBuilder()

        if "inline_keyboard" in buttons_data:
            for row in buttons_data["inline_keyboard"]:
                for btn in row:
                    if btn.get("url"):
                        builder.row(InlineKeyboardButton(text=btn["text"], url=btn["url"]), width=2)
                    elif btn.get("callback_data"):
                        builder.row(InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]), width=2)

        elif "buttons" in buttons_data:
            for btn in buttons_data["buttons"]:
                if btn.get("url"):
                    builder.row(InlineKeyboardButton(text=btn["text"], url=btn["url"]), width=2)
                elif btn.get("callback_data"):
                    builder.row(InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]), width=2)

        buttons = builder.as_markup()

    cleaned_media = []
    for m in media_list:
        # 1) { "type": "photo"/"video", "file_id": "..." }
        # 2) шаблон: { "url": "...", "type": "photo" }
        if isinstance(m, dict):
            if m.get("file_id") and m.get("type"):
                cleaned_media.append(m)
                continue
            if m.get("url") and m.get("type"):
                cleaned_media.append({
                    "type": m["type"],
                    "file_id": m["url"],
                })
                continue

    if call.data.endswith("yes"):
        async with get_session() as session:
            result = await session.execute(select(TgGroup).where(TgGroup.user_id == call.from_user.id))
            groups = result.scalars().all()

        for grp in groups:
            await send_post_to_group(bot, grp.tg_channel_id, cleaned_media, text=text, buttons=buttons)

        await call.message.answer("🎉 ✅ Пост опубликован!")

        tg_rate.time_per_post[call.from_user.id] = datetime.now()

    else:
        await call.message.answer("❌ Публикация отменена")

    await TelegramPostingMenu.send_tg_posting_menu(call)
    await state.clear()


# Скип кнопка обработка
@posting_router.callback_query(F.data == "tg_next_media")
async def skip_text(call: CallbackQuery, state: FSMContext):
    await call.answer(show_alert=False)
    await state.update_data(text="")
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="tg_cancel"),
        InlineKeyboardButton(text="➡️ Далее", callback_data="tg_next_buttons"),
    )
    await call.message.answer(
        "✏️ Текст пропущен.\n"
        "📎 Отправьте медиафайлы (фото/видео) или нажмите '➡️ Далее', чтобы пропустить:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PostingTGStates.waiting_for_media)


@posting_router.callback_query(F.data == "tg_next_buttons")
async def skip_media(call: CallbackQuery, state: FSMContext):
    await call.answer(show_alert=False)
    await state.update_data(media_list=[])
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="tg_cancel"),
        InlineKeyboardButton(text="➡️ Далее", callback_data="tg_next_schedule"),
    )
    await call.message.answer(
        "📎 Медиафайлы пропущены.\n"
        "🎛 Перейти к добавлению кнопок или нажмите '➡️ Далее', чтобы пропустить:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PostingTGStates.waiting_for_buttons)


@posting_router.callback_query(F.data == "tg_next_schedule")
async def skip_buttons(call: CallbackQuery, state: FSMContext):
    await call.answer(show_alert=False)
    await state.update_data(buttons={})
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏱ Сейчас", callback_data="tg_schedule_now"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="tg_cancel")
    )
    await call.message.answer(
        "🎛 Кнопки пропущены.\n"
        "⏰ Выберите время публикации поста: '⏱ Сейчас' или укажите дату и время:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PostingTGStates.waiting_for_schedule)


@posting_router.callback_query(F.data == "tg_schedule_now")
async def schedule_now(call: CallbackQuery, state: FSMContext):
    await call.answer(show_alert=False)
    await state.update_data(schedule_time=None)
    await send_confirmation(call.message, state)


@posting_router.callback_query(F.data == "tg_cancel")
async def cancel_posting_tg(call: CallbackQuery, state: FSMContext):
    await call.answer(show_alert=False)
    await state.clear()
    await TelegramPostingMenu.send_tg_posting_menu(call)
    await call.message.answer("❌ Операция отменена. Возврат в главное меню TG постинга.")
