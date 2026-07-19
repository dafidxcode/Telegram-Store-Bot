"""Start, help, and menu command handlers with inline keyboard buttons."""

import logging
import time
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
    day = wib.day
    return wib.strftime(f"%-d %B %Y pukul %-H:%M WIB")


def get_greeting() -> str:
    hour = datetime.now(tz=timezone(timedelta(hours=7))).hour
    if 4 <= hour < 11:
        return "Selamat Pagi"
    elif 11 <= hour < 15:
        return "Selamat Siang"
    elif 15 <= hour < 18:
        return "Selamat Sore"
    else:
        return "Selamat Malam"


def build_home_text(user) -> str:
    stock = db.get_stock_count()
    sold = db.get_total_sold()
    total_users = db.get_total_users()
    user_orders = db.get_user_order_count(user.id)
    username = f"@{user.username}" if user.username else "Tidak ada"
    first_name = user.first_name or "teman"

    return (
        f"{get_greeting()}, {first_name}! 🌟\n"
        f"📅 {get_now_wib()}\n"
        f"\n"
        f"Selamat datang di *{config.SHOP_NAME}*.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📊 STATISTIK AKUN\n"
        f"👤 Username : {username}\n"
        f"🆔 ID : {user.id}\n"
        f"🛒 Total Order : {user_orders} transaksi\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📊 STATISTIK BOT\n"
        f"✅ Akun Terjual : {sold}\n"
        f"💰 Harga : Rp {format_rupiah(config.HARGA_PER_AKUN)}/akun\n"
        f"📦 Stok Akun : {stock}\n"
        f"👥 Total User : {total_users}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"Mulai dari mana?\n"
        f"🛒 Beli akun → Daftar Produk\n"
        f"📋 Cek transaksi → Riwayat Order"
    )


def build_products_text() -> str:
    products = db.get_active_products()
    if not products:
        return "*🛍️ DAFTAR PRODUK*\n\nBelum ada produk tersedia."

    lines = ["*🛍️ DAFTAR PRODUK*\n"]
    for i, p in enumerate(products, 1):
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "Unlimited"
        duration = f"\n⏰ Durasi: {p['duration']}" if p.get("duration") else ""
        desc = f"\n{p['description']}" if p.get("description") else ""

        lines.append(
            f"*{i}. {p['name']}* {'🔥' if i == 1 else ''}\n"
            f"{desc}{duration}\n"
            f"💰 Harga: *Rp {format_rupiah(p['price'])}*\n"
            f"📦 Stok: *{stock}* {'Akun' if p['stock_type'] == 'limited' else ''}\n"
        )

    lines.append("Pilih produk untuk memesan:")
    return "\n".join(lines)


def get_main_menu_keyboard(user_id: int = 0):
    rows = [
        [InlineKeyboardButton("🛍️ Daftar Produk", callback_data="menu:produk")],
        [
            InlineKeyboardButton("📦 Cek Stok", callback_data="menu:stok"),
            InlineKeyboardButton("📋 Riwayat Order", callback_data="menu:orders"),
        ],
        [
            InlineKeyboardButton("❓ Bantuan", callback_data="menu:help"),
        ],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stock", cmd_stock))
    app.add_handler(CommandHandler("produk", cmd_produk))
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
    buttons.append([InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
    ])

    text = (
        "*❓ Bantuan*\n\n"
        "*Cara Beli:*\n"
        "1. Klik *🛍️ Daftar Produk*\n"
        "2. Pilih produk\n"
        "3. Pilih jumlah\n"
        "4. Konfirmasi & bayar via QRIS\n"
        "5. Akun otomatis dikirim\n\n"
        "*Commands:*\n"
        "/start - 🏠 Menu utama\n"
        "/produk - 🛍️ Lihat produk\n"
        "/beli - 🛒 Beli akun\n"
        "/stock - 📦 Cek stok\n"
        "/myorders - 📋 Riwayat order\n"
        "/cancel - ❌ Batalkan proses"
    )

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    stock = db.get_stock_count()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Daftar Produk", callback_data="menu:produk")],
        [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
    ])

    await message.reply_text(
        f"*📦 Info Stok*\n\n"
        f"📦 Stok tersedia: *{stock}* akun\n"
        f"💰 Harga: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
        f"💵 Total nilai: *Rp {format_rupiah(config.HARGA_PER_AKUN * stock)}*",
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
        buttons.append([InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "stok":
        stock = db.get_stock_count()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Daftar Produk", callback_data="menu:produk")],
            [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
        ])
        text = (
            f"*📦 Info Stok*\n\n"
            f"📦 Stok tersedia: *{stock}* akun\n"
            f"💰 Harga: *Rp {config.HARGA_PER_AKUN:,}/akun*\n"
            f"💵 Total nilai: *Rp {format_rupiah(config.HARGA_PER_AKUN * stock)}*"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif action == "orders":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
        ])
        try:
            user_id = update.effective_user.id
            orders = db.get_user_orders(user_id)

            if not orders:
                await query.edit_message_text(
                    "Belum ada orderan. Yuk beli sekarang! 🛒",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛍️ Daftar Produk", callback_data="menu:produk")],
                        [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
                    ]),
                )
                return

            _STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦"}
            recent = orders[:10]
            lines = ["*📋 Riwayat Order*\n"]

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
            [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
        ])
        await query.edit_message_text(
            "*⚙️ Admin Panel*\n\n"
            "📦 /products - Lihat produk\n"
            "➕ /addproduct <nama> <harga> - Tambah produk\n"
            "✏️ /editproduct <id> <field>=<value> - Edit produk\n"
            "🗑️ /delproduct <id> - Hapus produk\n"
            "📋 /orders - Lihat order\n"
            "📊 /stockinfo - Info stok\n"
            "💰 /setprice <harga> - Ubah harga\n"
            "📥 /addstock - Tambah stok\n"
            "📣 /broadcast <pesan> - Kirim pesan\n"
            "👤 /addadmin <id> - Tambah admin\n"
            "👤 /removeadmin <id> - Hapus admin\n"
            "👥 /adminlist - Lihat daftar admin",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    elif action == "help":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu:start")],
        ])
        text = (
            "*❓ Bantuan*\n\n"
            "*Cara Beli:*\n"
            "1. Klik *🛍️ Daftar Produk*\n"
            "2. Pilih produk\n"
            "3. Pilih jumlah\n"
            "4. Konfirmasi & bayar via QRIS\n"
            "5. Akun otomatis dikirim\n\n"
            "*Commands:*\n"
            "/start - 🏠 Menu utama\n"
            "/produk - 🛍️ Lihat produk\n"
            "/beli - 🛒 Beli akun\n"
            "/stock - 📦 Cek stok\n"
            "/myorders - 📋 Riwayat order\n"
            "/cancel - ❌ Batalkan proses"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
