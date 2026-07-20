"""Admin command handlers.

- /addproduct - Add new product
- /editproduct - Edit product
- /delproduct - Delete product
- /products - View all products
- /addstock - Upload .txt file or paste stock
- /stockinfo - View stock info
- /orders - View recent orders + change status
- /broadcast - Send message to all users
- /setprice - Change price per product
- /addadmin - Add admin
- /removeadmin - Remove admin
- /adminlist - View admin list
"""

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import db
from handlers.start import btn_home, escape_md

logger = logging.getLogger(__name__)

_STATUS_EMOJI = {
    "pending": "⏳",
    "paid": "✅",
    "cancelled": "❌",
    "delivered": "📦",
}

_QUICK_ADD_RE = re.compile(r"^([^|]+)\|(\d{1,})\|?(.*)$")


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in config.ADMIN_IDS


async def _deny_non_admin(update: Update) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("This command is for admins only.")


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _admin_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")],
        [btn_home()],
    ])


async def handle_quick_addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Detect Name|Price|Description pattern and add product. Returns True if handled."""
    if not _is_admin(update):
        return False

    message = update.message
    if message is None or not message.text:
        return False

    text = message.text.strip()
    m = _QUICK_ADD_RE.match(text)
    if not m:
        return False

    name = m.group(1).strip()
    try:
        price = int(m.group(2))
    except ValueError:
        return False

    description = m.group(3).strip() if m.group(3) else ""

    if not name or price <= 0:
        return False

    product_id = db.add_product(name=name, description=description, price=price)
    await message.reply_text(
        f"*✅ Product added!*\n\n"
        f"🆔 ID: `{product_id}`\n"
        f"📦 Name: *{name}*\n"
        f"💰 Price: *Rp {format_rupiah(price)}*\n"
        f"📝 Description: {description or '-'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )
    return True


def register(app: Application) -> None:
    app.add_handler(CommandHandler("addproduct", cmd_addproduct))
    app.add_handler(CommandHandler("editproduct", cmd_editproduct))
    app.add_handler(CommandHandler("delproduct", cmd_delproduct))
    app.add_handler(CommandHandler("products", cmd_products))
    app.add_handler(CommandHandler("addstock", cmd_addstock))
    app.add_handler(CommandHandler("addstocktxt", cmd_addstock_txt))
    app.add_handler(CommandHandler("stockinfo", cmd_stockinfo))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("setprice", cmd_setprice))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("adminlist", cmd_adminlist))
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
            handle_quick_addproduct_text,
        ),
    )
    app.add_handler(
        MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_document),
    )


# ---------------------------------------------------------------------------
# Stock / product text handler (must come BEFORE quick-add-product)
# ---------------------------------------------------------------------------

async def handle_quick_addproduct_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """If in addstock mode, try parsing as email:password. Otherwise try quick-add product."""
    # Handle interactive admin states
    admin_state = context.user_data.get("admin_state")

    if admin_state == "addproduct_name":
        message = update.message
        if message is None or not message.text:
            return
        name = message.text.strip()
        if not name:
            await message.reply_text("Name cannot be empty. Send product name:")
            return
        context.user_data["admin_state"] = "addproduct_price"
        context.user_data["addproduct_name"] = name
        await message.reply_text(
            f"📦 Product name: *{name}*\n\n📝 Send the *price* (number only).\nExample: `15000`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    if admin_state == "addproduct_price":
        message = update.message
        if message is None or not message.text:
            return
        try:
            price = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text("Price must be a number. Send again:")
            return
        if price <= 0:
            await message.reply_text("Price must be > 0. Send again:")
            return
        context.user_data["admin_state"] = "addproduct_desc"
        context.user_data["addproduct_price"] = price
        await message.reply_text(
            f"💰 Price: *Rp {format_rupiah(price)}*\n\n📝 Send the *description* (or send `-` to skip).",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    if admin_state == "addproduct_desc":
        message = update.message
        if message is None or not message.text:
            return
        desc = message.text.strip()
        if desc == "-":
            desc = ""
        name = context.user_data.pop("addproduct_name", "")
        price = context.user_data.pop("addproduct_price", 0)
        context.user_data.pop("admin_state", None)

        if not name or price <= 0:
            await message.reply_text("Something went wrong. Start again.", reply_markup=_admin_back_keyboard())
            return

        product_id = db.add_product(name=name, description=desc, price=price)
        await message.reply_text(
            f"*✅ Product added!*\n\n"
            f"🆔 ID: `{product_id}`\n"
            f"📦 Name: *{escape_md(name)}*\n"
            f"💰 Price: *Rp {format_rupiah(price)}*\n"
            f"📝 Description: {desc or '-'}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    if admin_state == "setprice_value":
        message = update.message
        if message is None or not message.text:
            return
        try:
            new_price = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text("Price must be a number. Send again:")
            return
        if new_price <= 0:
            await message.reply_text("Price must be > 0. Send again:")
            return
        product_id = context.user_data.pop("setprice_product_id", None)
        context.user_data.pop("admin_state", None)
        if product_id:
            db.update_product(product_id, price=new_price)
            product = db.get_product(product_id)
            product_name = escape_md(product["name"]) if product else "Unknown"
            await message.reply_text(
                f"📦 Product: *{product_name}*\n"
                f"💰 New price: *Rp {format_rupiah(new_price)}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(),
            )
        else:
            await message.reply_text("Something went wrong.", reply_markup=_admin_back_keyboard())
        return

    if admin_state == "broadcast_msg":
        message = update.message
        if message is None or not message.text:
            return
        text = message.text.strip()
        context.user_data.pop("admin_state", None)

        try:
            user_ids = db.get_all_user_ids()
        except Exception:
            await message.reply_text("Failed to get users.", reply_markup=_admin_back_keyboard())
            return

        success = 0
        failed = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.MARKDOWN)
                success += 1
            except Exception:
                failed += 1

        await message.reply_text(
            f"*✅ Broadcast complete!*\n\n"
            f"📤 Sent: *{success}* users\n"
            f"❌ Failed: *{failed}* users",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    if admin_state == "addadmin_id":
        message = update.message
        if message is None or not message.text:
            return
        try:
            new_admin_id = int(message.text.strip())
        except ValueError:
            await message.reply_text("ID must be a number. Send again:")
            return
        context.user_data.pop("admin_state", None)
        if new_admin_id in config.ADMIN_IDS:
            await message.reply_text(
                f"ID `{new_admin_id}` is already an admin.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(),
            )
            return
        config.ADMIN_IDS.add(new_admin_id)
        await message.reply_text(
            f"*✅ Admin added!*\n\n"
            f"🆔 ID: `{new_admin_id}`\n"
            f"👥 Total admins: *{len(config.ADMIN_IDS)}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    # Handle addstock mode
    addstock_pid = context.user_data.get("addstock_product_id")
    if addstock_pid:
        message = update.message
        if message is None or not message.text:
            return

        lines = message.text.strip().splitlines()
        count = db.add_stock_batch(lines, product_id=addstock_pid)

        product = db.get_product(addstock_pid)
        stock = db.get_stock_count(addstock_pid)
        product_name = product["name"] if product else "Unknown"

        context.user_data.pop("addstock_product_id", None)
        context.user_data.pop("state", None)

        if count > 0:
            await message.reply_text(
                f"*✅ Stock added to {product_name}!*\n\n"
                f"📥 Added: *{count}* accounts\n"
                f"📦 Product stock: *{stock}* accounts\n\n"
                f"💡 Send more stock or click Back below.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"📥 Add More to {product_name}", callback_data=f"admin:astk:{addstock_pid}")],
                    [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")],
                    [btn_home()],
                ]),
            )
        else:
            await message.reply_text(
                f"*⚠️ No stock added to {product_name}*\n\n"
                f"Please check format:\n"
                f"`email:password`\n"
                f"one account per line.\n\n"
                f"Current product stock: *{stock}* accounts",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🔄 Try Again — {product_name}", callback_data=f"admin:astk:{addstock_pid}")],
                    [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="menu:admin")],
                    [btn_home()],
                ]),
            )
        return

    await handle_quick_addproduct(update, context)


# ---------------------------------------------------------------------------
# Product management
# ---------------------------------------------------------------------------

async def cmd_addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    raw = update.message.text.replace("/addproduct", "").strip() if update.message.text else ""
    if not raw or "|" not in raw:
        await update.message.reply_text(
            "*➕ ADD PRODUCT*\n\n"
            "Format: `/addproduct ProductName|Price|Description`\n\n"
            "*Examples:*\n"
            "`/addproduct Leonardo|10000|Leonardo AI Account`\n"
            "`/addproduct GSuite|100000|GSuite 30 days`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    parts = [p.strip() for p in raw.split("|")]
    name = parts[0]
    if not name:
        await update.message.reply_text(
            "Product name cannot be empty.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        price = int(parts[1])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Price must be a number.\n\n"
            "Format: `/addproduct ProductName|Price|Description`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    description = parts[2] if len(parts) > 2 else ""

    product_id = db.add_product(name=name, description=description, price=price)
    await update.message.reply_text(
        f"*✅ Product added!*\n\n"
        f"🆔 ID: `{product_id}`\n"
        f"📦 Name: *{name}*\n"
        f"💰 Price: *Rp {format_rupiah(price)}*\n"
        f"📝 Description: {description or '-'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_editproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "*✏️ EDIT PRODUCT*\n\n"
            "Use: `/editproduct <id> <field>=<value>`\n\n"
            "*Fields:* name, price, description, stock_type, stock_count, duration, is_active\n\n"
            "*Examples:*\n"
            "`/editproduct 1 price=15000`\n"
            "`/editproduct 1 name=Leonardo Pro`\n"
            "`/editproduct 1 is_active=0` (deactivate)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "ID must be a number.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            f"Product ID `{product_id}` not found.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    kwargs = {}
    for arg in args[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k == "price":
                kwargs["price"] = int(v)
            elif k == "stock_count":
                kwargs["stock_count"] = int(v)
            elif k == "is_active":
                kwargs["is_active"] = int(v)
            elif k in ("name", "description", "stock_type", "duration"):
                kwargs[k] = v

    if not kwargs:
        await update.message.reply_text(
            "No changes made. Use field=value.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    db.update_product(product_id, **kwargs)
    updated = db.get_product(product_id)
    await update.message.reply_text(
        f"*✅ Product updated!*\n\n"
        f"🆔 ID: `{product_id}`\n"
        f"📦 Name: *{updated['name']}*\n"
        f"💰 Price: *Rp {format_rupiah(updated['price'])}*\n"
        f"📦 Stock: {updated['stock_type']} ({updated['stock_count']})\n"
        f"{'✅ Active' if updated['is_active'] else '❌ Inactive'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_delproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Use: `/delproduct <id>`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "ID must be a number.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            f"Product ID `{product_id}` not found.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    db.delete_product(product_id)
    await update.message.reply_text(
        f"*🗑️ Product deleted!*\n\n"
        f"📦 Name: *{escape_md(product['name'])}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    products = db.get_all_products()
    if not products:
        await update.message.reply_text(
            "*📦 PRODUCT LIST*\n\nNo products yet.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
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

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


# ---------------------------------------------------------------------------
# Stock management
# ---------------------------------------------------------------------------

async def cmd_addstock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    products = db.get_active_products()
    if not products:
        await message.reply_text(
            "*📥 ADD STOCK*\n\nNo active products yet. Add a product first.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
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

    await message.reply_text(
        "*📥 ADD STOCK*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nSelect product to add stock to:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_addstock_txt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    await message.reply_text(
        "*📥 ADD STOCK*\n\n"
        "Send a .txt file with format per line:\n"
        "`email:password`\n\n"
        "Or paste directly in chat:\n"
        "`email1:password1`\n"
        "`email2:password2`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return

    message = update.message
    if message is None or message.document is None:
        return

    doc = message.document
    if doc.mime_type and "text" not in doc.mime_type and not doc.file_name.endswith(".txt"):
        await message.reply_text(
            "Only .txt files are accepted.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        file = await doc.get_file()
        content = await file.download_as_bytearray()
        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()
    except Exception as e:
        logger.exception("Failed to download file: %s", e)
        await message.reply_text(
            "Failed to read file. Please try again.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    addstock_pid = context.user_data.get("addstock_product_id")
    count = db.add_stock_batch(lines, product_id=addstock_pid or 1)
    product_id_used = addstock_pid
    context.user_data.pop("addstock_product_id", None)
    context.user_data.pop("state", None)

    product = db.get_product(product_id_used) if product_id_used else None
    stock = db.get_stock_count(product_id_used) if product_id_used else db.get_stock_count()
    product_label = product["name"] if product else "default product"

    if count > 0:
        await message.reply_text(
            f"*✅ Stock added successfully!*\n\n"
            f"📦 Product: *{product_label}*\n"
            f"📥 Added: *{count}* accounts\n"
            f"📦 Stock: *{stock}* accounts",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
    else:
        await message.reply_text(
            f"*⚠️ No stock added*\n\n"
            f"Check format: `email:password` per line.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )


async def cmd_stockinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

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

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    status_filter = context.args[0] if context.args else None

    try:
        orders = db.get_all_orders(limit=20, status=status_filter)
    except Exception as exc:
        logger.exception("Failed get_all_orders: %s", exc)
        await message.reply_text(
            "Sorry, something went wrong. Please try again.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    if not orders:
        await message.reply_text(
            "*📋 RECENT ORDERS*\n\nNo orders yet.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
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

    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard_rows),
    )


async def cmd_setprice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "*💰 CHANGE PRICE*\n\n"
            "Use: `/setprice <product_id> <new_price>`\n\n"
            "*Example:*\n"
            "`/setprice 1 15000`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Product ID must be a number.", reply_markup=_admin_back_keyboard())
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            f"Product ID `{product_id}` not found.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        new_price = int(args[1].replace(".", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("Price must be a number.", reply_markup=_admin_back_keyboard())
        return

    if new_price <= 0:
        await update.message.reply_text("Price must be greater than 0.", reply_markup=_admin_back_keyboard())
        return

    db.update_product(product_id, price=new_price)
    updated = db.get_product(product_id)
    await update.message.reply_text(
        f"*✅ Price updated!*\n\n"
        f"📦 Product: *{updated['name']}*\n"
        f"💰 New price: *Rp {new_price:,}/account*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    text = " ".join(context.args or []).strip()
    if not text:
        await message.reply_text(
            "*📣 BROADCAST*\n\n"
            "Send a message to all users.\n\n"
            "Use: `/broadcast <message>`\n\n"
            "*Example:* `/broadcast Weekend promo 20% off!`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        user_ids = db.get_all_user_ids()
    except Exception as exc:
        logger.exception("Failed get_all_user_ids: %s", exc)
        await message.reply_text(
            "Sorry, something went wrong. Please try again.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    success = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.MARKDOWN)
            success += 1
        except Exception:
            failed += 1

    await message.reply_text(
        f"*✅ Broadcast complete!*\n\n"
        f"📤 Sent: *{success}* users\n"
        f"❌ Failed: *{failed}* users",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "*👤 ADD ADMIN*\n\n"
            "Use: `/addadmin <telegram_user_id>`\n\n"
            "*Example:* `/addadmin 123456789`\n\n"
            "💡 To find ID: Forward a message to @userinfobot",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        new_admin_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.", reply_markup=_admin_back_keyboard())
        return

    if new_admin_id in config.ADMIN_IDS:
        await update.message.reply_text(
            f"ID `{new_admin_id}` is already an admin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    config.ADMIN_IDS.add(new_admin_id)
    await update.message.reply_text(
        f"*✅ Admin added!*\n\n"
        f"🆔 ID: `{new_admin_id}`\n"
        f"👥 Total admins: *{len(config.ADMIN_IDS)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "*👤 REMOVE ADMIN*\n\n"
            "Use: `/removeadmin <telegram_user_id>`\n\n"
            "⚠️ Cannot remove the main admin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        remove_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.", reply_markup=_admin_back_keyboard())
        return

    if remove_id == config.ADMIN_USER_ID:
        await update.message.reply_text(
            "Cannot remove the main admin.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    if remove_id not in config.ADMIN_IDS:
        await update.message.reply_text(
            f"ID `{remove_id}` is not an admin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    config.ADMIN_IDS.discard(remove_id)
    await update.message.reply_text(
        f"*✅ Admin removed!*\n\n"
        f"🆔 ID: `{remove_id}`\n"
        f"👥 Total admins: *{len(config.ADMIN_IDS)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    lines = ["*👥 ADMIN LIST*\n"]
    for i, admin_id in enumerate(sorted(config.ADMIN_IDS), 1):
        is_main = " ⭐" if admin_id == config.ADMIN_USER_ID else ""
        lines.append(f"{i}. `{admin_id}`{is_main}")

    lines.append(f"\n📊 Total: *{len(config.ADMIN_IDS)}* admins")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )
