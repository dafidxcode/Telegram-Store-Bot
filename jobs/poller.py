"""Background job: poll KlikQRIS status for all pending orders.

When status changes to 'paid':
  1. Update order status
  2. Fetch stock from DB based on quantity
  3. Create .txt file with purchased accounts
  4. Send .txt file to user
  5. Notify admin

When status is 'expired'/'failed':
  1. Delete QRIS image from chat
  2. Update order status
  3. Release stock back
  4. Redirect user to main menu
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
        [InlineKeyboardButton("🛍️ Product List", callback_data="menu:produk")],
        [
            InlineKeyboardButton("📦 Check Stock", callback_data="menu:stok"),
            InlineKeyboardButton("📋 Order History", callback_data="menu:orders"),
        ],
        [InlineKeyboardButton("❓ Help", callback_data="menu:help")],
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
        logger.exception("Failed to fetch pending orders: %s", e)
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
            logger.warning("Check status %s failed: %s", order_id, e)
            continue
        except Exception as e:
            logger.exception("Unexpected error checking %s: %s", order_id, e)
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
                txt_file.name = f"accounts_{order_id}.txt"

                caption = (
                    f"✅ PAYMENT SUCCESSFUL!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 Order: #{order_id}\n"
                    f"🔢 Quantity: {quantity} accounts\n"
                    f"💰 Total: Rp {format_rupiah(order['total'])}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📁 Your account file is attached.\n"
                    f"Keep it safe! 🔐"
                )

                try:
                    await bot.send_document(
                        chat_id=user_id,
                        document=txt_file,
                        caption=caption,
                    )
                except Exception as e:
                    logger.warning("Failed to send file to user %s: %s", user_id, e)

                try:
                    for admin_id in config.ADMIN_IDS:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"✅ Order *#{order_id}* paid & delivered!\n"
                                f"User: @{order.get('username', 'N/A')}\n"
                                f"Quantity: {quantity} accounts\n"
                                f"Status: Delivered"
                            ),
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.warning("Failed to notify admin: %s", e)
            else:
                logger.warning("Order %s paid but stock insufficient!", order_id)
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"Payment successful for Order *#{order_id}*!\n\n"
                            f"However, there are not enough accounts in stock. "
                            f"Admin will process this manually shortly."
                        ),
                        parse_mode="Markdown",
                    )
                    for admin_id in config.ADMIN_IDS:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"⚠️ WARNING: Order *#{order_id}* paid but OUT OF STOCK!\n"
                                f"User: @{order.get('username', 'N/A')}\n"
                                f"Quantity: {quantity} accounts\n"
                                f"Please process manually!"
                            ),
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.warning("Failed to notify: %s", e)

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
                    logger.warning("Failed to delete QRIS message %s: %s", qris_msg_id, e)

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"❌ Order *#{order_id}* has expired/been cancelled\n"
                        f"(status: {payment_status})\n\n"
                        f"Create a new order below 👇"
                    ),
                    parse_mode="Markdown",
                    reply_markup=_get_main_menu_keyboard(user_id),
                )
            except Exception as e:
                logger.warning("Failed to notify user %s: %s", user_id, e)
