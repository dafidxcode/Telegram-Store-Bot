"""Start, help, and menu command handlers with inline keyboard buttons."""

import logging
from datetime import datetime, timezone, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
import db

logger = logging.getLogger(__name__)


def escape_md(text: str) -> str:
    """Escape characters that have special meaning in Telegram MarkdownV1."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def get_now_wib() -> str:
    wib = datetime.now(tz=timezone(timedelta(hours=7)))
    return wib.strftime(f"%-d %B %Y at %-H:%M WIB")


def get_greeting() -> str:
    hour = datetime.now(tz=timezone(timedelta(hours=7))).hour
    if 4 <= hour < 11:
        return "Good Morning"
    elif 11 <= hour < 15:
        return "Good Afternoon"
    elif 15 <= hour < 18:
        return "Good Evening"
    else:
        return "Good Night"


# ---------------------------------------------------------------------------
# Global navigation buttons — used across ALL chatbox screens
# ---------------------------------------------------------------------------

def btn_home():
    return InlineKeyboardButton("🏠 Home", callback_data="menu:start")


def btn_back(text="⬅️ Back", data="menu:start"):
    return InlineKeyboardButton(text, callback_data=data)


def btn_cancel_payment():
    return InlineKeyboardButton("❌ Cancel Payment", callback_data="global:cancel_payment")


def global_nav_row():
    return [btn_home()]


def global_nav_keyboard(user_id: int = 0):
    """Three-button row: Back | Cancel | Home — for payment screens."""
    return InlineKeyboardMarkup([
        [btn_back(), btn_cancel_payment(), btn_home()],
    ])


def global_nav_keyboard_simple(user_id: int = 0):
    """Single Home button — for general screens."""
    return InlineKeyboardMarkup([global_nav_row()])


# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

def build_home_text(user) -> str:
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

    product_stock_text = "\n".join(product_lines) if product_lines else "  No products yet"

    return (
        f"{get_greeting()}, {first_name}!\n"
        f"📅 {get_now_wib()}\n"
        f"\n"
        f"Welcome to *{escape_md(config.SHOP_NAME)}*.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*👤 ACCOUNT STATS*\n"
        f"Username : {username}\n"
        f"ID : {user.id}\n"
        f"📦 Total Orders : {user_orders} transactions\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*📊 BOT STATS*\n"
        f"📨 Accounts Sold : {sold}\n"
        f"🛍 Active Products : {product_count}\n"
        f"👥 Total Users : {total_users}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*📦 STOCK PER PRODUCT*\n"
        f"{product_stock_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"💡 Where to start?\n"
        f"• Buy account → Product List\n"
        f"• Check transactions → Order History\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def build_products_text() -> str:
    products = db.get_active_products()
    if not products:
        return "*🛍️ PRODUCT LIST*\n\nNo products available yet."

    lines = ["*🛍️ PRODUCT LIST*\n"]
    for i, p in enumerate(products, 1):
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "Unlimited"
        duration = f"\n⏰ Duration: {escape_md(p['duration'])}" if p.get("duration") else ""
        desc = f"\n{escape_md(p['description'])}" if p.get("description") else ""

        lines.append(
            f"*{i}. {escape_md(p['name'])}*\n"
            f"{desc}{duration}\n"
            f"💰 Price: *Rp {format_rupiah(p['price'])}*\n"
            f"📦 Stock: *{stock}* {'accounts' if p['stock_type'] == 'limited' else ''}\n"
        )

    lines.append("Select a product to order:")
    return "\n".join(lines)


def get_main_menu_keyboard(user_id: int = 0):
    rows = [
        [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
        [
            InlineKeyboardButton("📦 Check Stock", callback_data="menu:stok"),
            InlineKeyboardButton("📋 Order History", callback_data="menu:orders"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu:help"),
        ],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu:admin")])
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

    text = build_home_text(user)
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(user.id))


async def cmd_produk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    text = build_products_text()
    products = db.get_active_products()
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(
            f"🛒 {escape_md(p['name'])} - Rp {format_rupiah(p['price'])}",
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append([btn_home()])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    keyboard = InlineKeyboardMarkup([global_nav_row()])

    text = (
        "*❓ Help*\n\n"
        "*How to Buy:*\n"
        "1. Click *🛍️ Product List*\n"
        "2. Select a product\n"
        "3. Choose quantity\n"
        "4. Confirm & pay via QRIS\n"
        "5. Account is delivered automatically\n\n"
        "*Commands:*\n"
        "/start - 🏠 Main menu\n"
        "/produk - 🛍️ View products\n"
        "/beli - 🛒 Buy account\n"
        "/stock - 📦 Check stock\n"
        "/myorders - 📋 Order history\n"
        "/cancel - ❌ Cancel process"
    )

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    products = db.get_active_products()
    total_stock = db.get_stock_count()

    text = f"*📦 Stock Info*\n\n"
    if products:
        for p in products:
            stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            text += f"• *{escape_md(p['name'])}*: {stock} accounts | Rp {format_rupiah(p['price'])}/ea\n"
        text += f"\n📦 Total: *{total_stock}* accounts"
    else:
        text += "No products available yet."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
        [btn_home()],
    ])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Global cancel payment handler
# ---------------------------------------------------------------------------

async def handle_global_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Cancel Payment button — cancel the most recent pending order."""
    query = update.callback_query
    if query is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    orders = db.get_user_orders(user_id)
    pending = [o for o in orders if o.get("status") == "pending"]

    if not pending:
        await query.answer("No pending payment to cancel.", show_alert=True)
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
    text = build_home_text(user) if user else "Home"
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(user_id),
    )


# ---------------------------------------------------------------------------
# Menu button callbacks
# ---------------------------------------------------------------------------

async def _safe_edit_or_send(query, text: str, reply_markup=None) -> None:
    """Try edit_message_text; if it fails (photo/deleted message), send new message instead."""
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

    if action == "start":
        user = update.effective_user
        text = build_home_text(user)
        uid = (user.id or 0) if user else 0
        await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(uid))

    elif action == "produk":
        text = build_products_text()
        products = db.get_active_products()
        buttons = []
        for p in products:
            buttons.append([InlineKeyboardButton(
                f"🛒 {p['name']} - Rp {format_rupiah(p['price'])}",
                callback_data=f"buy:{p['id']}",
            )])
        buttons.append([btn_home()])
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "stok":
        products = db.get_active_products()
        total_stock = db.get_stock_count()

        text = f"*📦 Stock Info*\n\n"
        if products:
            for p in products:
                stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
                text += f"• *{escape_md(p['name'])}*: {stock} accounts | Rp {format_rupiah(p['price'])}/ea\n"
            text += f"\n📦 Total: *{total_stock}* accounts"
        else:
            text += "No products available yet."

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
            [btn_home()],
        ])
        await _safe_edit_or_send(query, text, reply_markup=keyboard)

    elif action == "orders":
        keyboard = InlineKeyboardMarkup([global_nav_row()])
        try:
            user_id = update.effective_user.id
            orders = db.get_user_orders(user_id)

            if not orders:
                await _safe_edit_or_send(
                    query,
                    "No orders yet. Buy now! 🛒",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
                        [btn_home()],
                    ]),
                )
                return

            recent = orders[:10]
            lines = ["*📋 Order History*\n"]

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
        keyboard = InlineKeyboardMarkup([global_nav_row()])
        text = (
            "*❓ Help*\n\n"
            "*How to Buy:*\n"
            "1. Click *🛍️ Product List*\n"
            "2. Select a product\n"
            "3. Choose quantity\n"
            "4. Confirm & pay via QRIS\n"
            "5. Account is delivered automatically\n\n"
            "*Commands:*\n"
            "/start - 🏠 Main menu\n"
            "/produk - 🛍️ View products\n"
            "/beli - 🛒 Buy account\n"
            "/stock - 📦 Check stock\n"
            "/myorders - 📋 Order history\n"
            "/cancel - ❌ Cancel process"
        )
        await _safe_edit_or_send(query, text, reply_markup=keyboard)


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

    # Clear any pending admin state when navigating
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
