"""Start, help, and menu command handlers with inline keyboard buttons."""

import logging
from datetime import datetime, timezone, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
import db

logger = logging.getLogger(__name__)


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


def build_home_text(user) -> str:
    stock = db.get_stock_count()
    sold = db.get_total_sold()
    total_users = db.get_total_users()
    user_orders = db.get_user_order_count(user.id)
    username = f"@{user.username}" if user.username else "N/A"
    first_name = user.first_name or "friend"

    return (
        f"{get_greeting()}, {first_name}! 🌟\n"
        f"📅 {get_now_wib()}\n"
        f"\n"
        f"Welcome to *{config.SHOP_NAME}*.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📊 ACCOUNT STATS\n"
        f"👤 Username : {username}\n"
        f"🆔 ID : {user.id}\n"
        f"🛒 Total Orders : {user_orders} transactions\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📊 BOT STATS\n"
        f"✅ Accounts Sold : {sold}\n"
        f"💰 Price : Rp {format_rupiah(config.HARGA_PER_AKUN)}/account\n"
        f"📦 Stock : {stock}\n"
        f"👥 Total Users : {total_users}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"Where to start?\n"
        f"🛒 Buy account → Product List\n"
        f"📋 Check transactions → Order History"
    )


def build_products_text() -> str:
    products = db.get_active_products()
    if not products:
        return "*🛍️ PRODUCT LIST*\n\nNo products available yet."

    lines = ["*🛍️ PRODUCT LIST*\n"]
    for i, p in enumerate(products, 1):
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "Unlimited"
        duration = f"\n⏰ Duration: {p['duration']}" if p.get("duration") else ""
        desc = f"\n{p['description']}" if p.get("description") else ""

        lines.append(
            f"*{i}. {p['name']}* {'🔥' if i == 1 else ''}\n"
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
    user = update.effective_user
    message = update.message
    if message is None:
        return

    text = build_products_text()
    products = db.get_active_products()
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(
            f"🛒 {p['name']} - Rp {format_rupiah(p['price'])}",
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
    ])

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

    stock = db.get_stock_count()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
    ])

    await message.reply_text(
        f"*📦 Stock Info*\n\n"
        f"📦 Available stock: *{stock}* accounts\n"
        f"💰 Price: *Rp {config.HARGA_PER_AKUN:,}/account*\n"
        f"💵 Total value: *Rp {format_rupiah(config.HARGA_PER_AKUN * stock)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# Menu button callbacks
# ---------------------------------------------------------------------------

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
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(uid))

    elif action == "produk":
        text = build_products_text()
        products = db.get_active_products()
        buttons = []
        for p in products:
            buttons.append([InlineKeyboardButton(
                f"🛒 {p['name']} - Rp {format_rupiah(p['price'])}",
                callback_data=f"buy:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "stok":
        stock = db.get_stock_count()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
        ])
        text = (
            f"*📦 Stock Info*\n\n"
            f"📦 Available stock: *{stock}* accounts\n"
            f"💰 Price: *Rp {config.HARGA_PER_AKUN:,}/account*\n"
            f"💵 Total value: *Rp {format_rupiah(config.HARGA_PER_AKUN * stock)}*"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif action == "orders":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
        ])
        try:
            user_id = update.effective_user.id
            orders = db.get_user_orders(user_id)

            if not orders:
                await query.edit_message_text(
                    "No orders yet. Buy now! 🛒",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
                        [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
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
                lines.append(f"#{order_id} | {qty} accounts | Rp {format_rupiah(total)} | {emoji} {status}")

            await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

        except Exception as e:
            logger.exception("handle_menu orders error: %s", e)
            await query.edit_message_text("Sorry, something went wrong. Please try again.", reply_markup=keyboard)

    elif action == "admin":
        if update.effective_user.id not in config.ADMIN_IDS:
            await query.answer("Access denied.", show_alert=True)
            return

        stock = db.get_stock_count()
        sold = db.get_total_sold()
        total_users = db.get_total_users()
        products = db.get_active_products()
        pending = len(db.get_pending_qris_orders())

        text = (
            f"*⚙️ ADMIN PANEL*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*📊 Dashboard*\n"
            f"📦 Stock Ready : *{stock}* accounts\n"
            f"✅ Sold : *{sold}* accounts\n"
            f"⏳ Pending Orders : *{pending}*\n"
            f"👥 Total Users : *{total_users}*\n"
            f"🛍️ Total Products : *{len(products)}*\n"
            f"💰 Price : *Rp {format_rupiah(config.HARGA_PER_AKUN)}/account*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Select admin menu below 👇"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_panel_keyboard())

    elif action == "help":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:start")],
        ])
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
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


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

    action = query.data.split(":")[1] if query.data else ""

    if action == "products":
        products = db.get_all_products()
        if not products:
            await query.edit_message_text(
                "*📦 Product List*\n\nNo products yet.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_back_keyboard(),
            )
            return

        lines = ["*📦 PRODUCT LIST*\n"]
        for p in products:
            stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "Unlimited"
            status = "✅" if p["is_active"] else "❌"
            lines.append(
                f"{status} #{p['id']} | *{p['name']}*\n"
                f"   💰 Price: Rp {format_rupiah(p['price'])}\n"
                f"   📦 Stock: {stock}\n"
            )

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_back_keyboard(),
        )

    elif action == "stockinfo":
        stock = db.get_stock_count()
        pending = len(db.get_pending_qris_orders())
        products = db.get_active_products()

        text = (
            f"*📊 STOCK INFO*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Ready Stock: *{stock}* accounts\n"
            f"⏳ Pending Orders: *{pending}*\n"
        )
        for p in products:
            p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            text += f"\n#{p['id']} {p['name']}: *{p_stock}* | Rp {format_rupiah(p['price'])}"

        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_back_keyboard())

    elif action == "orders":
        try:
            orders = db.get_all_orders(limit=20)
        except Exception as exc:
            logger.exception("Failed get_all_orders: %s", exc)
            await query.edit_message_text("Sorry, something went wrong.", reply_markup=get_admin_back_keyboard())
            return

        if not orders:
            await query.edit_message_text(
                "*📋 RECENT ORDERS*\n\nNo orders yet.",
                parse_mode=ParseMode.MARKDOWN,
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
            product_name = product["name"] if product else "N/A"

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
        back_row = [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")]
        keyboard_rows.append(back_row)

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_pending":
        try:
            orders = db.get_all_orders(limit=20, status="pending")
        except Exception:
            await query.edit_message_text("Sorry, something went wrong.", reply_markup=get_admin_back_keyboard())
            return

        if not orders:
            await query.edit_message_text(
                "*⏳ PENDING ORDERS*\n\nNo pending orders.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_back_keyboard(),
            )
            return

        lines = [f"*⏳ PENDING ORDERS* ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            order_id = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = product["name"] if product else "N/A"
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

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_paid":
        try:
            orders = db.get_all_orders(limit=20, status="paid")
        except Exception:
            await query.edit_message_text("Sorry, something went wrong.", reply_markup=get_admin_back_keyboard())
            return

        if not orders:
            await query.edit_message_text(
                "*✅ PAID ORDERS*\n\nNo paid orders.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_back_keyboard(),
            )
            return

        lines = [f"*✅ PAID ORDERS* ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            order_id = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = product["name"] if product else "N/A"
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

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "adminlist":
        lines = ["*👥 ADMIN LIST*\n"]
        for i, admin_id in enumerate(sorted(config.ADMIN_IDS), 1):
            is_main = " ⭐" if admin_id == config.ADMIN_USER_ID else ""
            lines.append(f"{i}. `{admin_id}`{is_main}")

        lines.append(f"\n📊 Total: *{len(config.ADMIN_IDS)}* admins")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_back_keyboard(),
        )

    elif action == "addproduct":
        text = (
            "*➕ ADD PRODUCT*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Format:\n"
            "`ProductName|Price|Description`\n\n"
            "*Examples:*\n"
            "`Leonardo|10000|Leonardo AI Account`\n"
            "`GSuite|100000|GSuite 30 days`\n\n"
            "Description is optional."
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_back_keyboard())

    elif action == "addstock":
        text = (
            "*📥 ADD STOCK*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*Method 1:* Send a .txt file with format:\n"
            "`email:password:balance`\n\n"
            "*Method 2:* Paste directly in chat:\n"
            "`email1:pass1:balance1`\n"
            "`email2:pass2:balance2`\n\n"
            "Or use command:\n"
            "`/addstock` then send file/txt\n\n"
            "Send now! 📤"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_back_keyboard())

    elif action == "setprice":
        text = (
            f"*💰 CHANGE PRICE*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Current price: *Rp {format_rupiah(config.HARGA_PER_AKUN)}/account*\n\n"
            f"Type command:\n"
            f"`/setprice NewPrice`\n\n"
            f"*Example:*\n"
            f"`/setprice 15000`"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_back_keyboard())

    elif action == "broadcast":
        text = (
            "*📣 BROADCAST*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send a message to all users.\n\n"
            "Type command:\n"
            "`/broadcast Your Message`\n\n"
            "*Example:*\n"
            "`/broadcast Weekend promo 20% off!`"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_back_keyboard())

    elif action == "addadmin":
        text = (
            "*👤 ADD ADMIN*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Type command:\n"
            "`/addadmin TelegramUserID`\n\n"
            "*Example:*\n"
            "`/addadmin 123456789`\n\n"
            "💡 To find ID: Forward a message to @userinfobot"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_back_keyboard())

    elif action == "removeadmin":
        text = (
            "*👤 REMOVE ADMIN*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Type command:\n"
            "`/removeadmin TelegramUserID`\n\n"
            "*Example:*\n"
            "`/removeadmin 123456789`\n\n"
            "⚠️ Cannot remove main admin."
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_back_keyboard())
