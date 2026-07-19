"""Start, help, and menu command handlers with inline keyboard buttons."""

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
import db

logger = logging.getLogger(__name__)

WIB_OFFSET = 7 * 3600


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def get_now_wib() -> str:
    import time
    now_utc = time.time() + WIB_OFFSET
    from datetime import datetime as dt, timezone, timedelta
    wib = dt.fromtimestamp(now_utc, tz=timezone(timedelta(hours=7)))
    day = wib.day
    suffix = ["", "st", "nd", "rd"][day] if day % 100 not in (11, 12, 13) and day % 10 in (1, 2, 3) else "th"
    return wib.strftime(f"%-d{suffix} %B %Y pukul %-H:%M WIB")


def get_greeting() -> str:
    from datetime import datetime as dt, timezone, timedelta
    hour = (dt.now(tz=timezone(timedelta(hours=7)))).hour
    if 4 <= hour < 11:
        return "Selamat Pagi"
    elif 11 <= hour < 15:
        return "Selamat Siang"
    elif 15 <= hour < 18:
        return "Selamat Sore"
    else:
        return "Selamat Malam"


def build_home_text(user) -> tuple[str, dict]:
    stock = db.get_stock_count()
    sold = db.get_total_sold()
    total_users = db.get_total_users()
    user_orders = db.get_user_order_count(user.id)
    username = f"@{user.username}" if user.username else "Tidak ada"
    first_name = user.first_name or "teman"

    text = (
        f"{get_greeting()}, {first_name}!\n"
        f"{get_now_wib()}\n"
        f"\n"
        f"Selamat datang di *{config.SHOP_NAME}*.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"  STATISTIK AKUN\n"
        f"Username : {username}\n"
        f"ID : {user.id}\n"
        f"Total Order : {user_orders} transaksi\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"  STATISTIK BOT\n"
        f"Akun Terjual : {sold}\n"
        f"Harga : Rp {format_rupiah(config.HARGA_PER_AKUN)}/akun\n"
        f"Stok Akun : {stock}\n"
        f"Total User : {total_users}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"Mulai dari mana?\n"
        f"Beli akun → Beli Sekarang\n"
        f"Cek transaksi → Riwayat Order"
    )
    return text, {"stock": stock, "sold": sold, "user_orders": user_orders}


def get_main_menu_keyboard(user_id: int = 0):
    rows = [
        [
            InlineKeyboardButton("Beli Akun", callback_data="menu:beli"),
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

    text, _ = build_home_text(user)
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
        "1. Klik *Beli Akun*\n"
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
        [InlineKeyboardButton("Beli Akun", callback_data="menu:beli")],
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
        user = update.effective_user
        text, _ = build_home_text(user)
        uid = (user.id or 0) if user else 0
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(uid))

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
            [InlineKeyboardButton("Beli Akun", callback_data="menu:beli")],
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
                        [InlineKeyboardButton("Beli Akun", callback_data="menu:beli")],
                        [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
                    ]),
                )
                return

            _STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦"}
            recent = orders[:10]
            lines = ["*Riwayat Order*\n"]

            for o in recent:
                order_id = o.get("id", "")
                qty = o.get("quantity", 0)
                total = o.get("total", 0)
                status = o.get("status", "pending")
                emoji = _STATUS_EMOJI.get(status, "⏳")
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
            [InlineKeyboardButton("Kembali ke Menu", callback_data="menu:start")],
        ])
        await query.edit_message_text(
            "*Admin Panel*\n\n"
            "/orders - Lihat order\n"
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
            "1. Klik *Beli Akun*\n"
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
