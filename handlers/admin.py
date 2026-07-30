"""Admin command handlers — all text translated per user language."""

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
from handlers.start import btn_home, escape_md, get_lang, t, format_rupiah, get_num_emoji

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


async def _deny_non_admin(update: Update, lang="en") -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(t("admin_access_denied", lang))


def _admin_back_keyboard(lang="id", back_data="menu:admin"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_back", lang), callback_data=back_data)],
        [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
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

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    product_id = db.add_product(name=name, description=description, price=price)
    await message.reply_text(
        f"{t('admin_product_added', lang)}\n\n"
        f"{t('admin_id', lang)}: `{product_id}`\n"
        f"{t('admin_name', lang)}: *{name}*\n"
        f"{t('admin_price', lang)}: *Rp {format_rupiah(price)}*\n"
        f"{t('admin_description', lang)}: {description or '-'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
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
    if not _is_admin(update):
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    admin_state = context.user_data.get("admin_state")

    if admin_state and admin_state.startswith("preorder_fulfill:"):
        message = update.message
        if message is None or not message.text:
            return
        delivered_content = message.text.strip()
        order_id = admin_state.split(":")[1]
        context.user_data.pop("admin_state", None)

        order = db.get_order(order_id)
        if not order:
            await message.reply_text("❌ Pesanan tidak ditemukan.", reply_markup=_admin_back_keyboard(lang))
            return

        product = db.get_product(order.get("product_id", 1))
        product_name = product["name"] if product else "N/A"
        u_id = order["user_id"]
        user_lang = db.get_user_lang(u_id)

        db.save_purchase_detail(
            order_id=order_id,
            user_id=u_id,
            product_name=product_name,
            accounts_delivered=delivered_content,
        )
        db.update_order_status(order_id, "delivered")

        buyer_text = (
            f"🎉 *PESANAN PRE-ORDER SELESAI!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Pesanan: `#{order_id}`\n"
            f"📦 Produk: *{escape_md(product_name)}*\n"
            f"🔢 Jumlah: {order['quantity']} akun\n"
            f"💰 Total: *Rp {format_rupiah(order['total'])}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔐 *Data Produk / Akun Anda:*\n"
            f"```\n{delivered_content}\n```\n\n"
            f"Terima kasih telah berbelanja! 🙏"
        )
        try:
            from handlers.start import get_main_menu_keyboard
            await context.bot.send_message(
                chat_id=u_id,
                text=buyer_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard(u_id, user_lang),
            )
        except Exception as e:
            logger.warning("Failed to send delivered preorder to user %s: %s", u_id, e)

        await message.reply_text(
            f"✅ *Produk Pre-Order #{order_id} berhasil dikirimkan ke pengguna!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "addproduct_name":
        message = update.message
        if message is None or not message.text:
            return
        name = message.text.strip()
        if not name:
            await message.reply_text(t("admin_name_empty", lang))
            return
        context.user_data["admin_state"] = "addproduct_price"
        context.user_data["addproduct_name"] = name
        await message.reply_text(
            f"{t('admin_product_name', lang)}: *{name}*\n\n{t('admin_send_price', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "addproduct_price":
        message = update.message
        if message is None or not message.text:
            return
        try:
            price = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text(t("admin_price_number", lang))
            return
        if price <= 0:
            await message.reply_text(t("admin_price_positive", lang))
            return
        context.user_data["admin_state"] = "addproduct_desc"
        context.user_data["addproduct_price"] = price
        await message.reply_text(
            f"{t('admin_price', lang)}: *Rp {format_rupiah(price)}*\n\n{t('admin_send_desc', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
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
            await message.reply_text(t("admin_something_wrong", lang), reply_markup=_admin_back_keyboard(lang))
            return

        product_id = db.add_product(name=name, description=desc, price=price)
        await message.reply_text(
            f"{t('admin_product_added', lang)}\n\n"
            f"{t('admin_id', lang)}: `{product_id}`\n"
            f"{t('admin_name', lang)}: *{escape_md(name)}*\n"
            f"{t('admin_price', lang)}: *Rp {format_rupiah(price)}*\n"
            f"{t('admin_description', lang)}: {desc or '-'}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "setprice_value":
        message = update.message
        if message is None or not message.text:
            return
        try:
            new_price = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text(t("admin_price_number", lang))
            return
        if new_price <= 0:
            await message.reply_text(t("admin_price_positive", lang))
            return
        product_id = context.user_data.pop("setprice_product_id", None)
        context.user_data.pop("admin_state", None)
        if product_id:
            db.update_product(product_id, price=new_price)
            product = db.get_product(product_id)
            product_name = escape_md(product["name"]) if product else "Unknown"
            await message.reply_text(
                f"{t('admin_name', lang)}: *{product_name}*\n"
                f"{t('admin_new_price', lang)}: *Rp {format_rupiah(new_price)}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(lang),
            )
        else:
            await message.reply_text(t("admin_something_wrong", lang), reply_markup=_admin_back_keyboard(lang))
        return

    if admin_state == "broadcast_msg":
        message = update.message
        if message is None:
            return

        context.user_data.pop("admin_state", None)

        try:
            user_ids = db.get_all_user_ids()
        except Exception:
            await message.reply_text(t("admin_try_again", lang), reply_markup=_admin_back_keyboard(lang))
            return

        success = 0
        failed = 0

        if message.photo:
            photo = message.photo[-1]
            broadcast_caption = (message.caption or "").strip()
            for uid in user_ids:
                try:
                    await context.bot.send_photo(
                        chat_id=uid,
                        photo=photo.file_id,
                        caption=broadcast_caption or None,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    success += 1
                except Exception:
                    failed += 1
        elif message.text:
            broadcast_text = message.text.strip()
            for uid in user_ids:
                try:
                    await context.bot.send_message(chat_id=uid, text=broadcast_text, parse_mode=ParseMode.MARKDOWN)
                    success += 1
                except Exception:
                    failed += 1
        else:
            await message.reply_text(t("admin_try_again", lang), reply_markup=_admin_back_keyboard(lang))
            return

        await message.reply_text(
            f"{t('admin_broadcast_done', lang)}\n\n"
            f"{t('admin_sent', lang)}: *{success}* {t('users', lang)}\n"
            f"{t('admin_failed', lang)}: *{failed}* {t('users', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "addadmin_id":
        message = update.message
        if message is None or not message.text:
            return
        try:
            new_admin_id = int(message.text.strip())
        except ValueError:
            await message.reply_text(t("admin_id_number", lang))
            return
        context.user_data.pop("admin_state", None)
        if new_admin_id in config.ADMIN_IDS:
            await message.reply_text(
                t("admin_already_admin", lang, id=new_admin_id),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(lang),
            )
            return
        config.ADMIN_IDS.add(new_admin_id)
        await message.reply_text(
            f"{t('admin_added', lang)}\n\n"
            f"{t('admin_id', lang)}: `{new_admin_id}`\n"
            f"{t('admin_total_admins', lang)}: *{len(config.ADMIN_IDS)}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "search_order":
        message = update.message
        if message is None or not message.text:
            return
        query_str = message.text.strip()
        context.user_data.pop("admin_state", None)

        orders = db.search_orders(query_str)
        if not orders:
            await message.reply_text(
                f"🔍 Hasil Pencarian: *{escape_md(query_str)}*\n\n❌ Pesanan tidak ditemukan.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(lang),
            )
            return

        lines = [f"🔍 Hasil Pencarian untuk *{escape_md(query_str)}* ({len(orders)} ditemukan):\n"]
        buttons = []
        for o in orders[:5]:
            username = o.get("username") or "no_user"
            status = o.get("status", "pending")
            emoji = _STATUS_EMOJI.get(status, "⏳")
            oid = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"

            lines.append(
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Pesanan: `{oid}`\n"
                f"👤 Pembeli: @{username} (ID: `{o['user_id']}`)\n"
                f"📦 Produk: *{product_name}*\n"
                f"🔢 Jumlah: {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
                f"Status: {emoji} *{status.upper()}*\n"
                f"📅 Waktu: {o['created_at']}"
            )
            if status == "pending":
                buttons.append([InlineKeyboardButton(f"✅ Approve #{oid}", callback_data=f"admin:apv:{oid}")])

        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])

        await message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    # Handle admin text input for user search
    if admin_state == "user_search":
        message = update.message
        if message is None or not message.text:
            return
        query_str = message.text.strip()
        context.user_data.pop("admin_state", None)

        users = db.search_users(query_str)
        if not users:
            await message.reply_text(
                f"🔍 User tidak ditemukan untuk: *{escape_md(query_str)}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(lang),
            )
            return

        lines = [f"🔍 Hasil Pencarian User ({len(users)} ditemukan):\n"]
        buttons = []
        for u in users[:10]:
            name = f"@{u['username']}" if u.get("username") else u.get("first_name", str(u["user_id"]))
            ban_icon = "🚫" if u.get("is_banned") else ""
            lines.append(f"{ban_icon} {name} | {u.get('total_orders', 0)} orders | Rp {format_rupiah(u.get('total_spent', 0))}")
            buttons.append([InlineKeyboardButton(
                f"👤 {name}",
                callback_data=f"admin:userdetail:{u['user_id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="admin:users")])
        await message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    # Commission settings
    if admin_state == "setcommission":
        message = update.message
        if message is None or not message.text:
            return
        try:
            pct = int(message.text.strip())
        except ValueError:
            await message.reply_text("Harus angka. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            return
        if pct < 1 or pct > 50:
            await message.reply_text("Persentase harus antara 1-50. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            return
        context.user_data.pop("admin_state", None)
        db.set_setting("commission_percent", str(pct))
        await message.reply_text(
            t("admin_commission_updated", lang, percent=pct),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang, back_data="admin:commission"),
        )
        return

    if admin_state == "setminwithdraw":
        message = update.message
        if message is None or not message.text:
            return
        try:
            amount = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text("Harus angka. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            return
        if amount < 10000:
            await message.reply_text("Minimal Rp 10.000. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            return
        context.user_data.pop("admin_state", None)
        db.set_setting("min_withdrawal", str(amount))
        await message.reply_text(
            t("admin_min_withdraw_updated", lang, amount=format_rupiah(amount)),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang, back_data="admin:commission"),
        )
        return

    if admin_state == "editproduct_name":
        message = update.message
        if message is None or not message.text:
            return
        new_name = message.text.strip()
        pid = context.user_data.pop("editproduct_id", None)
        context.user_data.pop("admin_state", None)
        if pid and new_name:
            db.update_product(pid, name=new_name)
            await message.reply_text(
                f"✅ Nama produk berhasil diubah menjadi: *{escape_md(new_name)}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Kembali ke Edit Produk", callback_data=f"admin:edetail:{pid}")],
                    [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
                ]),
            )
        return

    if admin_state == "editproduct_desc":
        message = update.message
        if message is None or not message.text:
            return
        new_desc = message.text.strip()
        if new_desc == "-":
            new_desc = ""
        pid = context.user_data.pop("editproduct_id", None)
        context.user_data.pop("admin_state", None)
        if pid is not None:
            db.update_product(pid, description=new_desc)
            await message.reply_text(
                f"✅ Deskripsi produk berhasil diubah!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Kembali ke Edit Produk", callback_data=f"admin:edetail:{pid}")],
                    [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
                ]),
            )
        return

    if admin_state == "editproduct_price":
        message = update.message
        if message is None or not message.text:
            return
        try:
            new_price = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text(t("admin_price_number", lang))
            return
        if new_price <= 0:
            await message.reply_text(t("admin_price_positive", lang))
            return
        pid = context.user_data.pop("editproduct_id", None)
        context.user_data.pop("admin_state", None)
        if pid is not None:
            db.update_product(pid, price=new_price)
            await message.reply_text(
                f"✅ Harga produk berhasil diubah menjadi: *Rp {format_rupiah(new_price)}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Kembali ke Edit Produk", callback_data=f"admin:edetail:{pid}")],
                    [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
                ]),
            )
        return

    if admin_state == "feedback_reply":
        message = update.message
        if message is None or not message.text:
            return
        reply_text = message.text.strip()
        feedback_id = context.user_data.pop("feedback_reply_id", None)
        context.user_data.pop("admin_state", None)
        if feedback_id:
            fb = db.get_all_feedback()
            fb_item = next((f for f in fb if f["id"] == feedback_id), None)
            if fb_item:
                db.reply_feedback(feedback_id, reply_text)
                try:
                    await context.bot.send_message(
                        chat_id=fb_item["user_id"],
                        text=t("feedback_reply_to_user", lang, reply=reply_text),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass
            await message.reply_text(
                t("feedback_reply_sent", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(lang, back_data="admin:feedbacklist"),
            )
        return

    if admin_state == "addvoucher":
        message = update.message
        if message is None or not message.text:
            return
        voucher_data = context.user_data.pop("addvoucher_data", {})
        code = message.text.strip().upper()
        if not code or len(code) < 3:
            await message.reply_text("Kode voucher minimal 3 karakter. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            context.user_data["admin_state"] = "addvoucher"
            return
        existing = db.get_voucher(code)
        if existing:
            await message.reply_text(f"Kode voucher *{code}* sudah ada. Kirim kode lain:", parse_mode=ParseMode.MARKDOWN, reply_markup=_admin_back_keyboard(lang))
            context.user_data["admin_state"] = "addvoucher"
            return
        voucher_data["code"] = code
        context.user_data["admin_state"] = "addvoucher_value"
        context.user_data["addvoucher_data"] = voucher_data
        dtype = voucher_data.get("discount_type", "fixed")
        dtype_label = "Nominal Tetap (Rp)" if dtype == "fixed" else "Persentase (%)"
        await message.reply_text(
            f"Kode: *{code}*\nTipe: *{dtype_label}*\n\nMasukkan nilai diskon:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "addvoucher_value":
        message = update.message
        if message is None or not message.text:
            return
        try:
            value = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text("Nilai harus angka. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            return
        voucher_data = context.user_data.pop("addvoucher_data", {})
        voucher_data["discount_value"] = value
        context.user_data["admin_state"] = "addvoucher_min"
        context.user_data["addvoucher_data"] = voucher_data
        await message.reply_text(
            f"Nilai diskon: *{value}*{'%' if voucher_data.get('discount_type') == 'percent' else ''}\n\nMasukkan minimal pembelian (0 = tanpa minimal):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "addvoucher_min":
        message = update.message
        if message is None or not message.text:
            return
        try:
            min_purchase = int(message.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await message.reply_text("Harus angka. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            return
        voucher_data = context.user_data.pop("addvoucher_data", {})
        voucher_data["min_purchase"] = min_purchase
        context.user_data["admin_state"] = "addvoucher_max"
        context.user_data["addvoucher_data"] = voucher_data
        await message.reply_text(
            "Masukkan maksimal penggunaan (0 = unlimited):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    if admin_state == "addvoucher_max":
        message = update.message
        if message is None or not message.text:
            return
        try:
            max_uses = int(message.text.strip())
        except ValueError:
            await message.reply_text("Harus angka. Kirim ulang:", reply_markup=_admin_back_keyboard(lang))
            return
        voucher_data = context.user_data.pop("addvoucher_data", {})
        code = voucher_data["code"]
        db.create_voucher(
            code=code,
            discount_type=voucher_data.get("discount_type", "fixed"),
            discount_value=voucher_data["discount_value"],
            min_purchase=voucher_data.get("min_purchase", 0),
            max_uses=max_uses,
        )
        context.user_data.pop("admin_state", None)
        await message.reply_text(
            t("admin_voucher_added", lang, code=code),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang, back_data="admin:vouchers"),
        )
        return

    if admin_state == "user_ban_reason":
        message = update.message
        if message is None or not message.text:
            return
        reason = message.text.strip()
        ban_uid = context.user_data.pop("ban_user_id", None)
        context.user_data.pop("admin_state", None)
        if ban_uid:
            db.ban_user(ban_uid, reason)
            await message.reply_text(
                t("user_banned_success", lang, id=ban_uid),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_admin_back_keyboard(lang, back_data="admin:users"),
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
                f"{t('admin_stock_added', lang, name=product_name)}\n\n"
                f"{t('admin_added_count', lang)}: *{count}* {t('accounts', lang)}\n"
                f"{t('admin_product_stock', lang)}: *{stock}* {t('accounts', lang)}\n\n"
                f"{t('admin_send_more', lang)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{t('admin_add_more', lang)} — {product_name}", callback_data=f"admin:astk:{addstock_pid}")],
                    [InlineKeyboardButton(t("btn_back", lang), callback_data="admin:addstock")],
                    [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
                ]),
            )
        else:
            await message.reply_text(
                f"{t('admin_stock_not_added', lang, name=product_name)}\n\n"
                f"{t('admin_check_format', lang)}\n\n"
                f"{t('admin_current_stock', lang)}: *{stock}* {t('accounts', lang)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{t('admin_try_again', lang)} — {product_name}", callback_data=f"admin:astk:{addstock_pid}")],
                    [InlineKeyboardButton(t("btn_back", lang), callback_data="admin:addstock")],
                    [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
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

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    raw = update.message.text.replace("/addproduct", "").strip() if update.message.text else ""
    if not raw or "|" not in raw:
        await update.message.reply_text(
            f"*{t('admin_add_product', lang)}*\n\n"
            f"{t('cmd_addproduct_usage', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    parts = [p.strip() for p in raw.split("|")]
    name = parts[0]
    if not name:
        await update.message.reply_text(t("admin_name_empty", lang), reply_markup=_admin_back_keyboard(lang))
        return

    try:
        price = int(parts[1])
    except (IndexError, ValueError):
        await update.message.reply_text(
            f"{t('admin_price_number', lang)}\n\n"
            f"Format: `/addproduct ProductName|Price|Description`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    description = parts[2] if len(parts) > 2 else ""

    product_id = db.add_product(name=name, description=description, price=price)
    await update.message.reply_text(
        f"{t('admin_product_added', lang)}\n\n"
        f"{t('admin_id', lang)}: `{product_id}`\n"
        f"{t('admin_name', lang)}: *{name}*\n"
        f"{t('admin_price', lang)}: *Rp {format_rupiah(price)}*\n"
        f"{t('admin_description', lang)}: {description or '-'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_editproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            t('cmd_editproduct_usage', lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text(t("admin_id_number", lang), reply_markup=_admin_back_keyboard(lang))
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            t("admin_not_found", lang, id=product_id),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
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
        await update.message.reply_text(t("admin_no_changes", lang), reply_markup=_admin_back_keyboard(lang))
        return

    db.update_product(product_id, **kwargs)
    updated = db.get_product(product_id)
    active_text = t("admin_active", lang) if updated['is_active'] else t("admin_inactive", lang)
    await update.message.reply_text(
        f"{t('admin_product_updated', lang)}\n\n"
        f"{t('admin_id', lang)}: `{product_id}`\n"
        f"{t('admin_name', lang)}: *{updated['name']}*\n"
        f"{t('admin_price', lang)}: *Rp {format_rupiah(updated['price'])}*\n"
        f"{t('admin_stock', lang)}: {updated['stock_type']} ({updated['stock_count']})\n"
        f"{active_text}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_delproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    args = context.args or []
    if not args:
        await update.message.reply_text(
            t('cmd_delproduct_usage', lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text(t("admin_id_number", lang), reply_markup=_admin_back_keyboard(lang))
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            t("admin_not_found", lang, id=product_id),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    db.delete_product(product_id)
    await update.message.reply_text(
        f"{t('admin_product_deleted', lang)}\n\n"
        f"{t('admin_name', lang)}: *{escape_md(product['name'])}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    products = db.get_all_products()
    if not products:
        await update.message.reply_text(
            f"{t('admin_product_list', lang)}\n\n{t('no_products', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    lines = [f"{t('admin_product_list', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for i, p in enumerate(products, 1):
        if p["stock_type"] == "preorder":
            stock = "⏳ Pre-Order"
        else:
            cnt = db.get_stock_count(p["id"])
            stock = "❌ Habis (0 akun)" if cnt == 0 else f"{cnt} akun"

        status = "✅" if p["is_active"] else "🔴 (Nonaktif)"
        lines.append(
            f"{status} *{get_num_emoji(i)} {escape_md(p['name'])}*\n"
            f"   💰 {t('admin_price', lang)}: *Rp {format_rupiah(p['price'])}*\n"
            f"   📦 {t('admin_stock', lang)}: *{stock}*\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
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

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    products = db.get_active_products()
    if not products:
        await message.reply_text(
            t("admin_no_active_products", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    buttons = []
    for p in products:
        stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        buttons.append([InlineKeyboardButton(
            f"📦 {p['name']} ({t('admin_stock', lang).lstrip('📦 ')}: {stock})",
            callback_data=f"admin:astk:{p['id']}",
        )])
    buttons.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

    await message.reply_text(
        f"{t('admin_add_stock', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_stock_product', lang)}",
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

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    await message.reply_text(
        f"{t('admin_add_stock', lang)}\n\n"
        f"{t('admin_method1', lang)}\n\n"
        f"{t('admin_method2', lang)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return

    message = update.message
    if message is None or message.document is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    doc = message.document
    if doc.mime_type and "text" not in doc.mime_type and not doc.file_name.endswith(".txt"):
        await message.reply_text(t("admin_only_txt", lang), reply_markup=_admin_back_keyboard(lang))
        return

    try:
        file = await doc.get_file()
        content = await file.download_as_bytearray()
        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()
    except Exception as e:
        logger.exception("Failed to download file: %s", e)
        await message.reply_text(t("admin_failed_read", lang), reply_markup=_admin_back_keyboard(lang))
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
            f"{t('admin_stock_file_added', lang)}\n\n"
            f"{t('admin_name', lang)}: *{product_label}*\n"
            f"{t('admin_added_count', lang)}: *{count}* {t('accounts', lang)}\n"
            f"{t('admin_stock', lang)}: *{stock}* {t('accounts', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
    else:
        await message.reply_text(
            t("admin_stock_file_none", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )


async def cmd_stockinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    total_stock = db.get_stock_count()
    pending = len(db.get_pending_qris_orders())
    products = db.get_active_products()

    text = (
        f"{t('admin_stock_info', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('admin_total_ready', lang)}: *{total_stock}* {t('accounts', lang)}\n"
        f"{t('admin_pending_orders', lang)}: *{pending}*\n"
    )
    for i, p in enumerate(products, 1):
        p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        text += f"\n{get_num_emoji(i)} {escape_md(p['name'])}: *{p_stock}* | Rp {format_rupiah(p['price'])}"

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    status_filter = context.args[0] if context.args else None

    try:
        orders = db.get_all_orders(limit=20, status=status_filter)
    except Exception as exc:
        logger.exception("Failed get_all_orders: %s", exc)
        await message.reply_text(t("admin_try_again", lang), reply_markup=_admin_back_keyboard(lang))
        return

    if not orders:
        await message.reply_text(
            f"{t('admin_recent_orders', lang)}\n\n{t('no_products', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    lines = [f"{t('admin_recent_orders', lang)} ({len(orders)})\n"]

    for o in orders:
        username = o.get("username") or "no_user"
        status = o.get("status", "pending")
        emoji = _STATUS_EMOJI.get(status, "⏳")
        oid = o["id"]
        product = db.get_product(o.get("product_id", 1))
        product_name = escape_md(product["name"]) if product else "N/A"

        lines.append(
            f"#{oid} | @{username}\n"
            f"📦 {product_name}\n"
            f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
            f"{t('status_label_header', lang)}: {emoji} {status}\n"
        )

    filter_buttons = [
        InlineKeyboardButton(t("btn_all", lang), callback_data="admin:orders"),
        InlineKeyboardButton(t("btn_pending", lang), callback_data="admin:orders_pending"),
        InlineKeyboardButton(t("btn_paid", lang), callback_data="admin:orders_paid"),
    ]
    keyboard_rows = [filter_buttons]
    keyboard_rows.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard_rows),
    )


async def cmd_setprice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            f"{t('admin_change_price', lang)}\n\n"
            f"{t('cmd_setprice_usage', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text(t("admin_id_number", lang), reply_markup=_admin_back_keyboard(lang))
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            t("admin_not_found", lang, id=product_id),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    try:
        new_price = int(args[1].replace(".", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text(t("admin_price_must_be_number", lang), reply_markup=_admin_back_keyboard(lang))
        return

    if new_price <= 0:
        await update.message.reply_text(t("admin_price_gt_zero", lang), reply_markup=_admin_back_keyboard(lang))
        return

    db.update_product(product_id, price=new_price)
    updated = db.get_product(product_id)
    await update.message.reply_text(
        f"{t('admin_price_updated', lang)}\n\n"
        f"{t('admin_name', lang)}: *{updated['name']}*\n"
        f"{t('admin_new_price', lang)}: *Rp {new_price:,}/{t('accounts', lang)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    args = context.args or []
    image_url = None
    text_parts = []
    for arg in args:
        if arg.startswith("--img="):
            image_url = arg[6:]
        else:
            text_parts.append(arg)

    broadcast_text = " ".join(text_parts).strip()

    if not broadcast_text and not image_url:
        await message.reply_text(
            f"{t('admin_broadcast', lang)}\n\n"
            f"{t('cmd_broadcast_usage', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    try:
        user_ids = db.get_all_user_ids()
    except Exception as exc:
        logger.exception("Failed get_all_user_ids: %s", exc)
        await message.reply_text(t("admin_try_again", lang), reply_markup=_admin_back_keyboard(lang))
        return

    success = 0
    failed = 0
    for uid in user_ids:
        try:
            if image_url:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=image_url,
                    caption=broadcast_text or None,
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await context.bot.send_message(chat_id=uid, text=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            success += 1
        except Exception:
            failed += 1

    await message.reply_text(
        f"{t('admin_broadcast_done', lang)}\n\n"
        f"{t('admin_sent', lang)}: *{success}* {t('users', lang)}\n"
        f"{t('admin_failed', lang)}: *{failed}* {t('users', lang)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    args = context.args or []
    if not args:
        await message.reply_text(
            f"{t('admin_add_admin', lang)}\n\n"
            f"{t('cmd_addadmin_usage', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    try:
        new_admin_id = int(args[0])
    except ValueError:
        await message.reply_text(t("admin_id_number", lang), reply_markup=_admin_back_keyboard(lang))
        return

    if new_admin_id in config.ADMIN_IDS:
        await update.message.reply_text(
            t("admin_already_admin", lang, id=new_admin_id),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    config.ADMIN_IDS.add(new_admin_id)
    await update.message.reply_text(
        f"{t('admin_added', lang)}\n\n"
        f"{t('admin_id', lang)}: `{new_admin_id}`\n"
        f"{t('admin_total_admins', lang)}: *{len(config.ADMIN_IDS)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    args = context.args or []
    if not args:
        await message.reply_text(
            f"{t('admin_remove_admin', lang)}\n\n"
            f"{t('cmd_removeadmin_usage', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    try:
        remove_id = int(args[0])
    except ValueError:
        await message.reply_text(t("admin_id_number", lang), reply_markup=_admin_back_keyboard(lang))
        return

    if remove_id == config.ADMIN_USER_ID:
        await update.message.reply_text(t("admin_cannot_remove", lang), reply_markup=_admin_back_keyboard(lang))
        return

    if remove_id not in config.ADMIN_IDS:
        await update.message.reply_text(
            t("admin_id_not_admin", lang, id=remove_id),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_admin_back_keyboard(lang),
        )
        return

    config.ADMIN_IDS.discard(remove_id)
    await update.message.reply_text(
        f"{t('admin_removed', lang)}\n\n"
        f"{t('admin_id', lang)}: `{remove_id}`\n"
        f"{t('admin_total_admins', lang)}: *{len(config.ADMIN_IDS)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )


async def cmd_adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await _deny_non_admin(update)
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    lines = [f"{t('admin_list_title', lang)}\n"]
    for i, aid in enumerate(sorted(config.ADMIN_IDS), 1):
        is_main = " ⭐" if aid == config.ADMIN_USER_ID else ""
        lines.append(f"{i}. `{aid}`{is_main}")

    lines.append(f"\n📊 {t('admin_total', lang)}: *{len(config.ADMIN_IDS)}* {t('admins', lang)}")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_admin_back_keyboard(lang),
    )
