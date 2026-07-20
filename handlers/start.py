"""Start, help, and menu command handlers with inline keyboard buttons."""

import logging
from datetime import datetime, timezone, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
import db
import lang as L

logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"


def escape_md(text: str) -> str:
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", DEFAULT_LANG)


def t(key: str, lang: str, **fmt) -> str:
    s = L.T.get(key, {}).get(lang) or L.T.get(key, {}).get(DEFAULT_LANG) or key
    if fmt:
        return s.format(**fmt)
    return s


def get_now_wib() -> str:
    wib = datetime.now(tz=timezone(timedelta(hours=7)))
    return wib.strftime(f"%-d %B %Y at %-H:%M WIB")


def get_greeting(lang: str = "en") -> str:
    hour = datetime.now(tz=timezone(timedelta(hours=7))).hour
    if 4 <= hour < 11:
        return t("good_morning", lang)
    elif 11 <= hour < 15:
        return t("good_afternoon", lang)
    elif 15 <= hour < 18:
        return t("good_evening", lang)
    else:
        return t("good_night", lang)


# ---------------------------------------------------------------------------
# Global navigation buttons
# ---------------------------------------------------------------------------

def btn_home(lang="en"):
    return InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")


def btn_back(lang="en", text=None, data="menu:start"):
    return InlineKeyboardButton(text or t("btn_back", lang), callback_data=data)


def btn_cancel_payment(lang="en"):
    return InlineKeyboardButton(t("btn_cancel_pay", lang), callback_data="global:cancel_payment")


def global_nav_row(lang="en"):
    return [btn_home(lang)]


def global_nav_keyboard(user_id: int = 0, lang="en"):
    return InlineKeyboardMarkup([
        [btn_back(lang), btn_cancel_payment(lang), btn_home(lang)],
    ])


def global_nav_keyboard_simple(user_id: int = 0, lang="en"):
    return InlineKeyboardMarkup([global_nav_row(lang)])


# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

def build_home_text(user, lang: str = "en") -> str:
    sold = db.get_total_sold()
    total_users = db.get_total_users()
    user_orders = db.get_user_order_count(user.id)
    username = escape_md(f"@{user.username}") if user.username else "N/A"
    first_name = escape_md(user.first_name or "friend")
    active_products = db.get_active_products()
    product_count = len(active_products)

    product_lines = []
    for p in active_products:
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        product_lines.append(f"  • {escape_md(p['name'])}: {stock} stock | Rp {format_rupiah(p['price'])}")

    product_stock_text = "\n".join(product_lines) if product_lines else f"  {t('no_products', lang)}"

    return (
        f"{get_greeting(lang)}, {first_name}!\n"
        f"📅 {get_now_wib()}\n"
        f"\n"
        f"{t('welcome', lang, shop=escape_md(config.SHOP_NAME))}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*{t('account_stats', lang)}*\n"
        f"{t('username', lang)} : {username}\n"
        f"ID : {user.id}\n"
        f"{t('total_orders', lang, n=user_orders)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*{t('bot_stats', lang)}*\n"
        f"{t('accounts_sold', lang, n=sold)}\n"
        f"{t('active_products', lang, n=product_count)}\n"
        f"{t('total_users', lang, n=total_users)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*{t('stock_per', lang)}*\n"
        f"{product_stock_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"{t('where_start', lang)}\n"
        f"{t('hint_buy', lang)}\n"
        f"{t('hint_orders', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def build_products_text(lang: str = "en") -> str:
    products = db.get_active_products()
    if not products:
        return t("no_products_yet", lang)

    lines = [f"{t('product_list_title', lang)}\n"]
    for i, p in enumerate(products, 1):
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else t("unlimited", lang)
        duration = f"\n{t('duration', lang)}: {escape_md(p['duration'])}" if p.get("duration") else ""
        desc = f"\n{escape_md(p['description'])}" if p.get("description") else ""

        acct_label = t("accounts", lang) if p['stock_type'] == 'limited' else ""
        lines.append(
            f"*{i}. {escape_md(p['name'])}*\n"
            f"{desc}{duration}\n"
            f"{t('price', lang)}: *Rp {format_rupiah(p['price'])}*\n"
            f"{t('stock', lang)}: *{stock}* {acct_label}\n"
        )

    lines.append(t("select_product", lang))
    return "\n".join(lines)


def get_main_menu_keyboard(user_id: int = 0, lang: str = "en"):
    other_lang = "ms" if lang == "en" else "en"
    lang_label = "🌐 Bahasa Melayu" if lang == "en" else "🌐 English"

    rows = [
        [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
        [
            InlineKeyboardButton(t("btn_check_stock", lang), callback_data="menu:stok"),
            InlineKeyboardButton(t("btn_order_history", lang), callback_data="menu:orders"),
        ],
        [
            InlineKeyboardButton(lang_label, callback_data="menu:lang"),
        ],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton(t("btn_admin_panel", lang), callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def get_admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 View Products", callback_data="admin:products"),
            InlineKeyboardButton("📊 Stock Info", callback_data="admin:stockinfo"),
        ],
        [
            InlineKeyboardButton("📋 View Orders", callback_data="admin:orders"),
            InlineKeyboardButton("👥 Admin List", callback_data="admin:adminlist"),
        ],
        [
            InlineKeyboardButton("➕ Add Product", callback_data="admin:addproduct"),
            InlineKeyboardButton("📥 Add Stock", callback_data="admin:addstock"),
        ],
        [
            InlineKeyboardButton("💰 Change Price", callback_data="admin:setprice"),
            InlineKeyboardButton("📣 Broadcast", callback_data="admin:broadcast"),
        ],
        [
            InlineKeyboardButton("👤 Add Admin", callback_data="admin:addadmin"),
            InlineKeyboardButton("👤 Remove Admin", callback_data="admin:removeadmin"),
        ],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
    ])


def get_admin_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
    ])


_STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦"}


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stock", cmd_stock))
    app.add_handler(CommandHandler("produk", cmd_produk))
    app.add_handler(CallbackQueryHandler(handle_global_cancel, pattern=r"^global:cancel_payment$"))
    app.add_handler(CallbackQueryHandler(handle_lang_toggle, pattern=r"^menu:lang$"))
    app.add_handler(CallbackQueryHandler(handle_menu_button, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(handle_admin_button, pattern=r"^admin:"))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if user is None or message is None:
        return

    try:
        db.upsert_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("Failed upsert user %s: %s", user.id, exc)

    lang = get_lang(context)
    text = build_home_text(user, lang)
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(user.id, lang))


async def cmd_produk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    lang = get_lang(context)
    text = build_products_text(lang)
    products = db.get_active_products()
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(
            f"🛒 {escape_md(p['name'])} - Rp {format_rupiah(p['price'])}",
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append([btn_home(lang)])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    lang = get_lang(context)
    keyboard = InlineKeyboardMarkup([global_nav_row(lang)])

    text = (
        f"*{t('help_title', lang)}*\n\n"
        f"{t('help_how_buy', lang)}\n"
        f"{t('help_step1', lang)}\n"
        f"{t('help_step2', lang)}\n"
        f"{t('help_step3', lang)}\n"
        f"{t('help_step4', lang)}\n"
        f"{t('help_step5', lang)}\n\n"
        f"{t('help_commands', lang)}\n"
        f"{t('help_cmd_start', lang)}\n"
        f"{t('help_cmd_produk', lang)}\n"
        f"{t('help_cmd_beli', lang)}\n"
        f"{t('help_cmd_stock', lang)}\n"
        f"{t('help_cmd_myorders', lang)}\n"
        f"{t('help_cmd_cancel', lang)}\n\n"
        f"{t('help_lang_tip', lang)}"
    )

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    lang = get_lang(context)
    products = db.get_active_products()
    total_stock = db.get_stock_count()

    text = f"*{t('stock_info', lang)}*\n\n"
    if products:
        for p in products:
            stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            text += f"• *{escape_md(p['name'])}*: {stock} {t('accounts', lang)} | Rp {format_rupiah(p['price'])}/ea\n"
        text += f"\n{t('total_stock', lang)}: *{total_stock}*"
    else:
        text += t("no_products", lang)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
        [btn_home(lang)],
    ])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Language toggle handler
# ---------------------------------------------------------------------------

async def handle_lang_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    current = get_lang(context)
    new_lang = "ms" if current == "en" else "en"
    context.user_data["lang"] = new_lang

    user = update.effective_user
    text = build_home_text(user, new_lang)
    uid = (user.id or 0) if user else 0
    await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(uid, new_lang))


# ---------------------------------------------------------------------------
# Global cancel payment handler
# ---------------------------------------------------------------------------

async def handle_global_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context)
    orders = db.get_user_orders(user_id)
    pending = [o for o in orders if o.get("status") == "pending"]

    if not pending:
        await query.answer(t("cancel_no_pending", lang), show_alert=True)
        return

    await query.answer()

    order = pending[0]
    order_id = order["id"]

    db.update_order_status(order_id, "cancelled")
    db.release_stock(order_id)

    qris_msg_id = order.get("qris_message_id")
    chat_id = query.message.chat_id if query.message else user_id

    if qris_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=qris_msg_id)
        except Exception:
            pass

    try:
        await query.message.delete()
    except Exception:
        pass

    user = update.effective_user
    text = build_home_text(user, lang) if user else "Home"
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(user_id, lang),
    )


# ---------------------------------------------------------------------------
# Menu button callbacks
# ---------------------------------------------------------------------------

async def _safe_edit_or_send(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except (BadRequest, Exception):
        try:
            await query.message.delete()
        except Exception:
            pass
        chat_id = query.message.chat_id if query.message else 0
        if chat_id:
            await query.bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup,
            )


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    action = query.data.split(":")[1] if query.data else ""
    lang = get_lang(context)

    if action == "start":
        user = update.effective_user
        text = build_home_text(user, lang)
        uid = (user.id or 0) if user else 0
        await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(uid, lang))

    elif action == "produk":
        text = build_products_text(lang)
        products = db.get_active_products()
        buttons = []
        for p in products:
            buttons.append([InlineKeyboardButton(
                f"🛒 {p['name']} - Rp {format_rupiah(p['price'])}",
                callback_data=f"buy:{p['id']}",
            )])
        buttons.append([btn_home(lang)])
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "stok":
        products = db.get_active_products()
        total_stock = db.get_stock_count()

        text = f"*{t('stock_info', lang)}*\n\n"
        if products:
            for p in products:
                stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
                text += f"• *{escape_md(p['name'])}*: {stock} {t('accounts', lang)} | Rp {format_rupiah(p['price'])}/ea\n"
            text += f"\n{t('total_stock', lang)}: *{total_stock}*"
        else:
            text += t("no_products", lang)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
            [btn_home(lang)],
        ])
        await _safe_edit_or_send(query, text, reply_markup=keyboard)

    elif action == "orders":
        keyboard = InlineKeyboardMarkup([global_nav_row(lang)])
        try:
            user_id = update.effective_user.id
            orders = db.get_user_orders(user_id)

            if not orders:
                await _safe_edit_or_send(
                    query,
                    t("no_orders", lang),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
                        [btn_home(lang)],
                    ]),
                )
                return

            recent = orders[:10]
            lines = [f"{t('order_history', lang)}\n"]

            for o in recent:
                order_id = o.get("id", "")
                qty = o.get("quantity", 0)
                total = o.get("total", 0)
                status = o.get("status", "pending")
                emoji = _STATUS_EMOJI.get(status, "⏳")
                product = db.get_product(o.get("product_id", 1))
                product_name = escape_md(product["name"]) if product else "N/A"
                lines.append(f"#{order_id} | {product_name} x{qty} | Rp {format_rupiah(total)} | {emoji} {status}")

            await _safe_edit_or_send(query, "\n".join(lines), reply_markup=keyboard)

        except Exception as e:
            logger.exception("handle_menu orders error: %s", e)
            await _safe_edit_or_send(query, "Sorry, something went wrong. Please try again.", reply_markup=keyboard)

    elif action == "admin":
        if update.effective_user.id not in config.ADMIN_IDS:
            await query.answer("Access denied.", show_alert=True)
            return

        total_stock = db.get_stock_count()
        sold = db.get_total_sold()
        total_users = db.get_total_users()
        products = db.get_active_products()
        pending = len(db.get_pending_qris_orders())

        product_lines = []
        for p in products:
            p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            product_lines.append(f"  #{p['id']} {escape_md(p['name'])}: {p_stock} stock | Rp {format_rupiah(p['price'])}")

        product_stock_text = "\n".join(product_lines) if product_lines else "  No products"

        text = (
            f"*⚙️ ADMIN PANEL*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*📊 Dashboard*\n"
            f"📦 Stock Ready : *{total_stock}* accounts\n"
            f"✅ Sold : *{sold}* accounts\n"
            f"⏳ Pending Orders : *{pending}*\n"
            f"👥 Total Users : *{total_users}*\n"
            f"🛍️ Total Products : *{len(products)}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*📦 PER-PRODUCT STOCK*\n"
            f"{product_stock_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Select admin menu below 👇"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_panel_keyboard())

    elif action == "help":
        other_lang = "ms" if lang == "en" else "en"
        context.user_data["lang"] = other_lang
        new_lang = other_lang
        user = update.effective_user
        text = build_home_text(user, new_lang)
        uid = (user.id or 0) if user else 0
        await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(uid, new_lang))


# ---------------------------------------------------------------------------
# Admin panel button callbacks
# ---------------------------------------------------------------------------

async def handle_admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    if update.effective_user.id not in config.ADMIN_IDS:
        await query.answer("Access denied.", show_alert=True)
        return

    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    for key in list(context.user_data.keys()):
        if key.startswith("admin_state") or key in ("addstock_product_id", "setprice_product_id", "addadmin_id"):
            del context.user_data[key]

    if action == "products":
        products = db.get_all_products()
        if not products:
            await _safe_edit_or_send(
                query,
                "*📦 Product List*\n\nNo products yet.",
                reply_markup=get_admin_back_keyboard(),
            )
            return

        lines = ["*📦 PRODUCT LIST*\n"]
        for p in products:
            stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "Unlimited"
            status = "✅" if p["is_active"] else "❌"
            lines.append(
                f"{status} #{p['id']} | *{escape_md(p['name'])}*\n"
                f"   💰 Price: Rp {format_rupiah(p['price'])}\n"
                f"   📦 Stock: {stock}\n"
            )

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=get_admin_back_keyboard(),
        )

    elif action == "stockinfo":
        total_stock = db.get_stock_count()
        pending = len(db.get_pending_qris_orders())
        products = db.get_active_products()

        text = (
            f"*📊 STOCK INFO*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Total Ready Stock: *{total_stock}* accounts\n"
            f"⏳ Pending Orders: *{pending}*\n"
        )
        for p in products:
            p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            text += f"\n#{p['id']} {escape_md(p['name'])}: *{p_stock}* | Rp {format_rupiah(p['price'])}"

        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard())

    elif action == "orders":
        try:
            orders = db.get_all_orders(limit=20)
        except Exception as exc:
            logger.exception("Failed get_all_orders: %s", exc)
            await _safe_edit_or_send(query, "Sorry, something went wrong.", reply_markup=get_admin_back_keyboard())
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                "*📋 RECENT ORDERS*\n\nNo orders yet.",
                reply_markup=get_admin_back_keyboard(),
            )
            return

        lines = [f"*📋 RECENT ORDERS* ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            status = o.get("status", "pending")
            emoji = _STATUS_EMOJI.get(status, "⏳")
            order_id = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"

            lines.append(
                f"#{order_id} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
                f"Status: {emoji} {status}\n"
            )

        filter_buttons = [
            InlineKeyboardButton("📋 All", callback_data="admin:orders"),
            InlineKeyboardButton("⏳ Pending", callback_data="admin:orders_pending"),
            InlineKeyboardButton("✅ Paid", callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_pending":
        try:
            orders = db.get_all_orders(limit=20, status="pending")
        except Exception:
            await _safe_edit_or_send(query, "Sorry, something went wrong.", reply_markup=get_admin_back_keyboard())
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                "*⏳ PENDING ORDERS*\n\nNo pending orders.",
                reply_markup=get_admin_back_keyboard(),
            )
            return

        lines = [f"*⏳ PENDING ORDERS* ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            order_id = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"
            lines.append(
                f"#{order_id} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
            )

        filter_buttons = [
            InlineKeyboardButton("📋 All", callback_data="admin:orders"),
            InlineKeyboardButton("⏳ Pending", callback_data="admin:orders_pending"),
            InlineKeyboardButton("✅ Paid", callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_paid":
        try:
            orders = db.get_all_orders(limit=20, status="paid")
        except Exception:
            await _safe_edit_or_send(query, "Sorry, something went wrong.", reply_markup=get_admin_back_keyboard())
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                "*✅ PAID ORDERS*\n\nNo paid orders.",
                reply_markup=get_admin_back_keyboard(),
            )
            return

        lines = [f"*✅ PAID ORDERS* ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            order_id = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"
            lines.append(
                f"#{order_id} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
            )

        filter_buttons = [
            InlineKeyboardButton("📋 All", callback_data="admin:orders"),
            InlineKeyboardButton("⏳ Pending", callback_data="admin:orders_pending"),
            InlineKeyboardButton("✅ Paid", callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "adminlist":
        lines = ["*👥 ADMIN LIST*\n"]
        for i, admin_id in enumerate(sorted(config.ADMIN_IDS), 1):
            is_main = " ⭐" if admin_id == config.ADMIN_USER_ID else ""
            lines.append(f"{i}. `{admin_id}`{is_main}")

        lines.append(f"\n📊 Total: *{len(config.ADMIN_IDS)}* admins")

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=get_admin_back_keyboard(),
        )

    elif action == "addproduct":
        context.user_data["admin_state"] = "addproduct_name"
        text = (
            "*➕ ADD PRODUCT*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 Send the *product name* now.\n\n"
            "Example: `Leonardo AI Account`"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard())

    elif action == "setprice":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(
                query,
                "*💰 CHANGE PRICE*\n\nNo products yet.",
                reply_markup=get_admin_back_keyboard(),
            )
            return

        buttons = []
        for p in products:
            buttons.append([InlineKeyboardButton(
                f"💰 {p['name']} — Rp {format_rupiah(p['price'])}",
                callback_data=f"admin:spick:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "*💰 CHANGE PRICE*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nSelect product to change price:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "spick":
        if len(parts) < 3:
            return
        try:
            product_id = int(parts[2])
        except ValueError:
            return
        product = db.get_product(product_id)
        if not product:
            await _safe_edit_or_send(query, "Product not found.", reply_markup=get_admin_back_keyboard())
            return

        context.user_data["admin_state"] = "setprice_value"
        context.user_data["setprice_product_id"] = product_id

        text = (
            f"*💰 CHANGE PRICE — {escape_md(product['name'])}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Current price: *Rp {format_rupiah(product['price'])}*\n\n"
            "📝 Send the *new price* now.\n\n"
            "Example: `15000`"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard())

    elif action == "broadcast":
        context.user_data["admin_state"] = "broadcast_msg"
        text = (
            "*📣 BROADCAST*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 Send the *message* to broadcast now.\n\n"
            "Example: `Weekend promo 20% off!`"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard())

    elif action == "addadmin":
        context.user_data["admin_state"] = "addadmin_id"
        text = (
            "*👤 ADD ADMIN*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 Send the *Telegram User ID* now.\n\n"
            "💡 To find ID: Forward a message to @userinfobot\n\n"
            "Example: `123456789`"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard())

    elif action == "removeadmin":
        others = sorted(config.ADMIN_IDS - {config.ADMIN_USER_ID})
        if not others:
            await _safe_edit_or_send(
                query,
                "*👤 REMOVE ADMIN*\n\nNo additional admins to remove.",
                reply_markup=get_admin_back_keyboard(),
            )
            return

        buttons = []
        for aid in others:
            buttons.append([InlineKeyboardButton(
                f"❌ Remove {aid}",
                callback_data=f"admin:rmadmin:{aid}",
            )])
        buttons.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "*👤 REMOVE ADMIN*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nSelect admin to remove:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "rmadmin":
        if len(parts) < 3:
            return
        try:
            remove_id = int(parts[2])
        except ValueError:
            return
        if remove_id == config.ADMIN_USER_ID:
            await _safe_edit_or_send(query, "Cannot remove the main admin.", reply_markup=get_admin_back_keyboard())
            return
        config.ADMIN_IDS.discard(remove_id)
        await _safe_edit_or_send(
            query,
            f"*✅ Admin removed!*\n\n🆔 ID: `{remove_id}`\n👥 Total admins: *{len(config.ADMIN_IDS)}*",
            reply_markup=get_admin_back_keyboard(),
        )

    elif action == "addstock":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(
                query,
                "*📥 ADD STOCK*\n\nNo active products yet. Add a product first.",
                reply_markup=get_admin_back_keyboard(),
            )
            return

        buttons = []
        for p in products:
            stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            buttons.append([InlineKeyboardButton(
                f"📦 {p['name']} (Stock: {stock})",
                callback_data=f"admin:astk:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "*📥 ADD STOCK*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nSelect product to add stock to:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "astk":
        if len(parts) < 3:
            return
        try:
            product_id = int(parts[2])
        except ValueError:
            return

        product = db.get_product(product_id)
        if not product:
            await _safe_edit_or_send(query, "Product not found.", reply_markup=get_admin_back_keyboard())
            return

        context.user_data["addstock_product_id"] = product_id
        context.user_data["state"] = "addstock"

        text = (
            f"*📥 ADD STOCK — {escape_md(product['name'])}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Current stock: *{db.get_stock_count(product_id)}* accounts\n\n"
            "*Method 1:* Send a .txt file\n"
            "Format per line: `email:password`\n\n"
            "*Method 2:* Paste directly in chat\n"
            "`email1:password1`\n"
            "`email2:password2`\n\n"
            "Send now! 📤"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard())
