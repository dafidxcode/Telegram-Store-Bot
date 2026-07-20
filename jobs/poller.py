"""Background job: poll KlikQRIS status for all pending orders.

When status changes to 'SUCCESS' (paid):
  1. Update order status
  2. Fetch stock from DB based on quantity & product_id
  3. Create .txt file with purchased accounts
  4. Send .txt file to user (in user's language)
  5. Notify admin

When status is 'EXPIRED'/'FAILED':
  1. Delete QRIS image from chat
  2. Update order status to cancelled
  3. Release stock back
  4. Redirect user to main menu

Also cleans up locally-expired orders.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import db
from payments import klikqris
from handlers.start import build_home_text, get_main_menu_keyboard, t, format_rupiah, escape_md

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10


async def _cleanup_expired_orders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete orders that have passed their expires_at locally (no API needed)."""
    try:
        expired = db.get_expired_pending_orders()
    except Exception as e:
        logger.exception("Failed to fetch expired orders: %s", e)
        return

    for order in expired:
        order_id = order["id"]
        user_id = order["user_id"]

        db.update_order_status(order_id, "cancelled")
        released = db.release_stock(order_id)

        qris_msg_id = order.get("qris_message_id")
        if qris_msg_id:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=qris_msg_id)
            except Exception:
                pass

        try:
            user = await context.bot.get_chat(user_id)
            lang = db.get_user_lang(user_id)
            text = build_home_text(user, lang)
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard(user_id, lang),
            )
        except Exception as e:
            logger.warning("Failed to notify user %s about local expiry: %s", user_id, e)

        logger.info("Order %s locally EXPIRED and cleaned up, released %d stock", order_id, released)


async def check_payments(context: ContextTypes.DEFAULT_TYPE) -> None:
    # 1) Always clean up locally-expired orders first
    await _cleanup_expired_orders(context)

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
        product_id = order.get("product_id", 1)
        try:
            res = await klik.check_status(order_id)
            data = res.get("data") or {}
            raw_status = (
                data.get("payment_status")
                or data.get("status")
                or data.get("payment_status_raw")
                or "PENDING"
            )
            payment_status = str(raw_status).strip().upper()
            logger.info("Poller check %s: raw=%s parsed=%s keys=%s", order_id, raw_status, payment_status, list(data.keys()))
        except klikqris.KlikQRISError as e:
            logger.warning("Check status %s failed: %s", order_id, e)
            continue
        except Exception as e:
            logger.exception("Unexpected error checking %s: %s", order_id, e)
            continue

        if payment_status == "SUCCESS":
            db.update_order_status(order_id, "paid")
            logger.info("Order %s marked PAID via poller", order_id)

            quantity = order["quantity"]
            user_id = order["user_id"]
            user_lang = db.get_user_lang(user_id)

            product = db.get_product(product_id)
            product_name = product["name"] if product else "N/A"

            stock_items = db.take_stock(order_id, quantity, product_id=product_id)

            if stock_items:
                txt_content = ""
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
                    f"{t('payment_success', user_lang)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 {t('order_label', user_lang)}: #{order_id}\n"
                    f"📦 {t('product_label', user_lang)}: {escape_md(product_name)}\n"
                    f"🔢 {t('quantity_label_short', user_lang)}: {quantity} {t('accounts', user_lang)}\n"
                    f"💰 {t('total_label', user_lang)}: Rp {format_rupiah(order['total'])}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{t('file_attached', user_lang)}"
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
                        admin_lang = db.get_user_lang(admin_id)
                        await bot.send_message(
                            chat_id=admin_id,
                            text=t("admin_notif_paid", admin_lang,
                                   order_id=order_id,
                                   username=order.get("username", "N/A"),
                                   product_name=escape_md(product_name),
                                   qty=quantity),
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.warning("Failed to notify admin: %s", e)
            else:
                logger.warning("Order %s paid but stock insufficient for product %s!", order_id, product_id)
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=t("stock_insufficient", user_lang, order_id=order_id),
                        parse_mode="Markdown",
                    )
                    for admin_id in config.ADMIN_IDS:
                        admin_lang = db.get_user_lang(admin_id)
                        await bot.send_message(
                            chat_id=admin_id,
                            text=t("admin_stock_warning", admin_lang,
                                   order_id=order_id,
                                   username=order.get("username", "N/A"),
                                   product_name=escape_md(product_name),
                                   qty=quantity),
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.warning("Failed to notify: %s", e)

        elif payment_status in ("EXPIRED", "FAILED", "CANCELLED"):
            db.update_order_status(order_id, "cancelled")
            released = db.release_stock(order_id)
            logger.info("Order %s CANCELLED via poller (%s), released %d stock", order_id, payment_status, released)

            user_id = order["user_id"]
            qris_msg_id = order.get("qris_message_id")
            user_lang = db.get_user_lang(user_id)

            if qris_msg_id:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=qris_msg_id)
                    logger.info("Deleted QRIS message %s for order %s", qris_msg_id, order_id)
                except Exception as e:
                    logger.warning("Failed to delete QRIS message %s: %s", qris_msg_id, e)

            try:
                user = await context.bot.get_chat(user_id)
                text = build_home_text(user, user_lang)
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_menu_keyboard(user_id, user_lang),
                )
            except Exception as e:
                logger.warning("Failed to notify user %s: %s", user_id, e)
