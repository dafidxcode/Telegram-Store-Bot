"""Buy flow with product detail, cart +/- buttons, QRIS payment display."""

from __future__ import annotations

import io
import logging
import secrets
from datetime import datetime, timezone, timedelta

import qrcode
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
from handlers.start import (
    btn_home,
    btn_back,
    btn_cancel_payment,
    global_nav_keyboard,
    escape_md,
    get_lang,
    t,
    format_rupiah,
)

logger = logging.getLogger(__name__)

JUMLAH = 0
KONFIRMASI = 1


async def _create_order_and_pay(context, user, product, quantity, query=None, message=None):
    """Shared logic: create order, call QRIS API, send QRIS image, or fallback text."""
    lang = get_lang(context, user.id)
    total = product["price"] * quantity
    qris_nominal = total
    expires_at = (datetime.now(tz=timezone(timedelta(hours=7))) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"

    try:
        db.create_order(
            order_id, user.id, user.username, user.first_name,
            quantity, total, product_id=product["id"],
            qris_nominal=qris_nominal, expires_at=expires_at,
        )
    except Exception as exc:
        logger.exception("Failed to create order: %s", exc)
        uid = user.id or 0
        text = t("admin_try_again", lang)
        if query:
            await query.edit_message_text(text, reply_markup=get_main_menu_keyboard(uid, lang))
        elif message:
            await message.reply_text(text, reply_markup=get_main_menu_keyboard(uid, lang))
        return None, None

    qris_image_url = None
    qris_content = None
    qris_image_b64 = None
    api_expired_at = ""
    api_status = "PENDING"
    if klikqris.is_active():
        try:
            result = await klikqris.get().create_qris(
                order_id=order_id,
                amount=qris_nominal,
                keterangan=f"{product['name']} x{quantity}",
            )
            qris_data = result.get("data") or {}
            logger.info("KlikQRIS response keys: %s", list(qris_data.keys()))

            api_expired_at = qris_data.get("expired_at", "")
            api_status = qris_data.get("status", "PENDING")

            raw_qris_image = (
                qris_data.get("qris_image")
                or qris_data.get("image_url")
                or qris_data.get("qr_image")
            )
            qris_image_url = qris_data.get("qris_url")
            qris_content = (
                qris_data.get("qris_content")
                or qris_data.get("qris_data")
                or qris_data.get("qris_payload")
                or qris_data.get("qrContent")
            )

            if raw_qris_image:
                qris_image_b64 = klikqris.KlikQRIS.decode_qris_image(raw_qris_image)

            db.set_order_qris_ref(order_id, order_id)
            logger.info("QRIS created for %s — has_image_url=%s, has_b64=%s, has_content=%s",
                        order_id, bool(qris_image_url), bool(qris_image_b64), bool(qris_content))
        except klikqris.KlikQRISError as e:
            logger.warning("KlikQRIS create failed for %s: %s", order_id, e)
        except Exception as e:
            logger.exception("Unexpected error creating QRIS %s: %s", order_id, e)

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
        f"✅ {t('order_created', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {order_id}\n"
        f"📦 {t('product_label', lang)}: {escape_md(product['name'])}\n"
        f"🔢 {t('quantity_label', lang)}: {quantity} {t('accounts_label', lang)}\n"
        f"💰 Total: Rp {format_rupiah(qris_nominal)}\n"
        f"⏳ {t('status_label', lang)}: {api_status}\n"
        f"⏰ {t('expires_label', lang)}: {api_expired_at}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{t('scan_qris', lang)}\n"
        f"{t('auto_deliver', lang)}\n"
        f"{t('check_myorders', lang)}"
    )

    order_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel_order", lang), callback_data=f"order:cancel:{order_id}")],
    ])

    sent_msg = None

    # --- Strategy 1: decoded base64 PNG from qris_image field ---
    if sent_msg is None and qris_image_b64:
        try:
            photo_file = io.BytesIO(qris_image_b64)
            photo_file.seek(0)
            photo_file.name = f"qris_{order_id}.png"
            logger.info("Sending QRIS photo (b64 len=%d, file name=%s)", len(qris_image_b64), photo_file.name)
            sent_msg = await context.bot.send_photo(
                chat_id=user.id,
                photo=photo_file,
                caption=caption,
                reply_markup=order_keyboard,
            )
            logger.info("QRIS base64 image sent for %s, msg_id=%s", order_id, sent_msg.message_id if sent_msg else None)
        except Exception as e:
            logger.warning("Failed to send QRIS base64 for %s: %s", order_id, e, exc_info=True)
            sent_msg = None

    # --- Strategy 2: URL from qris_url ---
    if sent_msg is None and qris_image_url:
        try:
            logger.info("Sending QRIS photo via URL: %s", qris_image_url[:80])
            sent_msg = await context.bot.send_photo(
                chat_id=user.id,
                photo=qris_image_url,
                caption=caption,
                reply_markup=order_keyboard,
            )
            logger.info("QRIS image URL sent for %s, msg_id=%s", order_id, sent_msg.message_id if sent_msg else None)
        except Exception as e:
            logger.warning("Failed to send QRIS URL for %s: %s", order_id, e, exc_info=True)
            sent_msg = None

    # --- Strategy 3: render QR code from qris_content string ---
    if sent_msg is None and qris_content:
        try:
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(qris_content)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            buf.name = f"qris_{order_id}.png"
            sent_msg = await context.bot.send_photo(
                chat_id=user.id,
                photo=buf,
                caption=caption,
                reply_markup=order_keyboard,
            )
            logger.info("QRIS rendered from qris_content for %s", order_id)
        except Exception as e:
            logger.warning("Failed to render QRIS content for %s: %s", order_id, e)
            sent_msg = None

    # --- Fallback: text only ---
    if sent_msg is None:
        text = (
            f"*✅ {t('order_created', lang)}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{order_id}`\n"
            f"📦 {t('product_label', lang)}: *{escape_md(product['name'])}*\n"
            f"🔢 {t('quantity_label', lang)}: *{quantity}* {t('accounts_label', lang)}\n"
            f"💰 Total: *Rp {format_rupiah(qris_nominal)}*\n"
            f"⏳ {t('status_label', lang)}: *{api_status}*\n"
            f"⏰ {t('expires_label', lang)}: *{api_expired_at}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('qr_processing', lang)}"
        )
        sent_msg = await context.bot.send_message(
            chat_id=user.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=order_keyboard,
        )

    if sent_msg:
        db.set_order_qris_message_id(order_id, sent_msg.message_id)

    context.user_data.pop("product_id", None)
    context.user_data.pop("product", None)
    context.user_data.pop("qty", None)
    context.user_data.pop("state", None)
    context.user_data.pop("admin_state", None)
    return order_id, sent_msg


async def handle_order_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel order, delete QRIS message, show home menu silently."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) < 3:
        return
    order_id = parts[2]

    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        return

    db.update_order_status(order_id, "cancelled")
    db.release_stock(order_id)
    logger.info("Order %s cancelled by user via Cancel button", order_id)

    user_id = update.effective_user.id if update.effective_user else 0
    chat_id = query.message.chat_id if query.message else user_id

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
    except Exception:
        pass

    lang = get_lang(context, user_id)
    user = update.effective_user
    from handlers.start import build_home_text, get_main_menu_keyboard
    text = build_home_text(user, lang)
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(user_id, lang),
    )


def register(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(handle_order_cancel, pattern=r"^order:cancel:"))
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
    user_id = (update.effective_user.id or 0) if update.effective_user else 0
    lang = get_lang(context, user_id)
    context.user_data.pop("product_id", None)
    context.user_data.pop("product", None)
    context.user_data.pop("qty", None)
    context.user_data.pop("state", None)
    context.user_data.pop("admin_state", None)
    if query:
        await query.edit_message_text(t("cancelled", lang), reply_markup=get_main_menu_keyboard(user_id, lang))
    return ConversationHandler.END


async def cmd_beli(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None:
        return ConversationHandler.END

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    products = db.get_active_products()
    if not products:
        await message.reply_text(t("no_products_available", lang))
        return ConversationHandler.END

    buttons = []
    for p in products:
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        buttons.append([InlineKeyboardButton(
            f"🛒 {escape_md(p['name'])} - Rp {format_rupiah(p['price'])} (📦 {stock})",
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append([InlineKeyboardButton(t("cancel", lang), callback_data="buy:cancel")])

    await message.reply_text(
        f"*{t('select_product_title', lang)}*\n\n{t('choose_product', lang)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return JUMLAH


async def handle_select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END

    await query.answer()

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    try:
        product_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return ConversationHandler.END

    product = db.get_product(product_id)
    if not product or not product["is_active"]:
        await query.edit_message_text(t("product_not_available", lang))
        return ConversationHandler.END

    stock = db.get_stock_count(product_id) if product["stock_type"] == "limited" else None
    if product["stock_type"] == "limited" and (stock is None or stock <= 0):
        await query.edit_message_text(
            t("out_of_stock", lang, name=escape_md(product['name'])),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard(user_id, lang),
        )
        return ConversationHandler.END

    context.user_data["product_id"] = product_id
    context.user_data["product"] = product
    context.user_data["qty"] = 1

    await _show_product_detail(query, product, 1, stock, lang)
    return JUMLAH


async def _show_product_detail(query, product, qty, stock, lang="en"):
    total = product["price"] * qty
    stock_text = f"{stock} {t('accounts', lang)}" if stock else t("unlimited", lang)
    price_str = format_rupiah(product['price'])

    detail = product.get("description", "")
    detail_lines = detail.split("\n") if detail else []
    detail_text = ""
    if detail_lines:
        detail_text = "\n".join(f"• {line.strip()}" for line in detail_lines if line.strip()) + "\n\n"

    text = (
        f"*{escape_md(product['name'])}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{t('product_details', lang)}*\n"
        f"{detail_text}"
        f"*{t('pricing', lang)}*\n"
        f"{t('pricing_per_account', lang, price=price_str)}\n\n"
        f"*{t('stock_heading', lang)}*\n"
        f"• {t('available', lang)} : {stock_text}\n"
        f"• {t('minimum', lang)}   : 1 {t('accounts', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{t('your_order', lang)}*\n"
        f"{t('quantity', lang)}    : {qty} {t('accounts', lang)}\n"
        f"{t('price', lang)}       : Rp {price_str}\n"
        f"{t('total', lang)}       : Rp {format_rupiah(total)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="cart:minus"),
            InlineKeyboardButton(str(qty), callback_data="cart:noop"),
            InlineKeyboardButton("➕", callback_data="cart:plus"),
        ],
        [InlineKeyboardButton(t("enter_qty_manually", lang), callback_data="cart:input")],
        [InlineKeyboardButton(t("pay_qris", lang, total=format_rupiah(total)), callback_data="cart:custom")],
        [InlineKeyboardButton(t("cancel", lang), callback_data="buy:cancel")],
    ])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def handle_cart_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return JUMLAH

    await query.answer()

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

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
            f"*{t('enter_quantity_title', lang)}*\n\n"
            f"{t('product_label', lang)}: *{escape_md(product['name'])}*\n"
            f"{t('price', lang)}: *Rp {format_rupiah(product['price'])}/{t('accounts', lang)}*\n"
            f"{t('stock', lang)}: *{stock if stock else '∞'}*\n\n"
            f"{t('type_number', lang)}\n"
            f"{t('example_type', lang, n=5)}",
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
                t("insufficient_stock", lang, stock=stock),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard(user_id, lang),
            )
            return ConversationHandler.END

        await query.edit_message_text(t("creating_order", lang), parse_mode=ParseMode.MARKDOWN)
        order_id, sent_msg = await _create_order_and_pay(context, user, product, qty, query=query)
        return ConversationHandler.END

    context.user_data["qty"] = qty
    await _show_product_detail(query, product, qty, stock, lang)
    return JUMLAH


async def receive_manual_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None:
        return JUMLAH

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    text = message.text.strip()
    try:
        qty = int(text)
    except ValueError:
        await message.reply_text(t("admin_price_number", lang))
        return JUMLAH

    if qty < 1:
        await message.reply_text(t("admin_price_positive", lang))
        return JUMLAH

    product = context.user_data.get("product")
    if not product:
        await message.reply_text(t("session_expired", lang))
        return ConversationHandler.END

    stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
    if stock is not None and qty > stock:
        await message.reply_text(
            t("insufficient_stock", lang, stock=stock) + "\n" + t("type_another_or_cancel", lang),
            parse_mode=ParseMode.MARKDOWN,
        )
        return JUMLAH

    user = update.effective_user
    if user is None:
        await message.reply_text(t("admin_try_again", lang))
        return ConversationHandler.END

    await message.reply_text(
        t("creating_order_for", lang, name=escape_md(product['name']), qty=qty),
        parse_mode=ParseMode.MARKDOWN,
    )
    order_id, sent_msg = await _create_order_and_pay(context, user, product, qty, message=message)
    return ConversationHandler.END


async def _show_confirm(query, context, product, qty):
    user_id = query.from_user.id if query.from_user else 0
    lang = get_lang(context, user_id)
    total = product["price"] * qty

    text = (
        f"*{t('order_confirmation', lang)}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 {t('product_label', lang)}: *{escape_md(product['name'])}*\n"
        f"🔢 {t('quantity_label', lang)}: *{qty}* {t('accounts_label', lang)}\n"
        f"💰 {t('price', lang)}: Rp {format_rupiah(product['price'])}/{t('accounts', lang)}\n"
        f"💵 {t('total', lang)}: *Rp {format_rupiah(total)}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{t('proceed_payment', lang)}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("confirm_pay", lang), callback_data="confirm:yes"),
            InlineKeyboardButton(t("btn_back", lang), callback_data="confirm:no"),
        ],
        [InlineKeyboardButton(t("cancel", lang), callback_data="buy:cancel")],
    ])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END

    await query.answer()

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    choice = query.data.split(":")[1] if query.data else ""

    if choice == "no":
        product = context.user_data.get("product")
        qty = context.user_data.get("qty", 1)
        if product:
            stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
            await _show_product_detail(query, product, qty, stock, lang)
            return JUMLAH
        context.user_data.clear()
        await query.edit_message_text(t("cancelled", lang), reply_markup=get_main_menu_keyboard(user_id, lang))
        return ConversationHandler.END

    product = context.user_data.get("product")
    quantity = context.user_data.get("qty", 1)

    if not product:
        context.user_data.clear()
        await query.edit_message_text(t("session_expired", lang), reply_markup=get_main_menu_keyboard(user_id, lang))
        return ConversationHandler.END

    user = update.effective_user
    if user is None:
        context.user_data.clear()
        await query.edit_message_text(t("admin_try_again", lang))
        return ConversationHandler.END

    stock = db.get_stock_count(product["id"]) if product["stock_type"] == "limited" else None
    if stock is not None and quantity > stock:
        await query.edit_message_text(
            t("insufficient_stock", lang, stock=stock),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard(user_id, lang),
        )
        return ConversationHandler.END

    await query.edit_message_text(t("creating_order", lang), parse_mode=ParseMode.MARKDOWN)
    order_id, sent_msg = await _create_order_and_pay(context, user, product, quantity, query=query)
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message = update.message
    if message is not None:
        user_id = update.effective_user.id if update.effective_user else 0
        lang = get_lang(context, user_id)
        await message.reply_text(t("cancelled", lang), reply_markup=get_main_menu_keyboard(user_id, lang))
    return ConversationHandler.END


async def cmd_myorders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        lang = get_lang(context, user_id)
        orders = db.get_user_orders(user_id)

        if not orders:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
                [btn_home(lang)],
            ])
            await update.message.reply_text(t("no_orders", lang), reply_markup=keyboard)
            return

        _STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦", "waiting_payment": "⏳"}
        recent = orders[:10]
        lines = []

        for o in recent:
            oid = o.get("id", "")
            qty = o.get("quantity", 0)
            total = o.get("total", 0)
            status = o.get("status", "pending")
            emoji = _STATUS_EMOJI.get(status, "⏳")
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"

            created = o.get("created_at", "")
            if created:
                try:
                    dt_obj = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                    created_wib = dt_obj.strftime("%d %B %Y at %-H:%M WIB")
                except Exception:
                    created_wib = created
            else:
                created_wib = "-"

            lines.append(
                f"📋 {oid}\n"
                f"📦 {t('product_label', lang)}: {product_name}\n"
                f"🔢 {t('quantity_label', lang)}: {qty} {t('accounts_label', lang)}\n"
                f"💰 Total: Rp {format_rupiah(total)}\n"
                f"{t('status_label_header', lang)}: {emoji} {status}\n"
                f"📅 {t('date_label', lang)}: {created_wib}\n"
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("buy_again", lang), callback_data="menu:produk")],
            [btn_home(lang)],
        ])

        await update.message.reply_text(
            f"*{t('order_history', lang)}*\n\n" + "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.exception("cmd_myorders error: %s", e)
        try:
            await update.effective_message.reply_text(t("admin_try_again", lang))
        except Exception:
            pass
