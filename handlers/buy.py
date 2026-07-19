"""Buy flow with product detail, cart +/- buttons, QRIS payment display."""

from __future__ import annotations

import io
import logging
import secrets
from datetime import datetime, timezone, timedelta

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


def get_wib_now() -> str:
    return datetime.now(tz=timezone(timedelta(hours=7))).strftime("%d %B %Y pukul %H:%M WIB")


def get_wib_expiry(minutes: int = 30) -> str:
    return datetime.now(tz=timezone(timedelta(hours=7)) + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")


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
                CallbackQueryHandler(handle_cart_action, pattern=r"^cart:(minus|plus|custom|input)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_jumlah),
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

    await message.reply_text(
        "*Pilih Produk*\n\nPilih produk yang ingin dibeli:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
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
        await query.edit_message_text(
            f"Maaf, stok *{product['name']}* kosong.\n\n"
            "Pilih produk lain atau tunggu admin menambah stok.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    context.user_data["product_id"] = product_id
    context.user_data["product"] = product
    context.user_data["qty"] = 1
    context.user_data["state"] = "detail"

    await _show_product_detail(query, product, 1, stock)
    return JUMLAH


async def _show_product_detail(query, product, qty, stock):
    total = product["price"] * qty
    stock_text = f"{stock} akun" if stock else "Unlimited"

    detail = product.get("description", "")
    detail_lines = detail.split("\n") if detail else []
    detail_text = ""
    if detail_lines:
        detail_text = "\n".join(f"• {line.strip()}" for line in detail_lines if line.strip()) + "\n\n"

    text = (
        f"*{product['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Detail Produk*\n"
        f"{detail_text}"
        f"*Harga*\n"
        f"Semua jumlah     : Rp {format_rupiah(product['price'])} / akun\n\n"
        f"*Stok*\n"
        f"• Tersedia : {stock_text}\n"
        f"• Minimal : 1 akun\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Pesanan Anda*\n"
        f"Jumlah      : {qty} akun\n"
        f"Harga       : Rp {format_rupiah(product['price'])}\n"
        f"Total Bayar : Rp {format_rupiah(total)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    minus_disabled = qty <= 1
    plus_disabled = stock is not None and qty >= stock

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="cart:minus"),
            InlineKeyboardButton(str(qty), callback_data="cart:noop"),
            InlineKeyboardButton("➕", callback_data="cart:plus"),
        ],
        [InlineKeyboardButton("Ketik Jumlah Manual", callback_data="cart:input")],
        [InlineKeyboardButton(f"Bayar via QRIS - Rp {format_rupiah(total)}", callback_data="cart:custom")],
    ])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def handle_cart_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return JUMLAH

    await query.answer()

    action = query.data.split(":")[1]
    product = context.user_data.get("product")
    if not product:
        return ConversationHandler.END

    qty = context.user_data.get("qty", 1)
    stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None

    if action == "minus":
        qty = max(1, qty - 1)
    elif action == "plus":
        max_qty = stock if stock else 999
        qty = min(qty + 1, max_qty)
    elif action == "input":
        await query.edit_message_text(
            f"*Masukkan Jumlah*\n\n"
            f"Produk: *{product['name']}*\n"
            f"Harga: *Rp {format_rupiah(product['price'])}/akun*\n"
            f"Stok: *{stock if stock else '∞'}*\n\n"
            f"Ketik jumlah (angka):",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = "input_qty"
        return JUMLAH
    elif action == "custom":
        await _show_confirm(query, context, product, qty)
        return KONFIRMASI

    context.user_data["qty"] = qty
    await _show_product_detail(query, product, qty, stock)
    return JUMLAH


async def receive_manual_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None:
        return JUMLAH

    text = message.text.strip()
    try:
        qty = int(text)
    except ValueError:
        await message.reply_text("Masukkan angka yang valid. /cancel untuk batal.")
        return JUMLAH

    if qty < 1:
        await message.reply_text("Minimal 1 akun. /cancel untuk batal.")
        return JUMLAH

    product = context.user_data.get("product")
    if not product:
        await message.reply_text("Sesi expired. /beli untuk mulai lagi.")
        return ConversationHandler.END

    stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
    if stock is not None and qty > stock:
        await message.reply_text(
            f"Stok tidak cukup. Tersedia: *{stock}* akun.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return JUMLAH

    context.user_data["qty"] = qty

    total = product["price"] * qty
    stock_text = f"{stock} akun" if stock else "Unlimited"
    detail = product.get("description", "")
    detail_lines = detail.split("\n") if detail else []
    detail_text = ""
    if detail_lines:
        detail_text = "\n".join(f"• {line.strip()}" for line in detail_lines if line.strip()) + "\n\n"

    text = (
        f"*{product['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Detail Produk*\n"
        f"{detail_text}"
        f"*Harga*\n"
        f"Semua jumlah     : Rp {format_rupiah(product['price'])} / akun\n\n"
        f"*Stok*\n"
        f"• Tersedia : {stock_text}\n"
        f"• Minimal : 1 akun\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Pesanan Anda*\n"
        f"Jumlah      : {qty} akun\n"
        f"Harga       : Rp {format_rupiah(product['price'])}\n"
        f"Total Bayar : Rp {format_rupiah(total)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="cart:minus"),
            InlineKeyboardButton(str(qty), callback_data="cart:noop"),
            InlineKeyboardButton("➕", callback_data="cart:plus"),
        ],
        [InlineKeyboardButton("Ketik Jumlah Manual", callback_data="cart:input")],
        [InlineKeyboardButton(f"Bayar via QRIS - Rp {format_rupiah(total)}", callback_data="cart:custom")],
    ])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    return JUMLAH


async def _show_confirm(query, context, product, qty):
    total = product["price"] * qty

    text = (
        f"*Konfirmasi Pesanan*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Produk: *{product['name']}*\n"
        f"Jumlah: *{qty}* akun\n"
        f"Harga: Rp {format_rupiah(product['price'])}/akun\n"
        f"Total: *Rp {format_rupiah(total)}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Lanjut ke pembayaran?"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Konfirmasi & Bayar", callback_data="confirm:yes"),
            InlineKeyboardButton("Batal", callback_data="confirm:no"),
        ]
    ])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END

    await query.answer()

    choice = query.data.split(":")[1] if query.data else ""

    if choice == "no":
        context.user_data.clear()
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await query.edit_message_text("Dibatalkan.", reply_markup=get_main_menu_keyboard(uid))
        return ConversationHandler.END

    product = context.user_data.get("product")
    quantity = context.user_data.get("qty", 1)

    if not product:
        context.user_data.clear()
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await query.edit_message_text("Sesi expired. Mulai lagi:", reply_markup=get_main_menu_keyboard(uid))
        return ConversationHandler.END

    user = update.effective_user
    if user is None:
        context.user_data.clear()
        await query.edit_message_text("Gagal membuat order.")
        return ConversationHandler.END

    total = product["price"] * quantity
    qris_nominal = total + 500

    from datetime import datetime as dt, timezone, timedelta
    expires_at = (dt.now(tz=timezone(timedelta(hours=7))) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

    order_id = f"ORD-{dt.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"

    try:
        db.create_order(
            order_id, user.id, user.username, user.first_name,
            quantity, total, product_id=product["id"],
            qris_nominal=qris_nominal, expires_at=expires_at,
        )
    except Exception as exc:
        logger.exception("Gagal membuat order: %s", exc)
        context.user_data.clear()
        uid = user.id or 0
        await query.edit_message_text("Maaf, gagal membuat order. Coba lagi.", reply_markup=get_main_menu_keyboard(uid))
        return ConversationHandler.END

    qris_image_url = None
    if klikqris.is_active():
        try:
            result = await klikqris.get().create_qris(
                order_id=order_id,
                amount=qris_nominal,
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
            f"ORDER DIBUAT\n"
            f"ID: {order_id}\n"
            f"Produk: {product['name']}\n"
            f"Jumlah: {quantity} akun\n"
            f"Total Bayar: Rp {format_rupiah(total)}\n"
            f"Nominal QRIS: Rp {format_rupiah(qris_nominal)}\n"
            f"Status: menunggu pembayaran\n"
            f"Expired: {expires_at}\n\n"
            "Bayar memakai QRIS. Akun akan dikirim otomatis setelah pembayaran terdeteksi."
        )
        try:
            await query.delete_message()
        except Exception:
            pass
        await context.bot.send_photo(
            chat_id=user.id,
            photo=qris_image_url,
            caption=caption,
        )
    else:
        text = (
            f"*ORDER DIBUAT*\n\n"
            f"ID: `{order_id}`\n"
            f"Produk: *{product['name']}*\n"
            f"Jumlah: *{quantity}* akun\n"
            f"Total Bayar: *Rp {format_rupiah(total)}*\n"
            f"Nominal QRIS: *Rp {format_rupiah(qris_nominal)}*\n"
            f"Status: menunggu pembayaran\n"
            f"Expired: `{expires_at}`\n\n"
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

        _STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦", "waiting_payment": "⏳"}
        recent = orders[:10]
        lines = []

        for o in recent:
            order_id = o.get("id", "")
            qty = o.get("quantity", 0)
            total = o.get("total", 0)
            status = o.get("status", "pending")
            emoji = _STATUS_EMOJI.get(status, "⏳")
            product = db.get_product(o.get("product_id", 1))
            product_name = product["name"] if product else "N/A"

            created = o.get("created_at", "")
            if created:
                try:
                    from datetime import datetime as dt
                    dt_obj = dt.strptime(created, "%Y-%m-%d %H:%M:%S")
                    created_wib = dt_obj.strftime("%d %B %Y pukul %H:%M WIB")
                except Exception:
                    created_wib = created
            else:
                created_wib = "-"

            lines.append(
                f"  {order_id}\n"
                f"Produk: {product_name}\n"
                f"Jumlah: {qty} akun\n"
                f"Total: Rp {format_rupiah(total)}\n"
                f"Status: {emoji} {status}\n"
                f"Tanggal: {created_wib}\n"
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Beli Lagi", callback_data="menu:produk")],
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])

        await update.message.reply_text(
            "*Riwayat Order*\n\n" + "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.exception("cmd_myorders error: %s", e)
        try:
            await update.effective_message.reply_text("Maaf, ada masalah. Coba lagi.")
        except Exception:
            pass
