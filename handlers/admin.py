"""Admin command handlers.

- /addproduct - Tambah produk baru
- /editproduct - Edit produk
- /delproduct - Hapus produk
- /products - Lihat semua produk
- /addstock - Upload .txt file atau paste stock
- /stockinfo - Lihat info stok
- /orders - Lihat order terbaru + ubah status
- /broadcast - Kirim pesan ke semua user
- /setprice - Ubah harga per akun
- /addadmin - Tambah admin
- /removeadmin - Hapus admin
- /adminlist - Lihat daftar admin
"""

import logging

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

logger = logging.getLogger(__name__)

_STATUS_EMOJI = {
    "pending": "⏳",
    "paid": "✅",
    "cancelled": "❌",
    "delivered": "📦",
}


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in config.ADMIN_IDS


async def _deny_non_admin(update: Update) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("Perintah ini khusus admin.")


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _admin_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Kembali ke Admin Panel", callback_data="menu:admin")],
        [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
    ])


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
        MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_document),
    )


# ---------------------------------------------------------------------------
# Product management
# ---------------------------------------------------------------------------

async def cmd_addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "*➕ TAMBAH PRODUK*\n\n"
            "Gunakan: `/addproduct <nama> <harga> [deskripsi]`\n\n"
            "*Contoh:*\n"
            "`/addproduct Leonardo 10000 Akun Leonardo AI`\n"
            "`/addproduct GSuite 100000 GSuite durasi 30 hari`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    name = args[0]
    try:
        price = int(args[1])
    except ValueError:
        await update.message.reply_text(
            "Harga harus berupa angka.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    description = " ".join(args[2:]) if len(args) > 2 else ""

    product_id = db.add_product(name=name, description=description, price=price)
    await update.message.reply_text(
        f"*✅ Produk ditambahkan!*\n\n"
        f"🆔 ID: `{product_id}`\n"
        f"📦 Nama: *{name}*\n"
        f"💰 Harga: *Rp {format_rupiah(price)}*\n"
        f"📝 Deskripsi: {description or '-'}",
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
            "*✏️ EDIT PRODUK*\n\n"
            "Gunakan: `/editproduct <id> <field>=<value>`\n\n"
            "*Field:* name, price, description, stock_type, stock_count, duration, is_active\n\n"
            "*Contoh:*\n"
            "`/editproduct 1 price=15000`\n"
            "`/editproduct 1 name=Leonardo Pro`\n"
            "`/editproduct 1 is_active=0` (nonaktifkan)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "ID harus angka.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            f"Produk ID `{product_id}` tidak ditemukan.",
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
            "Tidak ada perubahan. Gunakan field=value.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    db.update_product(product_id, **kwargs)
    updated = db.get_product(product_id)
    await update.message.reply_text(
        f"*✅ Produk diupdate!*\n\n"
        f"🆔 ID: `{product_id}`\n"
        f"📦 Nama: *{updated['name']}*\n"
        f"💰 Harga: *Rp {format_rupiah(updated['price'])}*\n"
        f"📦 Stok: {updated['stock_type']} ({updated['stock_count']})\n"
        f"{'✅ Aktif' if updated['is_active'] else '❌ Nonaktif'}",
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
            "Gunakan: `/delproduct <id>`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "ID harus angka.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            f"Produk ID `{product_id}` tidak ditemukan.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    db.delete_product(product_id)
    await update.message.reply_text(
        f"*🗑️ Produk dihapus!*\n\n"
        f"📦 Nama: *{product['name']}*",
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
            "*📦 DAFTAR PRODUK*\n\nBelum ada produk.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    lines = ["*📦 DAFTAR PRODUK*\n"]
    for p in products:
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "Unlimited"
        status = "✅" if p["is_active"] else "❌"
        lines.append(
            f"{status} #{p['id']} | *{p['name']}*\n"
            f"   💰 Harga: Rp {format_rupiah(p['price'])}\n"
            f"   📦 Stok: {stock}\n"
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

    await message.reply_text(
        "*📥 TAMBAH STOK*\n\n"
        "*Cara 1:* Kirim file .txt dengan format per baris:\n"
        "`email:password:balance`\n\n"
        "*Cara 2:* Paste langsung daftar akun di chat (satu akun per baris)\n\n"
        "Kirim sekarang! 📤",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_addstock_txt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    await message.reply_text(
        "*📥 TAMBAH STOK*\n\n"
        "Kirim file .txt dengan format per baris:\n"
        "`email:password:balance`\n\n"
        "Atau paste langsung di chat:\n"
        "`email1:pass1:balance1`\n"
        "`email2:pass2:balance2`",
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
            "Hanya file .txt yang diterima.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        file = await doc.get_file()
        content = await file.download_as_bytearray()
        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()
    except Exception as e:
        logger.exception("Gagal download file: %s", e)
        await message.reply_text(
            "Gagal membaca file. Coba lagi.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    count = db.add_stock_batch(lines)
    stock = db.get_stock_count()

    await message.reply_text(
        f"*✅ Stok berhasil ditambahkan!*\n\n"
        f"📥 Ditambah: *{count}* akun\n"
        f"📦 Total stok: *{stock}* akun",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_stockinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    stock = db.get_stock_count()
    pending = len(db.get_pending_qris_orders())
    products = db.get_active_products()

    text = (
        f"*📊 INFO STOK*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Stok Ready: *{stock}* akun\n"
        f"⏳ Order Pending: *{pending}*\n"
    )
    for p in products:
        p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        text += f"\n#{p['id']} {p['name']}: *{p_stock}* | Rp {format_rupiah(p['price'])}"

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
        logger.exception("Gagal get_all_orders: %s", exc)
        await message.reply_text(
            "Maaf, ada masalah. Coba lagi.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    if not orders:
        await message.reply_text(
            "*📋 ORDER TERBARU*\n\nBelum ada order.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    lines = [f"*📋 ORDER TERBARU* ({len(orders)})\n"]

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
        InlineKeyboardButton("📋 Semua", callback_data="admin:orders"),
        InlineKeyboardButton("⏳ Pending", callback_data="admin:orders_pending"),
        InlineKeyboardButton("✅ Paid", callback_data="admin:orders_paid"),
    ]
    keyboard_rows = [filter_buttons]
    keyboard_rows.append([InlineKeyboardButton("⬅️ Kembali ke Admin Panel", callback_data="menu:admin")])

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
    if not args:
        await update.message.reply_text(
            f"*💰 UBAH HARGA*\n\n"
            f"Harga saat ini: *Rp {config.HARGA_PER_AKUN:,}/akun*\n\n"
            f"Gunakan: `/setprice <harga_baru>`\n\n"
            f"*Contoh:* `/setprice 15000`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        new_price = int(args[0].replace(".", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text(
            "Harga harus berupa angka.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    if new_price <= 0:
        await update.message.reply_text(
            "Harga harus lebih dari 0.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    config.HARGA_PER_AKUN = new_price
    await update.message.reply_text(
        f"*✅ Harga diubah!*\n\n"
        f"Harga baru: *Rp {new_price:,}/akun*",
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
            "Kirim pesan ke semua user.\n\n"
            "Gunakan: `/broadcast <pesan>`\n\n"
            "*Contoh:* `/broadcast Promo weekend diskon 20%!`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        user_ids = db.get_all_user_ids()
    except Exception as exc:
        logger.exception("Gagal get_all_user_ids: %s", exc)
        await message.reply_text(
            "Maaf, ada masalah. Coba lagi.",
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
        f"*✅ Broadcast selesai!*\n\n"
        f"📤 Terkirim: *{success}* user\n"
        f"❌ Gagal: *{failed}* user",
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
            "*👤 TAMBAH ADMIN*\n\n"
            "Gunakan: `/addadmin <telegram_user_id>`\n\n"
            "*Contoh:* `/addadmin 123456789`\n\n"
            "💡 Untuk cari ID: Forward pesan ke @userinfobot",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        new_admin_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "ID harus berupa angka.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    if new_admin_id in config.ADMIN_IDS:
        await update.message.reply_text(
            f"ID `{new_admin_id}` sudah menjadi admin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    config.ADMIN_IDS.add(new_admin_id)
    await update.message.reply_text(
        f"*✅ Admin ditambahkan!*\n\n"
        f"🆔 ID: `{new_admin_id}`\n"
        f"👥 Total admin: *{len(config.ADMIN_IDS)}*",
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
            "*👤 HAPUS ADMIN*\n\n"
            "Gunakan: `/removeadmin <telegram_user_id>`\n\n"
            "⚠️ Tidak bisa menghapus admin utama.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    try:
        remove_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "ID harus berupa angka.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    if remove_id == config.ADMIN_USER_ID:
        await update.message.reply_text(
            "Tidak bisa menghapus admin utama.",
            reply_markup=_admin_back_keyboard(),
        )
        return

    if remove_id not in config.ADMIN_IDS:
        await update.message.reply_text(
            f"ID `{remove_id}` bukan admin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(),
        )
        return

    config.ADMIN_IDS.discard(remove_id)
    await update.message.reply_text(
        f"*✅ Admin dihapus!*\n\n"
        f"🆔 ID: `{remove_id}`\n"
        f"👥 Total admin: *{len(config.ADMIN_IDS)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )


async def cmd_adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    lines = ["*👥 DAFTAR ADMIN*\n"]
    for i, admin_id in enumerate(sorted(config.ADMIN_IDS), 1):
        is_main = " ⭐" if admin_id == config.ADMIN_USER_ID else ""
        lines.append(f"{i}. `{admin_id}`{is_main}")

    lines.append(f"\n📊 Total: *{len(config.ADMIN_IDS)}* admin")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(),
    )
