"""Module for managing Telegram notifications (e.g. channel purchase alerts)."""

import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

import config
import db

logger = logging.getLogger(__name__)


def mask_name(name: str) -> str:
    """Mask user's name or username for privacy (e.g. 'Thomas' -> 'Th***', '@CoachAzizul' -> '@Co***')."""
    name = (name or "").strip()
    if not name:
        return "Pengguna***"
    if name.startswith("@"):
        un = name[1:]
        if len(un) <= 2:
            return f"@{un}***"
        return f"@{un[:2]}***"
    if len(name) <= 2:
        return f"{name}***"
    return f"{name[:2]}***"


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def escape_md(text: str) -> str:
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


async def send_channel_purchase_notif(bot: Bot, order: dict, product_name: str = "") -> None:
    """Send public purchase notification to the configured Telegram channel."""
    channel_id = config.get_channel_id()
    if not channel_id:
        logger.debug("No channel ID configured for purchase notifications.")
        return

    try:
        if not product_name:
            product = db.get_product(order.get("product_id", 1))
            product_name = product["name"] if product else "Produk Digital"

        buyer_name = order.get("first_name") or order.get("username") or f"User{str(order.get('user_id', ''))[-4:]}"
        masked = mask_name(buyer_name)

        total = order.get("total", 0)
        quantity = order.get("quantity", 1)

        bot_username = ""
        try:
            me = await bot.get_me()
            bot_username = me.username
        except Exception:
            pass

        bot_link = f"https://t.me/{bot_username}" if bot_username else config.get_channel_link()

        text = (
            "🎉 *PEMBELIAN SUKSES* 🎉\n"
            f"👤 *Pembeli:* {escape_md(masked)}\n"
            f"📦 *Produk:* {escape_md(product_name)}\n"
            f"💰 *Total:* Rp{format_rupiah(total)}\n"
            f"🛍️ *Jumlah:* {quantity}x\n\n"
            "✨ *Terima kasih telah berbelanja!*\n"
            "🛍️ *Mau order juga? Chat bot sekarang!*"
        )

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Order via Bot", url=bot_link)]
        ])

        target_chat = int(channel_id) if channel_id.lstrip("-").isdigit() else channel_id

        await bot.send_message(
            chat_id=target_chat,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
        logger.info("Sent purchase notification for order %s to channel %s", order.get("id"), channel_id)
    except Exception as e:
        if "Chat not found" in str(e):
            logger.warning(
                "⚠️ Gagal mengirim notifikasi ke channel %s: 'Chat not found'. "
                "Pastikan bot Telegram (@%s) sudah DITAMBAHKAN SEBAGAI ADMIN di Channel tersebut!",
                channel_id, bot_username or "bot"
            )
        else:
            logger.exception("Failed to send channel purchase notification for order %s: %s", order.get("id"), e)
