"""Buy flow with product detail, cart +/- buttons, QRIS payment display."""

from __future__ import annotations

import base64
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


def get_main_menu_keyboard(user_id: int = 0):
    rows = [
        [InlineKeyboardButton("🛍️ Daftar Produk", callback_data="menu:produk")],
        [
            InlineKeyboardButton("📦 Cek Stok", callback_data="menu:stok"),
            InlineKeyboardButton("📋 Riwayat Order", callback_data="menu:orders"),
        ],
        [InlineKeyboardButton("❓ Bantuan", callback_data="menu:help")],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def _cancel_button():
    return [InlineKeyboardButton("❌ Batalkan", callback_data="buy:cancel")]


async def _create_order_and_pay(context, user, product, quantity, query=None, message=None):
    """Shared logic: create order, call QRIS API, send QRIS image, or fallback text."""
    total = product["price"] * quantity
    qris_nominal = total + 500
    expires_at = (datetime.now(tz=timezone(timedelta(hours=7))) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"

    try:
        db.create_order(
            order_id, user.id, user.username, user.first_name,
            quantity, total, product_id=product["id"],
            qris_nominal=qris_nominal, expires_at=expires_at,
        )
    except Exception as exc:
        logger.exception("Gagal membuat order: %s", exc)
        uid = user.id or 0
        text = "Maaf, gagal membuat order. Coba lagi."
        if query:
            await query.edit_message_text(text, reply_markup=get_main_menu_keyboard(uid))
        elif message:
            await message.reply_text(text, reply_markup=get_main_menu_keyboard(uid))
        return None, None

    qris_image_url = None
    if klikqris.is_active():
        try:
            result = await klikqris.get().create_qris(
                order_id=order_id,
                amount=qris_nominal,
                keterangan=f"{product['name']} x{quantity}",
            )
            qris_data = result.get("data") or {}
            qris_image_url = qris_data.get("qris_image") or qris_data.get("image_url") or qris_data.get("url")
            db.set_order_qris_ref(order_id, order_id)
            logger.info("QRIS created for %s — image: %s", order_id, bool(qris_image_url))
            logger.debug("QRIS response data keys: %s", list(qris_data.keys()))
        except klikqris.KlikQRISError as e:
            logger.warning("KlikQRIS gagal untuk %s: %s", order_id, e)
        except Exception as e:
            logger.exception("Unexpected error QRIS %s: %s", order_id, e)

    if query:
        try:
            await query.delete_message()
        except Exception:
            pass
    elif message:
        try:
            await message.delete()
        except Exception:
            pass

    caption = (
        f"✅ ORDER DIBUAT\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {order_id}\n"
        f"📦 Produk: {product['name']}\n"
        f"🔢 Jumlah: {quantity} akun\n"
        f"💰 Total Bayar: Rp {format_rupiah(total)}\n"
        f"💳 Nominal QRIS: Rp {format_rupiah(qris_nominal)}\n"
        f"⏳ Status: menunggu pembayaran\n"
        f"⏰ Expired: 30 menit\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 Scan QRIS di atas untuk bayar.\n"
        "Akun dikirim otomatis setelah bayar. 🤖\n"
        "Cek status: /myorders"
    )

    sent_msg = None
    if qris_image_url:
        try:
            if qris_image_url.startswith("data:"):
                header, b64data = qris_image_url.split(",", 1)
                img_bytes = base64.b64decode(b64data)
                photo_file = io.BytesIO(img_bytes)
                photo_file.name = f"qris_{order_id}.png"
                sent_msg = await context.bot.send_photo(
                    chat_id=user.id,
                    photo=photo_file,
                    caption=caption,
                )
            else:
                sent_msg = await context.bot.send_photo(
                    chat_id=user.id,
                    photo=qris_image_url,
                    caption=caption,
                )
            logger.info("QRIS image sent for %s", order_id)
        except Exception as e:
            logger.warning("Gagal kirim QRIS image %s: %s. Fallback ke text.", order_id, e)
            sent_msg = None

    if sent_msg is None:
        text = (
            f"*✅ ORDER DIBUAT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{order_id}`\n"
            f"📦 Produk: *{product['name']}*\n"
            f"🔢 Jumlah: *{quantity}* akun\n"
            f"💰 Total Bayar: *Rp {format_rupiah(total)}*\n"
            f"💳 Nominal QRIS: *Rp {format_rupiah(qris_nominal)}*\n"
            f"⏳ Status: menunggu pembayaran\n"
            f"⏰ Expired: 30 menit\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Pembayaran QRIS sedang diproses. 🔄\n"
            "Cek status di /myorders."
        )
        sent_msg = await context.bot.send_message(
            chat_id=user.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )

    if sent_msg:
        db.set_order_qris_message_id(order_id, sent_msg.message_id)

    context.user_data.clear()
    return order_id, sent_msg


def register(app: Application) -> None:
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("beli", cmd_beli),
            CallbackQueryHandler(handle_select_product, pattern=r"^buy:\d+$"),
            CallbackQueryHandler(handle_cancel_btn, pattern=r"^buy:cancel$"),
        ],
        states={
            JUMLAH: [
                CallbackQueryHandler(handle_cancel_btn, pattern=r"^buy:cancel$"),
                CallbackQueryHandler(handle_cart_action, pattern=r"^cart:(minus|plus|custom|input)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_jumlah),
            ],
            KONFIRMASI: [
                CallbackQueryHandler(handle_cancel_btn, pattern=r"^buy:cancel$"),
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


async def handle_cancel_btn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data.clear()
    uid = (update.effective_user.id or 0) if update.effective_user else 0
    if query:
        await query.edit_message_text("Dibatalkan. ❌", reply_markup=get_main_menu_keyboard(uid))
    return ConversationHandler.END


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
            f"🛒 {p['name']} - Rp {format_rupiah(p['price'])} (📦 {stock})",
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append(_cancel_button())

    await message.reply_text(
        "*🛍️ Pilih Produk*\n\nPilih produk yang ingin dibeli:",
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
        f"*📋 Detail Produk*\n"
        f"{detail_text}"
        f"*💰 Harga*\n"
        f"Semua jumlah     : Rp {format_rupiah(product['price'])} / akun\n\n"
        f"*📦 Stok*\n"
        f"• Tersedia : {stock_text}\n"
        f"• Minimal : 1 akun\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*🛒 Pesanan Anda*\n"
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
        [InlineKeyboardButton("⌨️ Ketik Jumlah Manual", callback_data="cart:input")],
        [InlineKeyboardButton(f"💳 Bayar via QRIS - Rp {format_rupiah(total)}", callback_data="cart:custom")],
        _cancel_button(),
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
            f"*⌨️ Masukkan Jumlah*\n\n"
            f"Produk: *{product['name']}*\n"
            f"Harga: *Rp {format_rupiah(product['price'])}/akun*\n"
            f"Stok: *{stock if stock else '∞'}*\n\n"
            f"Ketik jumlah (angka), lalu kirim.\n"
            f"Contoh: ketik *5* untuk beli 5 akun.",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = "input_qty"
        return JUMLAH
    elif action == "custom":
        user = update.effective_user
        if user is None:
            return ConversationHandler.END

        stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
        if stock is not None and qty > stock:
            await query.edit_message_text(
                f"Stok tidak cukup. Tersedia: *{stock}* akun.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard(user.id),
            )
            return ConversationHandler.END

        await query.edit_message_text("⏳ Membuat order & QRIS...", parse_mode=ParseMode.MARKDOWN)
        order_id, sent_msg = await _create_order_and_pay(context, user, product, qty, query=query)
        return ConversationHandler.END

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
        await message.reply_text("Masukkan angka yang valid.")
        return JUMLAH

    if qty < 1:
        await message.reply_text("Minimal 1 akun.")
        return JUMLAH

    product = context.user_data.get("product")
    if not product:
        await message.reply_text("Sesi expired. /beli untuk mulai lagi.")
        return ConversationHandler.END

    stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
    if stock is not None and qty > stock:
        await message.reply_text(
            f"Stok tidak cukup. Tersedia: *{stock}* akun.\n"
            f"Ketik jumlah lain atau /cancel untuk batal.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return JUMLAH

    user = update.effective_user
    if user is None:
        await message.reply_text("Gagal memproses.")
        return ConversationHandler.END

    await message.reply_text(
        f"⏳ Membuat order untuk *{product['name']}* x{qty}...",
        parse_mode=ParseMode.MARKDOWN,
    )
    order_id, sent_msg = await _create_order_and_pay(context, user, product, qty, message=message)
    return ConversationHandler.END


async def _show_confirm(query, context, product, qty):
    total = product["price"] * qty

    text = (
        f"*✅ Konfirmasi Pesanan*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Produk: *{product['name']}*\n"
        f"🔢 Jumlah: *{qty}* akun\n"
        f"💰 Harga: Rp {format_rupiah(product['price'])}/akun\n"
        f"💵 Total: *Rp {format_rupiah(total)}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Lanjut ke pembayaran?"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Konfirmasi & Bayar", callback_data="confirm:yes"),
            InlineKeyboardButton("⬅️ Batal", callback_data="confirm:no"),
        ],
        _cancel_button(),
    ])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END

    await query.answer()

    choice = query.data.split(":")[1] if query.data else ""

    if choice == "no":
        product = context.user_data.get("product")
        qty = context.user_data.get("qty", 1)
        if product:
            stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
            await _show_product_detail(query, product, qty, stock)
            return JUMLAH
        context.user_data.clear()
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await query.edit_message_text("Dibatalkan. ❌", reply_markup=get_main_menu_keyboard(uid))
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

    stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
    if stock is not None and quantity > stock:
        await query.edit_message_text(
            f"Stok tidak cukup. Tersedia: *{stock}* akun.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard(user.id),
        )
        return ConversationHandler.END

    await query.edit_message_text("⏳ Membuat order & QRIS...", parse_mode=ParseMode.MARKDOWN)
    order_id, sent_msg = await _create_order_and_pay(context, user, product, quantity, query=query)
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message = update.message
    if message is not None:
        uid = (update.effective_user.id or 0) if update.effective_user else 0
        await message.reply_text("Dibatalkan. ❌", reply_markup=get_main_menu_keyboard(uid))
    return ConversationHandler.END


async def cmd_myorders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        orders = db.get_user_orders(user_id)

        if not orders:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Daftar Produk", callback_data="menu:produk")],
                [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
            ])
            await update.message.reply_text("Belum ada orderan. 🛒", reply_markup=keyboard)
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
                    dt_obj = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                    created_wib = dt_obj.strftime("%d %B %Y pukul %H:%M WIB")
                except Exception:
                    created_wib = created
            else:
                created_wib = "-"

            lines.append(
                f"📋 {order_id}\n"
                f"📦 Produk: {product_name}\n"
                f"🔢 Jumlah: {qty} akun\n"
                f"💰 Total: Rp {format_rupiah(total)}\n"
                f"Status: {emoji} {status}\n"
                f"📅 Tanggal: {created_wib}\n"
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Beli Lagi", callback_data="menu:produk")],
            [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
        ])

        await update.message.reply_text(
            "*📋 Riwayat Order*\n\n" + "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.exception("cmd_myorders error: %s", e)
        try:
            await update.effective_message.reply_text("Maaf, ada masalah. Coba lagi.")
        except Exception:
            pass
