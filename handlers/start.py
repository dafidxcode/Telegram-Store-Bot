"""Start, help, and menu command handlers with inline keyboard buttons."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
import db

logger = logging.getLogger(__name__)


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def get_main_menu_keyboard(user_id: int = 0):
    rows = [
        [
            InlineKeyboardButton("Beli Sekarang", callback_data="menu:beli"),
            InlineKeyboardButton("Cek Stok", callback_data="menu:stok"),
        ],
        [
            InlineKeyboardButton("Riwayat Order", callback_data="menu:orders"),
            InlineKeyboardButton("Bantuan", callback_data="menu:help"),
        ],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton("Admin Panel", callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stock", cmd_stock))
    app.add_handler(CallbackQueryHandler(handle_menu_button, pattern=r"^menu:"))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if user is None or message is None:
        return

    try:
        db.upsert_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("Gagal upsert user %s: %s", user.id, exc)

    stock = db.get_stock_count()
    first_name = user.first_name or "teman"

    text = (
        f" Halo {first_name}!\n\n"
        f"Selamat datang di *{config.SHOP_NAME}*.\n\n"
        f" Harga: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
        f" Stok tersedia: *{stock}* akun\n\n"
        "Pilih menu di bawah untuk mulai:"
    )

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(user.id))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
    ])

    text = (
        "*Bantuan*\n\n"
        "*Cara Beli:*\n"
        "1. Klik *Beli Sekarang*\n"
        "2. Pilih jumlah akun\n"
        "3. Konfirmasi & bayar via QRIS\n"
        "4. Akun otomatis dikirim\n\n"
        "*Commands:*\n"
        "/start - Menu utama\n"
        "/beli - Beli akun\n"
        "/stock - Cek stok\n"
        "/myorders - Riwayat order\n"
        "/cancel - Batalkan proses"
    )

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    stock = db.get_stock_count()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Beli Sekarang", callback_data="menu:beli")],
        [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
    ])

    await message.reply_text(
        f"*Info Stok*\n\n"
        f"Stok tersedia: *{stock}* akun\n"
        f"Harga: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
        f"Total nilai: *Rp {format_rupiah(config.HARGA_PER_AKUN * stock)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    action = query.data.split(":")[1] if query.data else ""

    if action == "start":
        stock = db.get_stock_count()
        first_name = (update.effective_user.first_name or "teman") if update.effective_user else "teman"
        user_id = (update.effective_user.id or 0) if update.effective_user else 0
        text = (
            f" Halo {first_name}!\n\n"
            f"Selamat datang di *{config.SHOP_NAME}*.\n\n"
            f" Harga: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
            f" Stok tersedia: *{stock}* akun\n\n"
            "Pilih menu di bawah untuk mulai:"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(user_id))

    elif action == "beli":
        stock = db.get_stock_count()
        if stock <= 0:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
            ])
            await query.edit_message_text(
                "Maaf, stok kosong. Silakan tunggu admin menambah stok.",
                reply_markup=keyboard,
            )
            return

        buttons = []
        for qty in [1, 2, 3, 5, 10, 20]:
            if qty <= stock:
                total = config.HARGA_PER_AKUN * qty
                buttons.append([InlineKeyboardButton(
                    f"{qty} Akun - Rp {format_rupiah(total)}",
                    callback_data=f"buy:{qty}",
                )])

        buttons.append([InlineKeyboardButton("Jumlah Lainnya", callback_data="buy:custom")])
        buttons.append([InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")])

        text = (
            f"*Beli Akun*\n\n"
            f"Harga: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
            f"Stok tersedia: *{stock}* akun\n\n"
            "Pilih jumlah:"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "stok":
        stock = db.get_stock_count()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Beli Sekarang", callback_data="menu:beli")],
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])
        text = (
            f"*Info Stok*\n\n"
            f"Stok tersedia: *{stock}* akun\n"
            f"Harga: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
            f"Total nilai: *Rp {format_rupiah(config.HARGA_PER_AKUN * stock)}*"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif action == "orders":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])
        try:
            user_id = update.effective_user.id
            orders = db.get_user_orders(user_id)

            if not orders:
                await query.edit_message_text(
                    "Belum ada orderan. Yuk beli sekarang!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Beli Sekarang", callback_data="menu:beli")],
                        [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
                    ]),
                )
                return

            _STATUS_EMOJI = {"pending": "\u23f3", "paid": "\u2705", "cancelled": "\u274c", "delivered": "\uD83D\uDCE6"}
            recent = orders[:10]
            lines = ["*Riwayat Order*\n"]

            for o in recent:
                order_id = o.get("id", "")
                qty = o.get("quantity", 0)
                total = o.get("total", 0)
                status = o.get("status", "pending")
                emoji = _STATUS_EMOJI.get(status, "\u23f3")
                lines.append(f"#{order_id} | {qty} akun | Rp {format_rupiah(total)} | {emoji} {status}")

            await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

        except Exception as e:
            logger.exception("handle_menu orders error: %s", e)
            await query.edit_message_text("Maaf, ada masalah. Coba lagi.", reply_markup=keyboard)

    elif action == "admin":
        if update.effective_user.id not in config.ADMIN_IDS:
            await query.answer("Akses ditolak.", show_alert=True)
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Kelola Stok", callback_data="menu:beli")],
            [InlineKeyboardButton("Info Stok & Order", callback_data="menu:stok")],
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])
        await query.edit_message_text(
            "*Admin Panel*\n\n"
            "Gunakan /orders - Lihat order\n"
            "/stockinfo - Info stok\n"
            "/setprice <harga> - Ubah harga\n"
            "/addstock - Tambah stok\n"
            "/broadcast <pesan> - Kirim pesan\n"
            "/addadmin <id> - Tambah admin\n"
            "/removeadmin <id> - Hapus admin\n"
            "/adminlist - Lihat daftar admin",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    elif action == "help":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])
        text = (
            "*Bantuan*\n\n"
            "*Cara Beli:*\n"
            "1. Klik *Beli Sekarang*\n"
            "2. Pilih jumlah akun\n"
            "3. Konfirmasi & bayar via QRIS\n"
            "4. Akun otomatis dikirim\n\n"
            "*Commands:*\n"
            "/start - Menu utama\n"
            "/beli - Beli akun\n"
            "/stock - Cek stok\n"
            "/myorders - Riwayat order\n"
            "/cancel - Batalkan proses"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
