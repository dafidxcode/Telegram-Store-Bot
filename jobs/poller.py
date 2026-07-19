"""Background job: poll KlikQRIS status untuk semua order pending.

Saat status berubah jadi 'paid':
  1. Update order status
  2. Ambil stock dari DB sesuai quantity
  3. Buat file .txt berisi akun yang dibeli
  4. Kirim file .txt ke user
  5. Notifikasi admin

Saat status 'expired'/'failed':
  1. Hapus QRIS image dari chat
  2. Update order status
  3. Release stock kembali
  4. Kirim user ke menu utama
"""

from __future__ import annotations

import io
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config
import db
from payments import klikqris

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _get_main_menu_keyboard(user_id: int = 0):
    rows = [
        [InlineKeyboardButton("🛍️ Daftar Produk", callback_data="menu:produk")],
        [
            InlineKeyboardButton("📦 Cek Stok", callback_data="menu:stok"),
            InlineKeyboardButton("📋 Riwayat Order", callback_data="menu:orders"),
        ],
        [InlineKeyboardButton("❓ Bantuan", callback_data="menu:help")],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


async def check_payments(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not klikqris.is_active():
        return

    try:
        orders = db.get_pending_qris_orders()
    except Exception as e:
        logger.exception("Gagal ambil pending orders: %s", e)
        return

    if not orders:
        return

    klik = klikqris.get()
    bot = context.bot

    for order in orders:
        order_id = order["id"]
        try:
            res = await klik.check_status(order_id)
            payment_status = (res.get("data") or {}).get("payment_status", "pending")
        except klikqris.KlikQRISError as e:
            logger.warning("Cek status %s gagal: %s", order_id, e)
            continue
        except Exception as e:
            logger.exception("Unexpected error cek %s: %s", order_id, e)
            continue

        if payment_status == "paid":
            db.update_order_status(order_id, "paid")
            logger.info("Order %s marked PAID via poller", order_id)

            quantity = order["quantity"]
            user_id = order["user_id"]

            stock_items = db.take_stock(order_id, quantity)

            if stock_items:
                txt_content = "\n"
                for item in stock_items:
                    bal = item.get("balance", "")
                    if bal:
                        txt_content += f"{item['email']}:{item['password']}:{bal}\n"
                    else:
                        txt_content += f"{item['email']}:{item['password']}\n"

                txt_bytes = txt_content.encode("utf-8")
                txt_file = io.BytesIO(txt_bytes)
                txt_file.name = f"akun_{order_id}.txt"

                caption = (
                    f"✅ PEMBAYARAN BERHASIL!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 Order: #{order_id}\n"
                    f"🔢 Jumlah: {quantity} akun\n"
                    f"💰 Total: Rp {format_rupiah(order['total'])}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📁 File akun kamu ada di lampiran.\n"
                    f"Simpan baik-baik! 🔐"
                )

                try:
                    await bot.send_document(
                        chat_id=user_id,
                        document=txt_file,
                        caption=caption,
                    )
                except Exception as e:
                    logger.warning("Gagal kirim file ke user %s: %s", user_id, e)

                try:
                    for admin_id in config.ADMIN_IDS:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"✅ Order *#{order_id}* dibayar & dikirim!\n"
                                f"User: @{order.get('username', 'N/A')}\n"
                                f"Jumlah: {quantity} akun\n"
                                f"Status: Dikirim"
                            ),
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.warning("Gagal notif admin: %s", e)
            else:
                logger.warning("Order %s paid tapi stok tidak cukup!", order_id)
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"Pembayaran berhasil untuk Order *#{order_id}*!\n\n"
                            f"Namun stok akun tidak cukup. "
                            f"Admin akan segera memproses manual."
                        ),
                        parse_mode="Markdown",
                    )
                    for admin_id in config.ADMIN_IDS:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"⚠️ WARNING: Order *#{order_id}* dibayar tapi STOK KOSONG!\n"
                                f"User: @{order.get('username', 'N/A')}\n"
                                f"Jumlah: {quantity} akun\n"
                                f"Harap proses manual!"
                            ),
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.warning("Gagal notif: %s", e)

        elif payment_status in ("expired", "failed", "cancelled"):
            db.update_order_status(order_id, "cancelled")
            released = db.release_stock(order_id)
            logger.info("Order %s CANCELLED via poller (%s), released %d stock", order_id, payment_status, released)

            user_id = order["user_id"]
            qris_msg_id = order.get("qris_message_id")

            if qris_msg_id:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=qris_msg_id)
                    logger.info("Deleted QRIS message %s for order %s", qris_msg_id, order_id)
                except Exception as e:
                    logger.warning("Gagal hapus QRIS message %s: %s", qris_msg_id, e)

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"❌ Order *#{order_id}* kadaluarsa/dibatalkan\n"
                        f"(status: {payment_status})\n\n"
                        f"Buat order baru di bawah 👇"
                    ),
                    parse_mode="Markdown",
                    reply_markup=_get_main_menu_keyboard(user_id),
                )
            except Exception as e:
                logger.warning("Gagal notif user %s: %s", user_id, e)
