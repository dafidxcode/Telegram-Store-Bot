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
from handlers.start import build_home_text, get_main_menu_keyboard, t, format_rupiah, escape_md, _safe_edit_or_send

logger = logging.getLogger(__name__)

POLL_INTERVAL = 15


async def process_paid_order(bot, order_id: str) -> bool:
    """Process paid order: update status, take stock or handle preorder, deliver files, notify user, admin, channel, and apply referral commission."""
    order = db.get_order(order_id)
    if not order:
        return False
    if order.get("status") == "paid":
        return True

    db.update_order_status(order_id, "paid")
    logger.info("Order %s marked PAID", order_id)

    order = db.get_order(order_id)
    if not order:
        return False

    quantity = order["quantity"]
    user_id = order["user_id"]
    product_id = order.get("product_id", 1)
    user_lang = db.get_user_lang(user_id)

    product = db.get_product(product_id)
    product_name = product["name"] if product else "N/A"
    stock_type = product.get("stock_type", "limited") if product else "limited"

    if stock_type == "preorder":
        buyer_msg = t("preorder_paid_buyer", user_lang,
                      order_id=order_id,
                      product_name=escape_md(product_name),
                      qty=quantity,
                      total=format_rupiah(order["total"]))
        try:
            await bot.send_message(
                chat_id=user_id,
                text=buyer_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard(user_id, user_lang),
            )
        except Exception as e:
            logger.warning("Failed to send preorder buyer notice %s: %s", order_id, e)

        qris_msg_id = order.get("qris_message_id")
        if qris_msg_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=qris_msg_id)
            except Exception:
                pass

        try:
            raw_user_name = f"@{order.get('username')}" if order.get("username") else str(user_id)
            user_name = escape_md(raw_user_name)
            for admin_id in config.ADMIN_IDS:
                admin_text = (
                    f"⏳ *PESANAN PRE-ORDER BARU!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 Pesanan: *#{order_id}*\n"
                    f"👤 Pengguna: {user_name} (ID: `{user_id}`)\n"
                    f"📦 Produk: *{escape_md(product_name)}*\n"
                    f"🔢 Jumlah: {quantity} akun\n"
                    f"💰 Total: *Rp {format_rupiah(order['total'])}*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💡 Klik tombol di bawah ini untuk memproses & mengirimkan data produk ke pengguna."
                )
                admin_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"📦 Proses #{order_id}", callback_data=f"admin:preorder_process:{order_id}")],
                ])
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=admin_keyboard,
                )
        except Exception as e:
            logger.warning("Failed to send preorder admin notif: %s", e)
        return True

    stock_items = db.take_stock(order_id, quantity, product_id=product_id)

    if stock_items:
        instruction_text = (product.get("instruction") or "").strip() if product else ""
        txt_content = ""
        if instruction_text:
            txt_content += f"==================================================\n"
            txt_content += f"INSTRUKSI PENGGUNAAN ({product_name}):\n"
            txt_content += f"{instruction_text}\n"
            txt_content += f"==================================================\n\n"

        account_lines = []
        for item in stock_items:
            em = item.get("email", "")
            pw = item.get("password", "")
            bal = item.get("balance", "")
            if pw and bal:
                txt_content += f"{em}:{pw}:{bal}\n"
                account_lines.append(f"{em}:{pw}:{bal}")
            elif pw:
                txt_content += f"{em}:{pw}\n"
                account_lines.append(f"{em}:{pw}")
            else:
                txt_content += f"{em}\n"
                account_lines.append(em)

        db.save_purchase_detail(
            order_id=order_id,
            user_id=user_id,
            product_name=product_name,
            accounts_delivered="\n".join(account_lines),
        )

        txt_bytes = txt_content.encode("utf-8")
        txt_file = io.BytesIO(txt_bytes)
        txt_file.name = f"accounts_{order_id}.txt"

        caption = (
            f"{t('payment_success', user_lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('order_label', user_lang)}: #{order_id}\n"
            f"{t('product_label', user_lang)}: {escape_md(product_name)}\n"
            f"{t('quantity_label_short', user_lang)}: {quantity} {t('accounts', user_lang)}\n"
            f"{t('total_label', user_lang)}: Rp {format_rupiah(order['total'])}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

        if instruction_text:
            caption += f"\n📌 *Instruksi Penggunaan:*\n{escape_md(instruction_text)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

        caption += f"\n{t('file_attached', user_lang)}"

        try:
            await bot.send_document(
                chat_id=user_id,
                document=txt_file,
                caption=caption,
                reply_markup=get_main_menu_keyboard(user_id, user_lang),
            )
        except Exception as e:
            logger.warning("Failed to send file to user %s: %s", user_id, e)

        qris_msg_id = order.get("qris_message_id")
        if qris_msg_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=qris_msg_id)
            except Exception:
                pass

        try:
            from notifier import send_channel_purchase_notif
            await send_channel_purchase_notif(bot, order, product_name)
        except Exception as e:
            logger.warning("Failed to send channel purchase notif: %s", e)

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

        try:
            buyer_user = db._conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if buyer_user and buyer_user["referred_by"]:
                referrer_id = buyer_user["referred_by"]
                if not db.has_commission_for_order(order_id):
                    commission_pct = db.get_commission_percent()
                    order_amount = order.get("total", 0)
                    commission_amount = int(order_amount * commission_pct / 100)
                    if commission_amount > 0:
                        db.add_commission(referrer_id, user_id, order_id, order_amount, commission_pct, commission_amount)
                        try:
                            referrer_lang = db.get_user_lang(referrer_id)
                            await bot.send_message(
                                chat_id=referrer_id,
                                text=t("commission_notif", referrer_lang,
                                    amount=format_rupiah(commission_amount),
                                    name=order.get("first_name") or order.get("username") or str(user_id),
                                    order_id=order_id),
                                parse_mode="Markdown",
                            )
                        except Exception:
                            pass
                        logger.info("Commission Rp %d applied for referrer %s from order %s", commission_amount, referrer_id, order_id)
        except Exception as exc:
            logger.exception("Failed to apply commission for order %s: %s", order_id, exc)

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

    return True


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
            logger.debug("Poller check %s: raw=%s parsed=%s keys=%s", order_id, raw_status, payment_status, list(data.keys()))
        except klikqris.KlikQRISError as e:
            logger.warning("Check status %s failed: %s", order_id, e)
            continue
        except Exception as e:
            logger.exception("Unexpected error checking %s: %s", order_id, e)
            continue

        if payment_status == "SUCCESS":
            await process_paid_order(bot, order_id)

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
