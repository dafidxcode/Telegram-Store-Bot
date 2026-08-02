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


async def send_admin_feedback_notif(bot: Bot, feedback_id: int, user_name: str, message_text: str) -> None:
    """Send immediate notification to Telegram Admin when a new feedback/reply arrives."""
    admin_targets = set()
    if config.ADMIN_USER_ID:
        admin_targets.add(config.ADMIN_USER_ID)
    if config.ADMIN_IDS:
        admin_targets.update(config.ADMIN_IDS)

    if not admin_targets:
        return

    text = (
        f"💬 *FEEDBACK / KRITIK SARAN BARU!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Thread:* `#FB-{feedback_id}`\n"
        f"👤 *Pengguna:* {escape_md(user_name)}\n"
        f"📝 *Pesan:*\n"
        f"_{escape_md(message_text)}_\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Balas Feedback", callback_data=f"admin_reply_fb:{feedback_id}")]
    ])

    for admin_id in admin_targets:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
            )
            logger.info("Feedback notif #FB-%d sent to admin %s", feedback_id, admin_id)
        except Exception as e:
            logger.warning("Failed to send feedback notif #FB-%d to admin %s: %s", feedback_id, admin_id, e)


async def send_channel_new_product_notif(bot: Bot, product: dict) -> None:
    """Send notification to Telegram channel when a new product is added."""
    channel_id = config.get_channel_id()
    if not channel_id:
        return

    try:
        product_name = product.get("name", "Produk Baru")
        price = product.get("price", 0)
        desc = product.get("description", "")
        stock_type = product.get("stock_type", "limited")

        bot_username = ""
        try:
            me = await bot.get_me()
            bot_username = me.username
        except Exception:
            pass

        bot_link = f"https://t.me/{bot_username}" if bot_username else config.get_channel_link()
        stock_info = "⏳ Pre-Order (Proses Manual)" if stock_type == "preorder" else "⚡ Stok Siap Dikirim"

        text = (
            "✨ *PRODUK BARU TERSEDIA!* ✨\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *Produk:* {escape_md(product_name)}\n"
            f"💰 *Harga:* Rp{format_rupiah(price)}\n"
            f"ℹ️ *Status:* {stock_info}\n"
        )
        if desc:
            text += f"📝 *Deskripsi:* _{escape_md(desc)}_\n"

        text += (
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛍️ *Tertarik? Langsung order via bot sekarang!*"
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
        logger.info("Sent new product notification for '%s' to channel %s", product_name, channel_id)
    except Exception as e:
        logger.exception("Failed to send channel new product notification for %s: %s", product.get("name"), e)


async def send_channel_add_stock_notif(bot: Bot, product_name: str, added_count: int, total_stock: int, price: int = 0) -> None:
    """Send notification to Telegram channel when stock is added."""
    channel_id = config.get_channel_id()
    if not channel_id:
        return
    if added_count <= 0:
        return

    try:
        bot_username = ""
        try:
            me = await bot.get_me()
            bot_username = me.username
        except Exception:
            pass

        bot_link = f"https://t.me/{bot_username}" if bot_username else config.get_channel_link()

        text = (
            "🔥 *RESTOK PRODUK!* 🔥\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *Produk:* {escape_md(product_name)}\n"
            f"📥 *Stok Ditambahkan:* +{added_count} akun\n"
            f"📊 *Total Stok Ready:* {total_stock} akun\n"
        )
        if price > 0:
            text += f"💰 *Harga:* Rp{format_rupiah(price)}\n"

        text += (
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ *Stok terbatas! Buruan order sebelum kehabisan!*"
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
        logger.info("Sent add stock notification (+%d) for '%s' to channel %s", added_count, product_name, channel_id)
    except Exception as e:
        logger.exception("Failed to send channel add stock notification for %s: %s", product_name, e)
