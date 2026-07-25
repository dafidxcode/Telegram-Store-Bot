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


def get_lang(context: ContextTypes.DEFAULT_TYPE, user_id: int = 0) -> str:
    cached = context.user_data.get("lang")
    if cached:
        return cached
    if user_id:
        db_lang = db.get_user_lang(user_id)
        context.user_data["lang"] = db_lang
        return db_lang
    return DEFAULT_LANG


def save_lang(context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str) -> None:
    context.user_data["lang"] = lang
    db.save_lang(user_id, lang)


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
    for i, p in enumerate(active_products, 1):
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        product_lines.append(f"  #{i} {escape_md(p['name'])}: {stock} stock | Rp {format_rupiah(p['price'])}")

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


def get_main_menu_keyboard(user_id: int = 0, lang: str = "id"):
    lang_label = "🌐 Bahasa Indonesia" if lang == "en" else "🌐 English"

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


def get_admin_panel_keyboard(lang="id"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_view_products", lang), callback_data="admin:products"),
            InlineKeyboardButton(t("btn_stock_info", lang), callback_data="admin:stockinfo"),
        ],
        [
            InlineKeyboardButton(t("btn_view_orders", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_financial_report", lang), callback_data="admin:report"),
        ],
        [
            InlineKeyboardButton(t("btn_add_product", lang), callback_data="admin:addproduct"),
            InlineKeyboardButton(t("btn_edit_product", lang), callback_data="admin:eprod"),
        ],
        [
            InlineKeyboardButton(t("btn_add_stock", lang), callback_data="admin:addstock"),
            InlineKeyboardButton(t("btn_change_price", lang), callback_data="admin:setprice"),
        ],
        [
            InlineKeyboardButton(t("btn_export_stock", lang), callback_data="admin:exstock"),
            InlineKeyboardButton(t("btn_search_order", lang), callback_data="admin:search"),
        ],
        [
            InlineKeyboardButton(t("btn_broadcast", lang), callback_data="admin:broadcast"),
            InlineKeyboardButton(t("btn_bot_settings", lang), callback_data="admin:settings"),
        ],
        [
            InlineKeyboardButton(t("btn_admin_list", lang), callback_data="admin:adminlist"),
            InlineKeyboardButton(t("btn_add_admin", lang), callback_data="admin:addadmin"),
            InlineKeyboardButton(t("btn_remove_admin", lang), callback_data="admin:removeadmin"),
        ],
        [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
    ])


def get_admin_back_keyboard(lang="id", back_data="menu:admin"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_back", lang), callback_data=back_data)],
        [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
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

    lang = get_lang(context, user.id)
    text = build_home_text(user, lang)
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(user.id, lang))


async def cmd_produk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    text = build_products_text(lang)
    products = db.get_active_products()
    buttons = []
    for p in products:
        p_name = escape_md(p['name'])
        btn_title = p_name if p_name.startswith(("🛒", "🛍️", "📦")) else f"🛒 {p_name}"
        buttons.append([InlineKeyboardButton(
            f"{btn_title} - Rp {format_rupiah(p['price'])}",
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append([btn_home(lang)])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    keyboard = InlineKeyboardMarkup([global_nav_row(lang)])

    text = (
        f"{t('help_title', lang)}\n\n"
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

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    products = db.get_active_products()
    total_stock = db.get_stock_count()

    text = f"{t('stock_info', lang)}\n\n"
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
# Language toggle handler — saves to DB
# ---------------------------------------------------------------------------

async def handle_lang_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    user = update.effective_user
    if user is None:
        return

    current = get_lang(context, user.id)
    new_lang = "id" if current == "en" else "en"
    save_lang(context, user.id, new_lang)

    text = build_home_text(user, new_lang)
    await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(user.id, new_lang))


# ---------------------------------------------------------------------------
# Global cancel payment handler
# ---------------------------------------------------------------------------

async def handle_global_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
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
    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    if action == "start":
        user = update.effective_user
        text = build_home_text(user, lang)
        await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(user_id, lang))

    elif action == "produk":
        text = build_products_text(lang)
        products = db.get_active_products()
        buttons = []
        for p in products:
            p_name = escape_md(p['name'])
            btn_title = p_name if p_name.startswith(("🛒", "🛍️", "📦")) else f"🛒 {p_name}"
            buttons.append([InlineKeyboardButton(
                f"{btn_title} - Rp {format_rupiah(p['price'])}",
                callback_data=f"buy:{p['id']}",
            )])
        buttons.append([btn_home(lang)])
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "stok":
        products = db.get_active_products()
        total_stock = db.get_stock_count()

        text = f"{t('stock_info', lang)}\n\n"
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
                oid = o.get("id", "")
                qty = o.get("quantity", 0)
                total = o.get("total", 0)
                status = o.get("status", "pending")
                emoji = _STATUS_EMOJI.get(status, "⏳")
                product = db.get_product(o.get("product_id", 1))
                product_name = escape_md(product["name"]) if product else "N/A"
                lines.append(f"#{oid} | {product_name} x{qty} | Rp {format_rupiah(total)} | {emoji} {status}")

            await _safe_edit_or_send(query, "\n".join(lines), reply_markup=keyboard)

        except Exception as e:
            logger.exception("handle_menu orders error: %s", e)
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=keyboard)

    elif action == "admin":
        if user_id not in config.ADMIN_IDS:
            await query.answer(t("admin_access_denied", lang), show_alert=True)
            return

        total_stock = db.get_stock_count()
        sold = db.get_total_sold()
        total_users = db.get_total_users()
        products = db.get_active_products()
        pending = len(db.get_pending_qris_orders())

        product_lines = []
        for i, p in enumerate(products, 1):
            p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            product_lines.append(f"  #{i} {escape_md(p['name'])}: {p_stock} stock | Rp {format_rupiah(p['price'])}")

        product_stock_text = "\n".join(product_lines) if product_lines else f"  {t('no_products_admin', lang)}"

        text = (
            f"{t('admin_panel', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('dashboard', lang)}\n"
            f"{t('stock_ready', lang)} : *{total_stock}* {t('accounts', lang)}\n"
            f"{t('sold', lang)} : *{sold}* {t('accounts', lang)}\n"
            f"{t('pending_orders', lang)} : *{pending}*\n"
            f"{t('total_users', lang, n=total_users)}\n"
            f"{t('total_products', lang)} : *{len(products)}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('per_product_stock', lang)}\n"
            f"{product_stock_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('select_admin_menu', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_panel_keyboard(lang))


# ---------------------------------------------------------------------------
# Admin panel button callbacks
# ---------------------------------------------------------------------------

async def handle_admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    if user_id not in config.ADMIN_IDS:
        await query.answer(t("admin_access_denied", lang), show_alert=True)
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
                t("admin_no_products", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"{t('admin_product_list', lang)}\n"]
        for i, p in enumerate(products, 1):
            stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else t("unlimited", lang)
            status = "✅" if p["is_active"] else "❌"
            lines.append(
                f"{status} #{i} | *{escape_md(p['name'])}*\n"
                f"   💰 {t('admin_price', lang)}: Rp {format_rupiah(p['price'])}\n"
                f"   📦 {t('admin_stock', lang)}: {stock}\n"
            )

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "stockinfo":
        total_stock = db.get_stock_count()
        pending = len(db.get_pending_qris_orders())
        products = db.get_active_products()

        text = (
            f"{t('admin_stock_info', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 {t('admin_total_ready', lang)}: *{total_stock}* {t('accounts', lang)}\n"
            f"⏳ {t('admin_pending_orders', lang)}: *{pending}*\n"
        )
        for i, p in enumerate(products, 1):
            p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            text += f"\n#{i} {escape_md(p['name'])}: *{p_stock}* | Rp {format_rupiah(p['price'])}"

        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "orders":
        try:
            orders = db.get_all_orders(limit=20)
        except Exception as exc:
            logger.exception("Failed get_all_orders: %s", exc)
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=get_admin_back_keyboard(lang))
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                t("admin_no_orders", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"{t('admin_recent_orders', lang)} ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            status = o.get("status", "pending")
            emoji = _STATUS_EMOJI.get(status, "⏳")
            oid = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"

            lines.append(
                f"#{oid} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
                f"Status: {emoji} {status}\n"
            )

        filter_buttons = [
            InlineKeyboardButton(t("btn_all", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_pending", lang), callback_data="admin:orders_pending"),
            InlineKeyboardButton(t("btn_paid", lang), callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_pending":
        try:
            orders = db.get_all_orders(limit=20, status="pending")
        except Exception:
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=get_admin_back_keyboard(lang))
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                t("admin_no_pending", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"{t('admin_pending_orders_title', lang)} ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            oid = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"
            lines.append(
                f"#{oid} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
            )

        filter_buttons = [
            InlineKeyboardButton(t("btn_all", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_pending", lang), callback_data="admin:orders_pending"),
            InlineKeyboardButton(t("btn_paid", lang), callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_paid":
        try:
            orders = db.get_all_orders(limit=20, status="paid")
        except Exception:
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=get_admin_back_keyboard(lang))
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                t("admin_no_paid", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"{t('admin_paid_orders', lang)} ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            oid = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"
            lines.append(
                f"#{oid} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
            )

        filter_buttons = [
            InlineKeyboardButton(t("btn_all", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_pending", lang), callback_data="admin:orders_pending"),
            InlineKeyboardButton(t("btn_paid", lang), callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "adminlist":
        lines = [f"{t('admin_list_title', lang)}\n"]
        for i, aid in enumerate(sorted(config.ADMIN_IDS), 1):
            is_main = " ⭐" if aid == config.ADMIN_USER_ID else ""
            lines.append(f"{i}. `{aid}`{is_main}")

        lines.append(f"\n📊 {t('admin_total', lang)}: *{len(config.ADMIN_IDS)}* {t('admins', lang)}")

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "addproduct":
        context.user_data["admin_state"] = "addproduct_name"
        text = (
            f"{t('admin_add_product', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_send_name', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "setprice":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(
                query,
                f"{t('admin_change_price', lang)}\n\n{t('no_products', lang)}",
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        buttons = []
        for p in products:
            buttons.append([InlineKeyboardButton(
                f"💰 {p['name']} — Rp {format_rupiah(p['price'])}",
                callback_data=f"admin:spick:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            f"{t('admin_change_price', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_product', lang)}",
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
            await _safe_edit_or_send(query, t("admin_not_found", lang, id=product_id), reply_markup=get_admin_back_keyboard(lang))
            return

        context.user_data["admin_state"] = "setprice_value"
        context.user_data["setprice_product_id"] = product_id

        text = (
            f"{t('admin_change_price', lang)} — *{escape_md(product['name'])}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_current_price', lang)}: *Rp {format_rupiah(product['price'])}*\n\n"
            f"{t('admin_send_new_price', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "broadcast":
        context.user_data["admin_state"] = "broadcast_msg"
        text = (
            f"{t('admin_broadcast', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_send_message', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "addadmin":
        context.user_data["admin_state"] = "addadmin_id"
        text = (
            f"{t('admin_add_admin', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_send_user_id', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "removeadmin":
        others = sorted(config.ADMIN_IDS - {config.ADMIN_USER_ID})
        if not others:
            await _safe_edit_or_send(
                query,
                t("admin_no_remove", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        buttons = []
        for aid in others:
            buttons.append([InlineKeyboardButton(
                f"❌ Remove {aid}",
                callback_data=f"admin:rmadmin:{aid}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            f"{t('admin_remove_admin', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_admin', lang)}",
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
            await _safe_edit_or_send(query, t("admin_cannot_remove", lang), reply_markup=get_admin_back_keyboard(lang))
            return
        config.ADMIN_IDS.discard(remove_id)
        await _safe_edit_or_send(
            query,
            f"{t('admin_removed', lang)}\n\n{t('admin_id', lang)}: `{remove_id}`\n{t('admin_total_admins', lang)}: *{len(config.ADMIN_IDS)}*",
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "addstock":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(
                query,
                t("admin_no_active_products", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        buttons = []
        for p in products:
            stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            buttons.append([InlineKeyboardButton(
                f"📦 {p['name']} ({t('admin_stock', lang).lstrip('📦 ')}: {stock})",
                callback_data=f"admin:astk:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            f"{t('admin_add_stock', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_stock_product', lang)}",
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
            await _safe_edit_or_send(query, t("admin_not_found", lang, id=product_id), reply_markup=get_admin_back_keyboard(lang))
            return

        context.user_data["addstock_product_id"] = product_id
        context.user_data["state"] = "addstock"

        text = (
            f"{t('admin_add_stock', lang)} — *{escape_md(product['name'])}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_current_stock', lang)}: *{db.get_stock_count(product_id)}* {t('accounts', lang)}\n\n"
            f"{t('admin_method1', lang)}\n\n"
            f"{t('admin_method2', lang)}\n\n"
            f"{t('admin_send_now', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "delproduct":
        products = db.get_all_products()
        if not products:
            await _safe_edit_or_send(
                query,
                t("admin_no_products", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        buttons = []
        for p in products:
            buttons.append([InlineKeyboardButton(
                f"🗑️ #{p['id']} {p['name']} (Rp {format_rupiah(p['price'])})",
                callback_data=f"admin:dprod:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            f"*{t('btn_delete_product', lang)}*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_delete_product', lang)}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "dprod":
        if len(parts) < 3:
            return
        try:
            product_id = int(parts[2])
        except ValueError:
            return
        product = db.get_product(product_id)
        if not product:
            await _safe_edit_or_send(query, t("admin_not_found", lang, id=product_id), reply_markup=get_admin_back_keyboard(lang))
            return

        db.delete_product(product_id)
        await _safe_edit_or_send(
            query,
            t("admin_product_deleted_success", lang, id=product_id, name=escape_md(product["name"])),
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "report":
        rep = db.get_financial_report()
        best_p = rep["best_product"]
        best_str = f"{escape_md(best_p['name'])} ({best_p['total_qty']} {t('accounts', lang)})" if best_p else "-"
        text = (
            f"{t('admin_financial_report_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 *Hari Ini*: Rp {format_rupiah(rep['today_revenue'])} ({rep['today_orders']} transaksi)\n"
            f"📆 *7 Hari Terakhir*: Rp {format_rupiah(rep['week_revenue'])} ({rep['week_orders']} transaksi)\n"
            f"🗓️ *30 Hari Terakhir*: Rp {format_rupiah(rep['month_revenue'])} ({rep['month_orders']} transaksi)\n"
            f"💰 *Total Keseluruhan*: Rp {format_rupiah(rep['total_revenue'])} ({rep['total_orders']} transaksi)\n"
            f"🏆 *Produk Terlaris*: {best_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "eprod":
        products = db.get_all_products()
        if not products:
            await _safe_edit_or_send(query, t("no_products", lang), reply_markup=get_admin_back_keyboard(lang))
            return
        buttons = []
        for i, p in enumerate(products, 1):
            status_icon = "🟢" if p["is_active"] else "🔴"
            buttons.append([InlineKeyboardButton(
                f"{status_icon} #{i} {p['name']} (Rp {format_rupiah(p['price'])})",
                callback_data=f"admin:etog:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(
            query,
            f"{t('btn_edit_product', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nKlik produk untuk *Mengubah Status Aktif/Nonaktif*:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "etog":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if product:
            new_status = 0 if product["is_active"] else 1
            db.update_product(pid, is_active=new_status)
            status_text = "🟢 Aktif" if new_status else "🔴 Nonaktif"
            await query.answer(f"Status {product['name']} diubah -> {status_text}", show_alert=True)
            products = db.get_all_products()
            buttons = []
            for i, p in enumerate(products, 1):
                status_icon = "🟢" if p["is_active"] else "🔴"
                buttons.append([InlineKeyboardButton(
                    f"{status_icon} #{i} {p['name']} (Rp {format_rupiah(p['price'])})",
                    callback_data=f"admin:etog:{p['id']}",
                )])
            buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
            await _safe_edit_or_send(
                query,
                f"{t('btn_edit_product', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nKlik produk untuk *Mengubah Status Aktif/Nonaktif*:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

    elif action == "exstock":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(query, t("no_products", lang), reply_markup=get_admin_back_keyboard(lang))
            return
        buttons = []
        for i, p in enumerate(products, 1):
            cnt = db.get_stock_count(p["id"])
            buttons.append([InlineKeyboardButton(
                f"📤 #{i} {p['name']} ({cnt} ready)",
                callback_data=f"admin:dlex:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(
            query,
            f"{t('admin_export_stock_title', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nPilih produk yang ingin di-export file stoknya:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "dlex":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if not product:
            return
        content = db.get_stock_file_content(pid)
        if not content:
            await query.answer("Stok produk ini kosong!", show_alert=True)
            return
        import io
        bio = io.BytesIO(content.encode("utf-8"))
        bio.name = f"stok_{product['name'].replace(' ', '_')}.txt"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=bio,
            caption=f"📦 Export stok ready for *{escape_md(product['name'])}*",
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.answer("File stok berhasil dikirim!")

    elif action == "search":
        context.user_data["admin_state"] = "search_order"
        await _safe_edit_or_send(
            query,
            f"{t('admin_search_order_title', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_search_order_prompt', lang)}",
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "settings":
        status = "🟢 AKTIF (Normal)" if not config.MAINTENANCE_MODE else "🔴 NONAKTIF (Maintenance ON)"
        btn_maint = "🔴 Aktifkan Maintenance" if not config.MAINTENANCE_MODE else "🟢 Matikan Maintenance Mode"
        text = (
            f"{t('admin_bot_settings_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status Bot: *{status}*\n\n"
            f"Ketika Maintenance Mode *ON*, pembeli tidak dapat membuat pesanan baru."
        )
        buttons = [
            [InlineKeyboardButton(btn_maint, callback_data="admin:toggle_maint")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "toggle_maint":
        config.MAINTENANCE_MODE = not config.MAINTENANCE_MODE
        status_txt = "Maintenance Mode ON" if config.MAINTENANCE_MODE else "Maintenance Mode OFF"
        await query.answer(f"Status Bot: {status_txt}", show_alert=True)
        status = "🟢 AKTIF (Normal)" if not config.MAINTENANCE_MODE else "🔴 NONAKTIF (Maintenance ON)"
        btn_maint = "🔴 Aktifkan Maintenance" if not config.MAINTENANCE_MODE else "🟢 Matikan Maintenance Mode"
        text = (
            f"{t('admin_bot_settings_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status Bot: *{status}*\n\n"
            f"Ketika Maintenance Mode *ON*, pembeli tidak dapat membuat pesanan baru."
        )
        buttons = [
            [InlineKeyboardButton(btn_maint, callback_data="admin:toggle_maint")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "apv":
        if len(parts) < 3:
            return
        order_id = parts[2]
        order = db.get_order(order_id)
        if not order:
            await query.answer("Pesanan tidak ditemukan!", show_alert=True)
            return
        if order["status"] == "paid":
            await query.answer("Pesanan ini sudah dibayar!", show_alert=True)
            return

        product_id = order.get("product_id", 1)
        items = db.take_stock(order_id, order["quantity"], product_id)
        if not items:
            await query.answer("⚠️ Stok produk tidak cukup!", show_alert=True)
            return

        db.update_order_status(order_id, "paid")
        product = db.get_product(product_id)
        product_name = product["name"] if product else "Produk"
        buyer_lang = db.get_user_lang(order["user_id"])

        lines = [f"{item['email']}:{item['password']}:{item['balance']}".rstrip(":") for item in items]
        doc_content = "\n".join(lines)

        import io
        file_bytes = io.BytesIO(doc_content.encode("utf-8"))
        file_bytes.name = f"akun_{order_id}.txt"

        caption = (
            f"{t('payment_success', buyer_lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('order_label', buyer_lang)}: #{order_id}\n"
            f"{t('product_label', buyer_lang)}: {escape_md(product_name)}\n"
            f"{t('quantity_label_short', buyer_lang)}: {order['quantity']} {t('accounts', buyer_lang)}\n"
            f"{t('total_label', buyer_lang)}: Rp {format_rupiah(order['total'])}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('file_attached', buyer_lang)}"
        )

        try:
            await context.bot.send_document(
                chat_id=order["user_id"],
                document=file_bytes,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as err:
            logger.exception("Failed to send document to buyer %s: %s", order["user_id"], err)

        await query.answer(f"✅ Order #{order_id} berhasil di-approve!", show_alert=True)
        await _safe_edit_or_send(query, f"✅ *Pesanan #{order_id} BERHASIL DI-APPROVE!*\n\nProduk telah dikirimkan ke pembeli.", reply_markup=get_admin_back_keyboard(lang))



