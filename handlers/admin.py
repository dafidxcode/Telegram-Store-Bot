"""Admin command handlers.

- /addstock - Upload .txt file or paste stock (email:password:balance)
- /stockinfo - Lihat info stok
- /orders - Lihat order terbaru + ubah status
- /broadcast - Kirim pesan ke semua user
- /setprice - Ubah harga per akun
"""

import logging

from telegram import Update
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
    "pending": "\u23f3",
    "paid": "\u2705",
    "cancelled": "\u274c",
    "delivered": "\uD83D\uDCE6",
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


def register(app: Application) -> None:
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


async def cmd_addstock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    await message.reply_text(
        "*Cara tambah stok:*\n\n"
        "1. Kirim file .txt dengan format per baris:\n"
        "`email:password:balance`\n\n"
        "2. Atau paste langsung daftar akun di chat (satu akun per baris)\n\n"
        "Kirim sekarang:",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_addstock_txt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    await message.reply_text(
        "Kirim file .txt dengan format per baris:\n"
        "`email:password:balance`\n\n"
        "Atau paste langsung di chat:",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return

    message = update.message
    if message is None or message.document is None:
        return

    doc = message.document
    if doc.mime_type and "text" not in doc.mime_type and not doc.file_name.endswith(".txt"):
        await message.reply_text("Hanya file .txt yang diterima.")
        return

    try:
        file = await doc.get_file()
        content = await file.download_as_bytearray()
        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()
    except Exception as e:
        logger.exception("Gagal download file: %s", e)
        await message.reply_text("Gagal membaca file. Coba lagi.")
        return

    count = db.add_stock_batch(lines)
    stock = db.get_stock_count()

    await message.reply_text(
        f"*Stok berhasil ditambahkan!*\n\n"
        f" Ditambah: *{count}* akun\n"
        f" Total stok: *{stock}* akun",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_stockinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    stock = db.get_stock_count()
    pending = len(db.get_pending_qris_orders())

    await update.message.reply_text(
        f"*Info Stok*\n\n"
        f"Stok ready: *{stock}* akun\n"
        f"Order pending: *{pending}*\n"
        f"Harga/akun: *Rp {config.HARGA_PER_AKUN:,}*",
        parse_mode=ParseMode.MARKDOWN,
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
        await message.reply_text("Maaf, ada masalah. Coba lagi.")
        return

    if not orders:
        await message.reply_text("Belum ada order.")
        return

    lines = [f"*Order Terbaru* ({len(orders)})\n"]

    for o in orders:
        username = o.get("username") or "no_user"
        status = o.get("status", "pending")
        emoji = _STATUS_EMOJI.get(status, "\u23f3")
        order_id = o["id"]

        lines.append(
            f"#{order_id} | @{username}\n"
            f"Jumlah: {o['quantity']} akun = Rp {format_rupiah(o['total'])}\n"
            f"Status: {emoji} {status}\n"
            f"{o.get('created_at', '')}\n"
        )

    await message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_setprice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            f"Harga saat ini: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
            "Gunakan: /setprice <harga_baru>",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        new_price = int(args[0].replace(".", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("Harga harus berupa angka.")
        return

    if new_price <= 0:
        await update.message.reply_text("Harga harus lebih dari 0.")
        return

    config.HARGA_PER_AKUN = new_price
    await update.message.reply_text(
        f"Harga diubah ke *Rp {new_price:,}/akun*",
        parse_mode=ParseMode.MARKDOWN,
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
        await message.reply_text("Gunakan: /broadcast <pesan>")
        return

    try:
        user_ids = db.get_all_user_ids()
    except Exception as exc:
        logger.exception("Gagal get_all_user_ids: %s", exc)
        await message.reply_text("Maaf, ada masalah. Coba lagi.")
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
        f"Broadcast terkirim ke *{success}* user. Gagal: *{failed}*.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Gunakan: /addadmin <telegram_user_id>\n\n"
            "Untuk cari ID:Forward pesan dari user ke @userinfobot",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        new_admin_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID harus berupa angka.")
        return

    if new_admin_id in config.ADMIN_IDS:
        await update.message.reply_text(f"ID {new_admin_id} sudah menjadi admin.")
        return

    config.ADMIN_IDS.add(new_admin_id)
    await update.message.reply_text(
        f"Admin ditambahkan: `{new_admin_id}`\n"
        f"Total admin: *{len(config.ADMIN_IDS)}*",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    args = context.args or []
    if not args:
        await update.message.reply_text("Gunakan: /removeadmin <telegram_user_id>")
        return

    try:
        remove_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID harus berupa angka.")
        return

    if remove_id == config.ADMIN_USER_ID:
        await update.message.reply_text("Tidak bisa menghapus admin utama.")
        return

    if remove_id not in config.ADMIN_IDS:
        await update.message.reply_text(f"ID {remove_id} bukan admin.")
        return

    config.ADMIN_IDS.discard(remove_id)
    await update.message.reply_text(
        f"Admin dihapus: `{remove_id}`\n"
        f"Total admin: *{len(config.ADMIN_IDS)}*",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    lines = ["*Daftar Admin*\n"]
    for i, admin_id in enumerate(sorted(config.ADMIN_IDS), 1):
        is_main = " (utama)" if admin_id == config.ADMIN_USER_ID else ""
        lines.append(f"{i}. `{admin_id}`{is_main}")

    lines.append(f"\nTotal: *{len(config.ADMIN_IDS)}* admin")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
