"""Buy flow with inline keyboard buttons.

- Menu button: buy:<product_id>
- Conversation: JUMLAH -> KONFIRMASI -> pembayaran QRIS -> auto deliver
"""

from __future__ import annotations

import io
import logging
import secrets
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import db
from payments import klikqris

logger = logging.getLogger(__name__)

JUMLAH = 0
KONFIRMASI = 1


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def get_main_menu_keyboard(user_id: int = 0):
    rows = [
        [InlineKeyboardButton("Daftar Produk", callback_data="menu:produk")],
        [
            InlineKeyboardButton("Cek Stok", callback_data="menu:stok"),
            InlineKeyboardButton("Riwayat Order", callback_data="menu:orders"),
        ],
        [InlineKeyboardButton("Bantuan", callback_data="menu:help")],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton("Admin Panel", callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def register(app: Application) -> None:
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("beli", cmd_beli),
            CallbackQueryHandler(handle_select_product, pattern=r"^buy:\d+$"),
        ],
        states={
            JUMLAH: [
                CallbackQueryHandler(handle_quick_qty, pattern=r"^qty:\d+$"),
                CallbackQueryHandler(handle_custom_qty, pattern=r"^qty:custom$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_jumlah),
            ],
            KONFIRMASI: [
                CallbackQueryHandler(handle_confirm, pattern=r"^confirm:(yes|no)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_message=False,
        per_chat=True,
        conversation_timeout=600,
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("myorders", cmd_myorders))
    app.add_handler(CommandHandler("pesanan", cmd_myorders))


async def cmd_beli(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None:
        return ConversationHandler.END

    products = db.get_active_products()
    if not products:
        await message.reply_text("Belum ada produk. Tunggu admin menambah produk.")
        return ConversationHandler.END

    buttons = []
    for p in products:
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        buttons.append([InlineKeyboardButton(
            f"{p['name']} - Rp {format_rupiah(p['price'])} (Stok: {stock})",
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append([InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")])

    text = (
        "*Pilih Produk*\n\n"
        "Pilih produk yang ingin dibeli:"
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    return JUMLAH


async def handle_select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END

    await query.answer()

    try:
        product_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return ConversationHandler.END

    product = db.get_product(product_id)
    if not product or not product["is_active"]:
        await query.edit_message_text("Produk tidak tersedia.")
        return ConversationHandler.END

    stock = db.get_stock_count(product_id) if product["stock_type"] == "limited" else None

    if product["stock_type"] == "limited" and (stock is None or stock <= 0):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])
        await query.edit_message_text(
            f"Maaf, stok *{product['name']}* kosong.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    context.user_data["product_id"] = product_id
    context.user_data["product"] = product

    buttons = []
    max_qty = min(stock, 20) if stock else 20
    for qty in [1, 2, 3, 5, 10]:
        if qty <= max_qty:
            total = product["price"] * qty
            buttons.append([InlineKeyboardButton(
                f"{qty} - Rp {format_rupiah(total)}",
                callback_data=f"qty:{qty}",
            )])

    buttons.append([InlineKeyboardButton("Jumlah Lainnya", callback_data="qty:custom")])
    buttons.append([InlineKeyboardButton("Kembali", callback_data=f"buy:{product_id}")])

    stock_text = f"{stock} akun" if stock else "Unlimited"
    text = (
        f"*{product['name']}*\n\n"
        f"{product.get('description', '')}\n"
        f"Harga: *Rp {format_rupiah(product['price'])}/akun*\n"
        f"Stok: *{stock_text}*\n\n"
        "Pilih jumlah:"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

    context.user_data["state"] = "select_qty"
    return JUMLAH


async def handle_quick_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return JUMLAH

    await query.answer()

    try:
        qty = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return JUMLAH

    return await _process_qty(query, context, qty)


async def handle_custom_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return JUMLAH

    await query.answer()

    product = context.user_data.get("product")
    stock = db.get_stock_count(product["id"]) if product and product["stock_type"] == "limited" else None
    stock_text = f"{stock} akun" if stock else "∞"

    await query.edit_message_text(
        f"*Masukkan Jumlah*\n\n"
        f"Stok tersedia: *{stock_text}*\n"
        f"Harga: *Rp {format_rupiah(product['price'])}/akun*\n\n"
        f"Ketik jumlah akun (contoh: `7`):",
        parse_mode=ParseMode.MARKDOWN,
    )
    return JUMLAH


async def _process_qty(query_or_message, context, qty: int) -> int:
    product = context.user_data.get("product")
    if not product:
        return ConversationHandler.END

    product_id = product["id"]
    stock = db.get_stock_count(product_id) if product["stock_type"] == "limited" else None

    if stock is not None and qty > stock:
        msg = query_or_message
        if hasattr(msg, "edit_message_text"):
            await msg.edit_message_text(
                f"Stok tidak cukup. Tersedia: *{stock}* akun.",
                parse_mode=ParseMode.MARKDOWN,
            )
        return JUMLAH

    total = product["price"] * qty
    context.user_data["quantity"] = qty
    context.user_data["total"] = total

    confirm_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Konfirmasi & Bayar", callback_data="confirm:yes"),
            InlineKeyboardButton("Batal", callback_data="confirm:no"),
        ]
    ])

    text = (
        f"*Pesanan Kamu*\n\n"
        f"Produk: *{product['name']}*\n"
        f"Jumlah: *{qty}* akun\n"
        f"Harga: Rp {format_rupiah(product['price'])}/akun\n"
        f"Total: *Rp {format_rupiah(total)}*\n\n"
        "Klik *Konfirmasi & Bayar* untuk melanjutkan."
    )

    if hasattr(query_or_message, "edit_message_text"):
        await query_or_message.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_keyboard)
    else:
        await query_or_message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_keyboard)

    return KONFIRMASI


async def receive_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None:
        return JUMLAH

    text = message.text.strip()
    try:
        qty = int(text)
    except ValueError:
        await message.reply_text("Jumlah tidak valid. Masukkan angka >= 1. /cancel untuk batal.")
        return JUMLAH

    if qty < 1:
        await message.reply_text("Jumlah minimal 1. /cancel untuk batal.")
        return JUMLAH

    product = context.user_data.get("product")
    if not product:
        await message.reply_text("Sesi expired. Mulai lagi: /beli")
        return ConversationHandler.END

    product_id = product["id"]
    stock = db.get_stock_count(product_id) if product["stock_type"] == "limited" else None

    if stock is not None and qty > stock:
        await message.reply_text(
            f"Stok tidak cukup. Tersedia: *{stock}* akun.\n"
            "Masukkan jumlah lebih kecil atau /cancel.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return JUMLAH

    total = product["price"] * qty
    context.user_data["quantity"] = qty
    context.user_data["total"] = total

    confirm_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Konfirmasi & Bayar", callback_data="confirm:yes"),
            InlineKeyboardButton("Batal", callback_data="confirm:no"),
        ]
    ])

    text = (
        f"*Pesanan Kamu*\n\n"
        f"Produk: *{product['name']}*\n"
        f"Jumlah: *{qty}* akun\n"
        f"Harga: Rp {format_rupiah(product['price'])}/akun\n"
        f"Total: *Rp {format_rupiah(total)}*\n\n"
        "Klik *Konfirmasi & Bayar* untuk melanjutkan."
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_keyboard)
    return KONFIRMASI


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END

    await query.answer()

    choice = query.data.split(":")[1] if query.data else ""

    if choice == "no":
        context.user_data.clear()
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await query.edit_message_text(
            "Dibatalkan.",
            reply_markup=get_main_menu_keyboard(uid),
        )
        return ConversationHandler.END

    product = context.user_data.get("product")
    quantity = context.user_data.get("quantity")
    total = context.user_data.get("total")

    if not product or quantity is None or total is None:
        context.user_data.clear()
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await query.edit_message_text(
            "Sesi order sudah berakhir. Mulai lagi:",
            reply_markup=get_main_menu_keyboard(uid),
        )
        return ConversationHandler.END

    user = update.effective_user
    if user is None:
        context.user_data.clear()
        await query.edit_message_text("Gagal membuat order: user tidak dikenal.")
        return ConversationHandler.END

    order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"

    try:
        db.create_order(order_id, user.id, user.username, user.first_name, quantity, total, product_id=product["id"])
    except Exception as exc:
        logger.exception("Gagal membuat order: %s", exc)
        context.user_data.clear()
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await query.edit_message_text(
            "Maaf, gagal membuat order. Coba lagi.",
            reply_markup=get_main_menu_keyboard(uid),
        )
        return ConversationHandler.END

    qris_image_url = None
    if klikqris.is_active():
        try:
            result = await klikqris.get().create_qris(
                order_id=order_id,
                amount=total,
                keterangan=f"{product['name']} x{quantity}",
            )
            qris_data = result.get("data") or {}
            qris_image_url = qris_data.get("qris_image")
            db.set_order_qris_ref(order_id, order_id)
            logger.info("QRIS created for %s", order_id)
        except klikqris.KlikQRISError as e:
            logger.warning("KlikQRIS gagal untuk %s: %s", order_id, e)
        except Exception as e:
            logger.exception("Unexpected error QRIS %s: %s", order_id, e)

    context.user_data.clear()

    if qris_image_url:
        caption = (
            f"Order *#{order_id}* dibuat!\n\n"
            f"Produk: *{product['name']}*\n"
            f"Jumlah: *{quantity}* akun\n"
            f"Total: *Rp {format_rupiah(total)}*\n\n"
            "Scan QR di atas untuk bayar via QRIS.\n"
            "Bot otomatis mengirim akun setelah pembayaran berhasil."
        )
        try:
            await query.delete_message()
        except Exception:
            pass
        await context.bot.send_photo(
            chat_id=user.id,
            photo=qris_image_url,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        text = (
            f"Order *#{order_id}* dibuat!\n\n"
            f"Produk: *{product['name']}*\n"
            f"Total: *Rp {format_rupiah(total)}*\n\n"
            "Pembayaran QRIS sedang diproses.\n"
            "Cek status di /myorders."
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message = update.message
    if message is not None:
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await message.reply_text("Dibatalkan.", reply_markup=get_main_menu_keyboard(uid))
    return ConversationHandler.END


async def cmd_myorders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        orders = db.get_user_orders(user_id)

        if not orders:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Daftar Produk", callback_data="menu:produk")],
                [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
            ])
            await update.message.reply_text("Belum ada orderan.", reply_markup=keyboard)
            return

        recent = orders[:20]
        _STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦"}

        lines = ["*Riwayat Order*\n"]
        for o in recent:
            order_id = o.get("id", "")
            qty = o.get("quantity", 0)
            total = o.get("total", 0)
            status = o.get("status", "pending")
            created_at = o.get("created_at", "")
            emoji = _STATUS_EMOJI.get(status, "⏳")
            product = db.get_product(o.get("product_id", 1))
            product_name = product["name"] if product else "N/A"
            lines.append(f"#{order_id} | {product_name} x{qty} | Rp {format_rupiah(total)} | {emoji} {status}")
            lines.append(str(created_at))
            lines.append("")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Beli Lagi", callback_data="menu:produk")],
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])

        await update.message.reply_text("\n".join(lines).rstrip(), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e:
        logger.exception("cmd_myorders error: %s", e)
        try:
            await update.effective_message.reply_text("Maaf, ada masalah. Coba lagi.")
        except Exception:
            pass
