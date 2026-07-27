"""Middleware / Guard for forcing users to join the Telegram channel before using the bot."""

import logging
from functools import wraps
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import db

logger = logging.getLogger(__name__)


async def is_user_channel_member(bot: Bot, user_id: int) -> bool:
    """Check if a user is a member of the required channel."""
    # Admins are exempt from mandatory channel join
    if user_id in config.ADMIN_IDS or user_id == config.ADMIN_USER_ID:
        return True

    channel_id = config.get_channel_id()
    if not channel_id:
        return True

    target_chat = int(channel_id) if channel_id.lstrip("-").isdigit() else channel_id

    try:
        member = await bot.get_chat_member(chat_id=target_chat, user_id=user_id)
        if member.status in ("creator", "administrator", "member"):
            return True
        return False
    except Exception as e:
        logger.warning("Could not check channel member status for user %s in channel %s: %s", user_id, channel_id, e)
        # If bot cannot verify status (e.g. invalid channel ID or bot not admin), allow user to proceed
        return True


def get_force_join_keyboard() -> InlineKeyboardMarkup:
    channel_link = config.get_channel_link()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=channel_link)],
        [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="check_join")]
    ])


def build_force_join_text(first_name: str = "Pengguna") -> str:
    shop_name = config.SHOP_NAME
    return (
        f"📢 *WAJIB JOIN CHANNEL*\n\n"
        f"Halo *{first_name}*! 👋\n"
        f"Untuk menggunakan bot *{shop_name}*, Anda diwajibkan untuk bergabung (subscribe) ke Channel Resmi kami terlebih dahulu.\n\n"
        f"1️⃣ Klik tombol *📢 Join Channel* di bawah.\n"
        f"2️⃣ Setelah me-join channel, klik tombol *✅ Saya Sudah Join*.\n\n"
        f"Terima kasih atas dukungannya! 🙏"
    )


async def send_force_join_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    first_name = user.first_name if user else "Pengguna"
    text = build_force_join_text(first_name)
    reply_markup = get_force_join_keyboard()

    if update.callback_query:
        try:
            await update.callback_query.answer("⚠️ Anda wajib bergabung dengan channel kami terlebih dahulu!", show_alert=True)
        except Exception:
            pass
        try:
            await update.callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except Exception:
            if user:
                await context.bot.send_message(chat_id=user.id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


def require_channel_join(func):
    """Decorator to enforce channel membership check before executing a handler."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return await func(update, context, *args, **kwargs)

        # Allow 'check_join' callback to be processed directly
        if update.callback_query and update.callback_query.data == "check_join":
            return await handle_check_join(update, context)

        joined = await is_user_channel_member(context.bot, user.id)
        if not joined:
            await send_force_join_prompt(update, context)
            return

        return await func(update, context, *args, **kwargs)
    return wrapper


async def handle_check_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler when user clicks 'Saya Sudah Join'."""
    query = update.callback_query
    if not query or not update.effective_user:
        return

    user_id = update.effective_user.id
    joined = await is_user_channel_member(context.bot, user_id)

    if joined:
        await query.answer("🎉 Terima kasih! Keanggotaan Anda telah diverifikasi.", show_alert=True)
        try:
            user_lang = db.get_user_lang(user_id)
            from handlers.start import build_home_text, get_main_menu_keyboard
            text = build_home_text(update.effective_user, user_lang)
            await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(user_id, user_lang))
        except Exception:
            from handlers.start import cmd_start
            await cmd_start(update, context)
    else:
        await query.answer("⚠️ Anda BELUM bergabung dengan channel! Silakan tekan tombol Join Channel terlebih dahulu.", show_alert=True)
