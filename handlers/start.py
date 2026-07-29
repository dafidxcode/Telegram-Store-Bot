"""Start, help, and menu command handlers with inline keyboard buttons."""

import logging
import os
from datetime import datetime, timezone, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

import config
import db
import lang as L
from channel_guard import require_channel_join, handle_check_join
from notifier import send_channel_purchase_notif

logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"


def escape_md(text: str) -> str:
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


def format_rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def get_lang(context: ContextTypes.DEFAULT_TYPE, user_id: int = 0) -> str:
    cached = context.user_data.get("lang")
    if cached:
        return cached
    if user_id:
        db_lang = db.get_user_lang(user_id)
        context.user_data["lang"] = db_lang
        return db_lang
    return DEFAULT_LANG


def save_lang(context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str) -> None:
    context.user_data["lang"] = lang
    db.save_lang(user_id, lang)


def t(key: str, lang: str, **fmt) -> str:
    s = L.T.get(key, {}).get(lang) or L.T.get(key, {}).get(DEFAULT_LANG) or key
    if fmt:
        return s.format(**fmt)
    return s


def get_now_wib() -> str:
    wib = datetime.now(tz=timezone(timedelta(hours=7)))
    fmt = "%#d %B %Y at %#H:%M WIB" if os.name == "nt" else "%-d %B %Y at %-H:%M WIB"
    return wib.strftime(fmt)


def get_greeting(lang: str = "en") -> str:
    hour = datetime.now(tz=timezone(timedelta(hours=7))).hour
    if 4 <= hour < 11:
        return t("good_morning", lang)
    elif 11 <= hour < 15:
        return t("good_afternoon", lang)
    elif 15 <= hour < 18:
        return t("good_evening", lang)
    else:
        return t("good_night", lang)


# ---------------------------------------------------------------------------
# Global navigation buttons
# ---------------------------------------------------------------------------

def btn_home(lang="en"):
    return InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")


def btn_back(lang="en", text=None, data="menu:start"):
    return InlineKeyboardButton(text or t("btn_back", lang), callback_data=data)


def btn_cancel_payment(lang="en"):
    return InlineKeyboardButton(t("btn_cancel_pay", lang), callback_data="global:cancel_payment")


def global_nav_row(lang="en"):
    return [btn_home(lang)]


def global_nav_keyboard(user_id: int = 0, lang="en"):
    return InlineKeyboardMarkup([
        [btn_back(lang), btn_cancel_payment(lang), btn_home(lang)],
    ])


def global_nav_keyboard_simple(user_id: int = 0, lang="en"):
    return InlineKeyboardMarkup([global_nav_row(lang)])


NUM_EMOJIS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}

def get_num_emoji(n: int) -> str:
    if 1 <= n <= 10:
        return NUM_EMOJIS[n]
    digits = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    return "".join(digits[int(d)] for d in str(n))


# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

def build_home_text(user, lang: str = "en") -> str:
    sold = db.get_total_sold()
    total_users = db.get_total_users()
    user_orders = db.get_user_order_count(user.id)
    username = escape_md(f"@{user.username}") if user.username else "N/A"
    first_name = escape_md(user.first_name or "friend")
    active_products = db.get_active_products()
    product_count = len(active_products)

    product_lines = []
    for i, p in enumerate(active_products, 1):
        product_lines.append(f"{get_num_emoji(i)} {escape_md(p['name'])}")

    product_stock_text = "\n".join(product_lines) if product_lines else f"{t('no_products', lang)}"

    return (
        f"{get_greeting(lang)}, {first_name}!\n"
        f"📅 {get_now_wib()}\n"
        f"\n"
        f"{t('welcome', lang, shop=escape_md(config.SHOP_NAME))}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*{t('account_stats', lang)}*\n"
        f"{t('username', lang)} : {username}\n"
        f"{t('user_id_label', lang)} : {user.id}\n"
        f"{t('total_orders', lang, n=user_orders)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*{t('bot_stats', lang)}*\n"
        f"{t('accounts_sold', lang, n=sold)}\n"
        f"{t('active_products', lang, n=product_count)}\n"
        f"{t('total_users', lang, n=total_users)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*{t('stock_per', lang)}*\n"
        f"{product_stock_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"{t('where_start', lang)}\n"
        f"{t('hint_buy', lang)}\n"
        f"{t('hint_orders', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def build_products_text(lang: str = "en") -> str:
    products = db.get_active_products()
    if not products:
        return t("no_products_yet", lang)

    lines = [f"{t('product_list_title', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for i, p in enumerate(products, 1):
        if p["stock_type"] == "preorder":
            stock_text = f"*{t('preorder_stock_text', lang)}*"
        else:
            cnt = db.get_stock_count(p["id"])
            stock_text = "❌ *HABIS*" if cnt == 0 else f"*{cnt}* {t('accounts', lang)}"

        duration = f"\n{t('duration', lang)}: {escape_md(p['duration'])}" if p.get("duration") else ""
        desc = f"\n📝 {escape_md(p['description'])}" if p.get("description") else ""

        lines.append(
            f"*{i}. {escape_md(p['name'])}*\n"
            f"{desc}{duration}\n"
            f"{t('price', lang)}: *Rp {format_rupiah(p['price'])}*\n"
            f"{t('stock', lang)}: {stock_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    lines.append(f"\n{t('select_product', lang)}")
    return "\n".join(lines)


def get_main_menu_keyboard(user_id: int = 0, lang: str = "id"):
    lang_label = "🌐 Bahasa Indonesia" if lang == "en" else "🌐 English"

    rows = [
        [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
        [
            InlineKeyboardButton(t("btn_check_stock", lang), callback_data="menu:stok"),
            InlineKeyboardButton(t("btn_order_history", lang), callback_data="menu:orders"),
        ],
        [
            InlineKeyboardButton(t("btn_referral", lang), callback_data="menu:referral"),
            InlineKeyboardButton(t("btn_feedback", lang), callback_data="menu:feedback"),
        ],
        [
            InlineKeyboardButton(lang_label, callback_data="menu:lang"),
        ],
    ]
    if user_id in config.ADMIN_IDS:
        rows.append([InlineKeyboardButton(t("btn_admin_panel", lang), callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def get_admin_panel_keyboard(lang="id"):
    """Main Admin Panel keyboard with clean sub-menu category buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_sub_products", lang), callback_data="admin:sub_products")],
        [InlineKeyboardButton(t("btn_sub_orders", lang), callback_data="admin:sub_orders")],
        [InlineKeyboardButton(t("btn_sub_users", lang), callback_data="admin:sub_users")],
        [InlineKeyboardButton(t("btn_sub_system", lang), callback_data="admin:sub_system")],
        [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
    ])


def get_admin_products_keyboard(lang="id"):
    """Sub-menu 1: Produk & Stok."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_view_products", lang), callback_data="admin:products"),
            InlineKeyboardButton(t("btn_stock_info", lang), callback_data="admin:stockinfo"),
        ],
        [
            InlineKeyboardButton(t("btn_add_product", lang), callback_data="admin:addproduct"),
            InlineKeyboardButton(t("btn_edit_product", lang), callback_data="admin:eprod"),
        ],
        [
            InlineKeyboardButton(t("btn_add_stock", lang), callback_data="admin:addstock"),
            InlineKeyboardButton(t("btn_delete_product", lang), callback_data="admin:delproduct"),
        ],
        [
            InlineKeyboardButton(t("btn_export_stock", lang), callback_data="admin:exstock"),
        ],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
    ])


def get_admin_orders_keyboard(lang="id"):
    """Sub-menu 2: Pesanan & Keuangan."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_view_orders", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_financial_report", lang), callback_data="admin:report"),
        ],
        [
            InlineKeyboardButton(t("btn_search_order", lang), callback_data="admin:search"),
            InlineKeyboardButton(t("btn_pending_preorders", lang), callback_data="admin:preorders"),
        ],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
    ])


def get_admin_users_keyboard(lang="id"):
    """Sub-menu 3: Pengguna, Referral & Feedback."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_user_management", lang), callback_data="admin:users"),
            InlineKeyboardButton(t("btn_feedback_list", lang), callback_data="admin:feedbacklist"),
        ],
        [
            InlineKeyboardButton(t("btn_withdrawal_requests", lang), callback_data="admin:withdrawals"),
            InlineKeyboardButton(t("btn_commission_settings", lang), callback_data="admin:commission"),
        ],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
    ])


def get_admin_system_keyboard(lang="id"):
    """Sub-menu 4: Sistem & Pengaturan Bot."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_broadcast", lang), callback_data="admin:broadcast"),
            InlineKeyboardButton(t("btn_admin_list", lang), callback_data="admin:adminlist"),
        ],
        [
            InlineKeyboardButton(t("btn_bot_settings", lang), callback_data="admin:settings"),
        ],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
    ])


def get_admin_back_keyboard(lang="id", back_data="menu:admin"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_back", lang), callback_data=back_data)],
        [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
    ])


_STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦"}


@require_channel_join
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text input for feedback messages and withdrawal flow from regular users."""
    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    admin_state = context.user_data.get("admin_state")
    withdraw_state = context.user_data.get("withdraw_state")

    if withdraw_state:
        message = update.message
        if message is None or not message.text:
            return
        text = message.text.strip()

        if text.lower() in ("/cancel", "batal", "cancel"):
            context.user_data.pop("withdraw_state", None)
            await message.reply_text(
                t("cancelled", lang),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
                ]),
            )
            return

        if withdraw_state == "bank":
            context.user_data["withdraw_bank"] = text
            context.user_data["withdraw_state"] = "account"
            await message.reply_text(
                t("withdraw_account_prompt", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t("cancel", lang), callback_data="menu:referral"),
                ]]),
            )
            return

        if withdraw_state == "account":
            context.user_data["withdraw_account"] = text
            context.user_data["withdraw_state"] = "name"
            await message.reply_text(
                t("withdraw_name_prompt", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t("cancel", lang), callback_data="menu:referral"),
                ]]),
            )
            return

        if withdraw_state == "name":
            context.user_data["withdraw_name"] = text
            context.user_data["withdraw_state"] = "amount"
            balance = db.get_user_commission_balance(user_id)
            await message.reply_text(
                f"{t('withdraw_amount_prompt', lang)}\n\n💰 {t('withdraw_balance', lang)}: *Rp {format_rupiah(balance)}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t("cancel", lang), callback_data="menu:referral"),
                ]]),
            )
            return

        if withdraw_state == "amount":
            try:
                amount = int(text.replace(".", "").replace(",", ""))
            except ValueError:
                await message.reply_text("Harus angka. Kirim ulang jumlah pencairan:", reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t("cancel", lang), callback_data="menu:referral"),
                ]]))
                return

            balance = db.get_user_commission_balance(user_id)
            min_wd = db.get_min_withdrawal()

            if amount < min_wd:
                await message.reply_text(
                    t("withdraw_below_min", lang, min=format_rupiah(min_wd), balance=format_rupiah(balance)),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            if amount > balance:
                await message.reply_text(
                    t("withdraw_insufficient", lang, balance=format_rupiah(balance)),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            bank = context.user_data.pop("withdraw_bank", "")
            account = context.user_data.pop("withdraw_account", "")
            name = context.user_data.pop("withdraw_name", "")
            context.user_data.pop("withdraw_state", None)

            wd_id = db.create_withdrawal_request(user_id, amount, bank, account, name)
            await message.reply_text(
                t("withdraw_success", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:referral")],
                    [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
                ]),
            )

            try:
                for admin_id in config.ADMIN_IDS:
                    admin_lang = db.get_user_lang(admin_id)
                    user_name = f"@{update.effective_user.username}" if update.effective_user and update.effective_user.username else str(user_id)
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=t("withdraw_notif", admin_lang,
                            name=user_name, user_id=user_id,
                            amount=format_rupiah(amount),
                            bank=bank, account=account, acc_name=name),
                        parse_mode=ParseMode.MARKDOWN,
                    )
            except Exception:
                pass
            return

    if admin_state == "feedback_msg":
        message = update.message
        if message is None or not message.text:
            return
        feedback_text = message.text.strip()
        category = context.user_data.pop("feedback_category", "lainnya")
        context.user_data.pop("admin_state", None)

        username = update.effective_user.username or "" if update.effective_user else ""
        db.add_feedback(user_id, username, category, feedback_text)

        await message.reply_text(
            t("feedback_sent", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
            ]),
        )


def register(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(handle_check_join, pattern=r"^check_join$"))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stock", cmd_stock))
    app.add_handler(CommandHandler("produk", cmd_produk))
    app.add_handler(CallbackQueryHandler(handle_global_cancel, pattern=r"^global:cancel_payment$"))
    app.add_handler(CallbackQueryHandler(handle_lang_toggle, pattern=r"^menu:lang$"))
    app.add_handler(CallbackQueryHandler(handle_referral_claim, pattern=r"^referral:claim$"))
    app.add_handler(CallbackQueryHandler(handle_feedback_category, pattern=r"^feedback:"))
    app.add_handler(CallbackQueryHandler(handle_menu_button, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(handle_admin_button, pattern=r"^admin:"))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, handle_text_input), group=5)


@require_channel_join
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if user is None or message is None:
        return

    if db.is_user_banned(user.id):
        lang = get_lang(context, user.id)
        await message.reply_text(t("banned_alert", lang))
        return

    try:
        db.upsert_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("Failed upsert user %s: %s", user.id, exc)

    if context.args and context.args[0].startswith("ref_"):
        ref_code = context.args[0][4:]
        ref_user = db.get_user_by_referral_code(ref_code)
        if ref_user and ref_user["user_id"] != user.id:
            granted = db.set_referred_by(user.id, ref_user["user_id"])
            if granted:
                lang = get_lang(context, user.id)
                try:
                    referrer_lang = db.get_user_lang(ref_user["user_id"])
                    await context.bot.send_message(
                        chat_id=ref_user["user_id"],
                        text=f"🎉 *Referral baru!* {user.first_name or 'User'} menggunakan kode referral Anda!",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass

    lang = get_lang(context, user.id)
    text = build_home_text(user, lang)
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard(user.id, lang))


@require_channel_join
async def cmd_produk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    text = build_products_text(lang)
    products = db.get_active_products()
    buttons = []
    for p in products:
        if p["stock_type"] == "limited" and db.get_stock_count(p["id"]) <= 0:
            continue
        p_name = escape_md(p['name'])
        btn_title = p_name if p_name.startswith(("🛒", "🛍️", "📦")) else f"🛒 {p_name}"
        buttons.append([InlineKeyboardButton(
            btn_title,
            callback_data=f"buy:{p['id']}",
        )])
    buttons.append([btn_home(lang)])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))


@require_channel_join
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    keyboard = InlineKeyboardMarkup([global_nav_row(lang)])

    text = (
        f"{t('help_title', lang)}\n\n"
        f"{t('help_how_buy', lang)}\n"
        f"{t('help_step1', lang)}\n"
        f"{t('help_step2', lang)}\n"
        f"{t('help_step3', lang)}\n"
        f"{t('help_step4', lang)}\n"
        f"{t('help_step5', lang)}\n\n"
        f"{t('help_commands', lang)}\n"
        f"{t('help_cmd_start', lang)}\n"
        f"{t('help_cmd_produk', lang)}\n"
        f"{t('help_cmd_beli', lang)}\n"
        f"{t('help_cmd_stock', lang)}\n"
        f"{t('help_cmd_myorders', lang)}\n"
        f"{t('help_cmd_cancel', lang)}\n\n"
        f"{t('help_lang_tip', lang)}"
    )

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@require_channel_join
async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    products = db.get_active_products()
    total_stock = db.get_stock_count()

    text = f"{t('stock_info', lang)}\n\n"
    if products:
        for p in products:
            if p["stock_type"] == "preorder":
                stock_str = t("preorder_label", lang)
            else:
                cnt = db.get_stock_count(p["id"])
                stock_str = "❌ HABIS" if cnt == 0 else f"{cnt} {t('accounts', lang)}"
            text += f"*{escape_md(p['name'])}*: {stock_str}\n"
        text += f"\n{t('total_stock', lang)}: *{total_stock}*"
    else:
        text += t("no_products", lang)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
        [btn_home(lang)],
    ])

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Language toggle handler — saves to DB
# ---------------------------------------------------------------------------

async def handle_lang_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    user = update.effective_user
    if user is None:
        return

    current = get_lang(context, user.id)
    new_lang = "id" if current == "en" else "en"
    save_lang(context, user.id, new_lang)

    text = build_home_text(user, new_lang)
    await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(user.id, new_lang))


# ---------------------------------------------------------------------------
# Global cancel payment handler
# ---------------------------------------------------------------------------

async def handle_global_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)
    orders = db.get_user_orders(user_id)
    pending = [o for o in orders if o.get("status") == "pending"]

    if not pending:
        await query.answer(t("cancel_no_pending", lang), show_alert=True)
        return

    await query.answer()

    order = pending[0]
    order_id = order["id"]

    db.update_order_status(order_id, "cancelled")
    db.release_stock(order_id)

    qris_msg_id = order.get("qris_message_id")
    chat_id = query.message.chat_id if query.message else user_id

    if qris_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=qris_msg_id)
        except Exception:
            pass

    try:
        await query.message.delete()
    except Exception:
        pass

    user = update.effective_user
    text = build_home_text(user, lang) if user else "Home"
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(user_id, lang),
    )


# ---------------------------------------------------------------------------
# Referral claim handler
# ---------------------------------------------------------------------------

@require_channel_join
async def handle_referral_claim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    code = db.generate_referral_code(user_id)
    ref_count = db.get_referral_count(user_id)
    ref_list = db.get_referral_list(user_id)

    lines = [
        f"{t('referral_stats', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('referral_code_label', lang)}: `{code}`\n"
        f"{t('referral_count', lang)}: *{ref_count}*\n"
    ]

    if ref_list:
        lines.append(f"\n📋 *Referral List:*")
        for r in ref_list[:10]:
            name = r.get("username") or r.get("first_name") or str(r["referred_id"])
            lines.append(f"  @{name}" if r.get("username") else f"  {name}")

    text = "\n".join(lines)
    buttons = [
        [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
    ]
    await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))


# ---------------------------------------------------------------------------
# Feedback handlers
# ---------------------------------------------------------------------------

@require_channel_join
async def handle_feedback_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    category = query.data.split(":")[1] if query.data else "lainnya"
    context.user_data["feedback_category"] = category
    context.user_data["admin_state"] = "feedback_msg"

    cat_label = t(f"feedback_{category}", lang)
    text = (
        f"{t('feedback_title', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('feedback_category', lang)}: *{cat_label}*\n\n"
        f"{t('feedback_send_msg', lang)}"
    )
    buttons = [
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:feedback")],
        [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
    ]
    await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))


# ---------------------------------------------------------------------------
# Menu button callbacks
# ---------------------------------------------------------------------------

async def _safe_edit_or_send(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except BadRequest as exc:
        err_msg = str(exc)
        if "Message is not modified" in err_msg:
            return
        bot = query.get_bot() if hasattr(query, "get_bot") else (query.message.get_bot() if query and query.message else None)
        try:
            if query and query.message:
                await query.message.delete()
        except Exception:
            pass
        chat_id = query.message.chat_id if (query and query.message) else 0
        if chat_id and bot:
            await bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup,
            )
    except Exception:
        bot = query.get_bot() if hasattr(query, "get_bot") else (query.message.get_bot() if query and query.message else None)
        chat_id = query.message.chat_id if (query and query.message) else 0
        if chat_id and bot:
            await bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup,
            )


@require_channel_join
async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    action = query.data.split(":")[1] if query.data else ""
    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    if action == "start":
        context.user_data.pop("admin_state", None)
        context.user_data.pop("feedback_category", None)
        user = update.effective_user
        text = build_home_text(user, lang)
        await _safe_edit_or_send(query, text, reply_markup=get_main_menu_keyboard(user_id, lang))

    elif action == "produk":
        text = build_products_text(lang)
        products = db.get_active_products()
        buttons = []
        for p in products:
            if p["stock_type"] == "limited" and db.get_stock_count(p["id"]) <= 0:
                continue
            p_name = escape_md(p['name'])
            btn_title = p_name if p_name.startswith(("🛒", "🛍️", "📦")) else f"🛒 {p_name}"
            buttons.append([InlineKeyboardButton(
                btn_title,
                callback_data=f"buy:{p['id']}",
            )])
        buttons.append([btn_home(lang)])
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "stok":
        products = db.get_active_products()
        total_stock = db.get_stock_count()

        text = f"{t('stock_info', lang)}\n\n"
        if products:
            for p in products:
                if p["stock_type"] == "limited":
                    cnt = db.get_stock_count(p["id"])
                    stock_str = "❌ HABIS" if cnt == 0 else f"{cnt} {t('accounts', lang)}"
                elif p["stock_type"] == "preorder":
                    stock_str = t("preorder_label", lang)
                else:
                    stock_str = t("unlimited", lang)
                text += f"*{escape_md(p['name'])}*: {stock_str}\n"
            text += f"\n{t('total_stock', lang)}: *{total_stock}*"
        else:
            text += t("no_products", lang)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
            [btn_home(lang)],
        ])
        await _safe_edit_or_send(query, text, reply_markup=keyboard)

    elif action == "orders":
        keyboard = InlineKeyboardMarkup([global_nav_row(lang)])
        try:
            orders = db.get_user_orders(user_id)

            if not orders:
                await _safe_edit_or_send(
                    query,
                    t("no_orders", lang),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(t("btn_product_list", lang), callback_data="menu:produk")],
                        [btn_home(lang)],
                    ]),
                )
                return

            recent = orders[:10]
            lines = [f"{t('order_history', lang)}\n"]

            for o in recent:
                oid = o.get("id", "")
                qty = o.get("quantity", 0)
                total = o.get("total", 0)
                status = o.get("status", "pending")
                emoji = _STATUS_EMOJI.get(status, "⏳")
                product = db.get_product(o.get("product_id", 1))
                product_name = escape_md(product["name"]) if product else "N/A"
                lines.append(f"#{oid} | {product_name} x{qty} | Rp {format_rupiah(total)} | {emoji} {status}")

            buttons = []
            for o in recent:
                oid = o.get("id", "")
                buttons.append([InlineKeyboardButton(
                    f"📋 Detail #{oid}",
                    callback_data=f"menu:detail:{oid}",
                )])
            buttons.append([InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")])

            await _safe_edit_or_send(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.exception("handle_menu orders error: %s", e)
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=keyboard)

    elif action == "admin":
        if user_id not in config.ADMIN_IDS:
            await query.answer(t("admin_access_denied", lang), show_alert=True)
            return

        total_stock = db.get_stock_count()
        sold = db.get_total_sold()
        total_users = db.get_total_users()
        products = db.get_active_products()
        pending = len(db.get_pending_qris_orders())

        product_lines = []
        for i, p in enumerate(products, 1):
            p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            product_lines.append(f"{get_num_emoji(i)} {escape_md(p['name'])}: {p_stock} stock | Rp {format_rupiah(p['price'])}")

        product_stock_text = "\n".join(product_lines) if product_lines else f"{t('no_products_admin', lang)}"

        text = (
            f"{t('admin_panel', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('dashboard', lang)}\n"
            f"{t('stock_ready', lang)} : *{total_stock}* {t('accounts', lang)}\n"
            f"{t('sold', lang)} : *{sold}* {t('accounts', lang)}\n"
            f"{t('pending_orders', lang)} : *{pending}*\n"
            f"{t('total_users', lang, n=total_users)}\n"
            f"{t('total_products', lang)} : *{len(products)}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('per_product_stock', lang)}\n"
            f"{product_stock_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('select_admin_menu', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_panel_keyboard(lang))

    elif action == "referral":
        code = db.generate_referral_code(user_id)
        ref_count = db.get_referral_count(user_id)
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{code}"
        commission_pct = db.get_commission_percent()
        balance = db.get_user_commission_balance(user_id)
        total_earned = db.get_user_total_commission(user_id)
        min_wd = db.get_min_withdrawal()

        text = (
            f"{t('referral_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔑 {t('referral_code_label', lang)}: `{code}`\n"
            f"{t('referral_link', lang)}:\n`{referral_link}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('referral_count', lang)}: *{ref_count}*\n"
            f"{t('commission_rate_label', lang)}: *{commission_pct}%*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('commission_earned', lang)}: *Rp {format_rupiah(total_earned)}*\n"
            f"{t('commission_balance', lang)}: *Rp {format_rupiah(balance)}*\n"
            f"{t('withdraw_min', lang)}: Rp {format_rupiah(min_wd)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('referral_share', lang)}"
        )
        buttons = [
            [InlineKeyboardButton(t("btn_commission_history", lang), callback_data="menu:commission_history")],
            [InlineKeyboardButton(t("btn_withdraw", lang), callback_data="menu:withdraw")],
            [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "commission_history":
        commissions = db.get_user_commissions(user_id, limit=15)
        lines = [f"{t('commission_history', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
        if not commissions:
            lines.append(t("commission_no_history", lang))
        else:
            for c in commissions:
                name = c.get("referred_username") or c.get("referred_name") or str(c["referred_id"])
                lines.append(
                    f"💰 +Rp {format_rupiah(c['commission_amount'])} "
                    f"{t('commission_from', lang)} @{name} "
                    f"{t('commission_on_order', lang)} #{c['order_id']}\n"
                    f"📅 {c['created_at']}"
                )
        buttons = [
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:referral")],
            [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
        ]
        await _safe_edit_or_send(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "withdraw":
        balance = db.get_user_commission_balance(user_id)
        min_wd = db.get_min_withdrawal()

        if balance < min_wd:
            await query.answer(
                t("withdraw_below_min", lang, min=format_rupiah(min_wd), balance=format_rupiah(balance)),
                show_alert=True,
            )
            return

        context.user_data["withdraw_state"] = "bank"
        text = (
            f"{t('withdraw_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('withdraw_balance', lang)}: *Rp {format_rupiah(balance)}*\n"
            f"{t('withdraw_min', lang)}: Rp {format_rupiah(min_wd)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('withdraw_bank_prompt', lang)}"
        )
        buttons = [
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:referral")],
            [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "withdraw_history":
        withdrawals = db.get_user_withdrawals(user_id, limit=10)
        lines = [f"{t('withdraw_history', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
        if not withdrawals:
            lines.append(t("withdraw_no_history", lang))
        else:
            status_map = {"pending": t("withdraw_pending", lang), "approved": t("withdraw_approved", lang), "rejected": t("withdraw_rejected", lang)}
            for w in withdrawals:
                s = status_map.get(w["status"], w["status"])
                lines.append(t("withdraw_detail", lang,
                    id=w["id"], amount=format_rupiah(w["amount"]), status=s,
                    bank=w.get("bank_name", "-"), account=w.get("account_number", "-"),
                    name=w.get("account_name", "-"), date=w.get("created_at", "-")))
        buttons = [
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:referral")],
            [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
        ]
        await _safe_edit_or_send(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "feedback":
        context.user_data["feedback_category"] = "umum"
        context.user_data["admin_state"] = "feedback_msg"
        text = (
            f"{t('feedback_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('feedback_send_msg', lang)}"
        )
        buttons = [
            [InlineKeyboardButton(t("cancel", lang), callback_data="menu:start")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "detail":
        parts = query.data.split(":")
        if len(parts) < 3:
            return
        order_id = parts[2]
        order = db.get_order(order_id)
        if not order or order["user_id"] != user_id:
            await query.answer("Pesanan tidak ditemukan.", show_alert=True)
            return

        product = db.get_product(order.get("product_id", 1))
        product_name = escape_md(product["name"]) if product else "N/A"
        detail = db.get_purchase_detail(order_id)

        status_emoji = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "delivered": "📦"}.get(order.get("status", ""), "⏳")

        text = (
            f"{t('purchase_detail_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('purchase_detail_order', lang)}: `#{order_id}`\n"
            f"{t('purchase_detail_product', lang)}: *{product_name}*\n"
            f"{t('purchase_detail_qty', lang)}: {order['quantity']} {t('accounts', lang)}\n"
            f"{t('purchase_detail_total', lang)}: *Rp {format_rupiah(order['total'])}*\n"
        )

        if order.get("original_total") and order["original_total"] > order["total"]:
            discount = order["original_total"] - order["total"]
            text += f"{t('purchase_detail_discount', lang)}: -Rp {format_rupiah(discount)}\n"
        if order.get("voucher_code"):
            text += f"{t('purchase_detail_voucher', lang)}: `{order['voucher_code']}`\n"

        text += (
            f"{t('purchase_detail_status', lang)}: {status_emoji} {order.get('status', '').upper()}\n"
            f"{t('purchase_detail_date', lang)}: {order.get('created_at', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

        if detail and detail.get("accounts_delivered"):
            text += f"\n{t('purchase_detail_accounts', lang)}:\n```\n{detail['accounts_delivered']}\n```"
        elif order.get("status") == "paid":
            text += f"\n{t('purchase_detail_accounts', lang)}: Menunggu..."

        buttons = [
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:orders")],
            [InlineKeyboardButton(t("btn_home", lang), callback_data="menu:start")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))


# ---------------------------------------------------------------------------
# Admin panel button callbacks
# ---------------------------------------------------------------------------

async def handle_admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    user_id = update.effective_user.id if update.effective_user else 0
    lang = get_lang(context, user_id)

    if user_id not in config.ADMIN_IDS:
        await query.answer(t("admin_access_denied", lang), show_alert=True)
        return

    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    for key in list(context.user_data.keys()):
        if key.startswith("admin_state") or key in ("addstock_product_id", "setprice_product_id", "addadmin_id"):
            del context.user_data[key]

    if action == "sub_products":
        text = f"*{t('btn_sub_products', lang)}*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nPilih fitur kelola produk & stok di bawah ini:"
        await _safe_edit_or_send(query, text, reply_markup=get_admin_products_keyboard(lang))

    elif action == "sub_orders":
        text = f"*{t('btn_sub_orders', lang)}*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nPilih fitur kelola pesanan & keuangan di bawah ini:"
        await _safe_edit_or_send(query, text, reply_markup=get_admin_orders_keyboard(lang))

    elif action == "sub_users":
        text = f"*{t('btn_sub_users', lang)}*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nPilih fitur kelola pengguna & referral di bawah ini:"
        await _safe_edit_or_send(query, text, reply_markup=get_admin_users_keyboard(lang))

    elif action == "sub_system":
        text = f"*{t('btn_sub_system', lang)}*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nPilih fitur sistem & pengaturan bot di bawah ini:"
        await _safe_edit_or_send(query, text, reply_markup=get_admin_system_keyboard(lang))

    elif action == "products":
        products = db.get_all_products()
        if not products:
            await _safe_edit_or_send(
                query,
                t("admin_no_products", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"{t('admin_product_list', lang)}\n"]
        for i, p in enumerate(products, 1):
            stock = t("preorder_label", lang) if p["stock_type"] == "preorder" else f"{db.get_stock_count(p['id'])} accounts"
            status = "✅" if p["is_active"] else "❌"
            lines.append(
                f"{status} {get_num_emoji(i)} | *{escape_md(p['name'])}*\n"
                f"   {t('admin_price', lang)}: Rp {format_rupiah(p['price'])}\n"
                f"   {t('admin_stock', lang)}: {stock}\n"
            )

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "stockinfo":
        total_stock = db.get_stock_count()
        pending = len(db.get_pending_qris_orders())
        products = db.get_active_products()

        text = (
            f"{t('admin_stock_info', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 {t('admin_total_ready', lang)}: *{total_stock}* {t('accounts', lang)}\n"
            f"⏳ {t('admin_pending_orders', lang)}: *{pending}*\n"
        )
        for i, p in enumerate(products, 1):
            p_stock = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
            text += f"\n{get_num_emoji(i)} {escape_md(p['name'])}: *{p_stock}* | Rp {format_rupiah(p['price'])}"

        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "orders":
        try:
            orders = db.get_all_orders(limit=20)
        except Exception as exc:
            logger.exception("Failed get_all_orders: %s", exc)
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=get_admin_back_keyboard(lang))
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                t("admin_no_orders", lang),
                reply_markup=get_admin_back_keyboard(lang),
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
                f"Status: {emoji} {status}\n"
            )

        filter_buttons = [
            InlineKeyboardButton(t("btn_all", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_pending", lang), callback_data="admin:orders_pending"),
            InlineKeyboardButton(t("btn_paid", lang), callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_pending":
        try:
            orders = db.get_all_orders(limit=20, status="pending")
        except Exception:
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=get_admin_back_keyboard(lang))
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                t("admin_no_pending", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"{t('admin_pending_orders_title', lang)} ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            oid = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"
            lines.append(
                f"#{oid} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
            )

        filter_buttons = [
            InlineKeyboardButton(t("btn_all", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_pending", lang), callback_data="admin:orders_pending"),
            InlineKeyboardButton(t("btn_paid", lang), callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "orders_paid":
        try:
            orders = db.get_all_orders(limit=20, status="paid")
        except Exception:
            await _safe_edit_or_send(query, t("admin_try_again", lang), reply_markup=get_admin_back_keyboard(lang))
            return

        if not orders:
            await _safe_edit_or_send(
                query,
                t("admin_no_paid", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"{t('admin_paid_orders', lang)} ({len(orders)})\n"]
        for o in orders:
            username = o.get("username") or "no_user"
            oid = o["id"]
            product = db.get_product(o.get("product_id", 1))
            product_name = escape_md(product["name"]) if product else "N/A"
            lines.append(
                f"#{oid} | @{username}\n"
                f"📦 {product_name}\n"
                f"🔢 {o['quantity']} = Rp {format_rupiah(o['total'])}\n"
            )

        filter_buttons = [
            InlineKeyboardButton(t("btn_all", lang), callback_data="admin:orders"),
            InlineKeyboardButton(t("btn_pending", lang), callback_data="admin:orders_pending"),
            InlineKeyboardButton(t("btn_paid", lang), callback_data="admin:orders_paid"),
        ]
        keyboard_rows = [filter_buttons]
        keyboard_rows.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )

    elif action == "preorders":
        pending_preorders = db.get_pending_preorders()
        if not pending_preorders:
            await _safe_edit_or_send(
                query,
                "❌ *Tidak ada pesanan Pre-Order yang pending saat ini.*",
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        lines = [f"⏳ *PESANAN PRE-ORDER PENDING ({len(pending_preorders)})*\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
        buttons = []
        for o in pending_preorders:
            username = f"@{o['username']}" if o.get("username") else f"ID {o['user_id']}"
            oid = o["id"]
            product_name = escape_md(o.get("product_name", "N/A"))
            lines.append(
                f"🆔 `#{oid}` | {username}\n"
                f"📦 *{product_name}* x{o['quantity']} = *Rp {format_rupiah(o['total'])}*\n"
                f"📅 {o['created_at']}\n"
            )
            buttons.append([InlineKeyboardButton(f"📦 Proses #{oid}", callback_data=f"admin:preorder_process:{oid}")])

        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action.startswith("preorder_process:"):
        order_id = action.split(":")[1]
        order = db.get_order(order_id)
        if not order:
            await query.answer("Pesanan tidak ditemukan.", show_alert=True)
            return

        context.user_data["admin_state"] = f"preorder_fulfill:{order_id}"
        product = db.get_product(order.get("product_id", 1))
        product_name = escape_md(product["name"]) if product else "N/A"

        text = (
            f"📝 *PROSES PESANAN PRE-ORDER #{order_id}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Pembeli: ID `{order['user_id']}`\n"
            f"📦 Produk: *{product_name}*\n"
            f"🔢 Jumlah: {order['quantity']} akun\n"
            f"💰 Total: *Rp {format_rupiah(order['total'])}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👉 *Silakan kirimkan data produk / akun / lisensi untuk pesanan ini* (Balas dengan pesan teks atau kirim file `.txt`):"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "adminlist":
        lines = [f"{t('admin_list_title', lang)}\n"]
        for i, aid in enumerate(sorted(config.ADMIN_IDS), 1):
            is_main = " ⭐" if aid == config.ADMIN_USER_ID else ""
            lines.append(f"{i}. `{aid}`{is_main}")

        lines.append(f"\n📊 {t('admin_total', lang)}: *{len(config.ADMIN_IDS)}* {t('admins', lang)}")

        await _safe_edit_or_send(
            query,
            "\n".join(lines),
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "addproduct":
        context.user_data["admin_state"] = "addproduct_name"
        text = (
            f"{t('admin_add_product', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_send_name', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "setprice":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(
                query,
                f"{t('admin_change_price', lang)}\n\n{t('no_products', lang)}",
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        buttons = []
        for p in products:
            buttons.append([InlineKeyboardButton(
                f"💰 {p['name']} — Rp {format_rupiah(p['price'])}",
                callback_data=f"admin:spick:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            f"{t('admin_change_price', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_product', lang)}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "spick":
        if len(parts) < 3:
            return
        try:
            product_id = int(parts[2])
        except ValueError:
            return
        product = db.get_product(product_id)
        if not product:
            await _safe_edit_or_send(query, t("admin_not_found", lang, id=product_id), reply_markup=get_admin_back_keyboard(lang))
            return

        context.user_data["admin_state"] = "setprice_value"
        context.user_data["setprice_product_id"] = product_id

        text = (
            f"{t('admin_change_price', lang)} — *{escape_md(product['name'])}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_current_price', lang)}: *Rp {format_rupiah(product['price'])}*\n\n"
            f"{t('admin_send_new_price', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "broadcast":
        context.user_data["admin_state"] = "broadcast_msg"
        text = (
            f"{t('admin_broadcast', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_send_message', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "addadmin":
        context.user_data["admin_state"] = "addadmin_id"
        text = (
            f"{t('admin_add_admin', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_send_user_id', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "removeadmin":
        others = sorted(config.ADMIN_IDS - {config.ADMIN_USER_ID})
        if not others:
            await _safe_edit_or_send(
                query,
                t("admin_no_remove", lang),
                reply_markup=get_admin_back_keyboard(lang),
            )
            return

        buttons = []
        for aid in others:
            buttons.append([InlineKeyboardButton(
                f"❌ Remove {aid}",
                callback_data=f"admin:rmadmin:{aid}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back_to_admin", lang), callback_data="menu:admin")])

        await _safe_edit_or_send(
            query,
            f"{t('admin_remove_admin', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_admin', lang)}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "rmadmin":
        if len(parts) < 3:
            return
        try:
            remove_id = int(parts[2])
        except ValueError:
            return
        if remove_id == config.ADMIN_USER_ID:
            await _safe_edit_or_send(query, t("admin_cannot_remove", lang), reply_markup=get_admin_back_keyboard(lang))
            return
        config.ADMIN_IDS.discard(remove_id)
        await _safe_edit_or_send(
            query,
            f"{t('admin_removed', lang)}\n\n{t('admin_id', lang)}: `{remove_id}`\n{t('admin_total_admins', lang)}: *{len(config.ADMIN_IDS)}*",
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "addstock":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(
                query,
                t("admin_no_active_products", lang),
                reply_markup=get_admin_back_keyboard(lang),
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

        await _safe_edit_or_send(
            query,
            f"{t('admin_add_stock', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_stock_product', lang)}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "astk":
        if len(parts) < 3:
            return
        try:
            product_id = int(parts[2])
        except ValueError:
            return

        product = db.get_product(product_id)
        if not product:
            await _safe_edit_or_send(query, t("admin_not_found", lang, id=product_id), reply_markup=get_admin_back_keyboard(lang))
            return

        context.user_data["addstock_product_id"] = product_id
        context.user_data["state"] = "addstock"

        text = (
            f"{t('admin_add_stock', lang)} — *{escape_md(product['name'])}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('admin_current_stock', lang)}: *{db.get_stock_count(product_id)}* {t('accounts', lang)}\n\n"
            f"{t('admin_method1', lang)}\n\n"
            f"{t('admin_method2', lang)}\n\n"
            f"{t('admin_send_now', lang)}"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "delproduct":
        products = db.get_all_products()
        if not products:
            await _safe_edit_or_send(query, t("admin_no_products", lang), reply_markup=get_admin_back_keyboard(lang))
            return
        buttons = []
        for i, p in enumerate(products, 1):
            num_str = get_num_emoji(i)
            buttons.append([InlineKeyboardButton(
                f"🗑️ {num_str} {p['name']} (Rp {format_rupiah(p['price'])})",
                callback_data=f"admin:dprod:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(
            query,
            f"{t('btn_delete_product', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_select_delete_product', lang)}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "dprod":
        if len(parts) < 3:
            return
        try:
            product_id = int(parts[2])
        except ValueError:
            return
        product = db.get_product(product_id)
        if not product:
            await _safe_edit_or_send(query, t("admin_not_found", lang, id=product_id), reply_markup=get_admin_back_keyboard(lang))
            return

        db.delete_product(product_id)
        await _safe_edit_or_send(
            query,
            t("admin_product_deleted_success", lang, id=product_id, name=escape_md(product["name"])),
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "report":
        rep = db.get_financial_report()
        best_p = rep["best_product"]
        best_str = f"{escape_md(best_p['name'])} ({best_p['total_qty']} {t('accounts', lang)})" if best_p else "-"
        text = (
            f"{t('admin_financial_report_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 *Hari Ini*: Rp {format_rupiah(rep['today_revenue'])} ({rep['today_orders']} transaksi)\n"
            f"📆 *7 Hari Terakhir*: Rp {format_rupiah(rep['week_revenue'])} ({rep['week_orders']} transaksi)\n"
            f"🗓️ *30 Hari Terakhir*: Rp {format_rupiah(rep['month_revenue'])} ({rep['month_orders']} transaksi)\n"
            f"💰 *Total Keseluruhan*: Rp {format_rupiah(rep['total_revenue'])} ({rep['total_orders']} transaksi)\n"
            f"🏆 *Produk Terlaris*: {best_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang))

    elif action == "eprod":
        products = db.get_all_products()
        if not products:
            await _safe_edit_or_send(query, t("no_products", lang), reply_markup=get_admin_back_keyboard(lang))
            return
        buttons = []
        for i, p in enumerate(products, 1):
            status_icon = "🟢" if p["is_active"] else "🔴"
            num_str = get_num_emoji(i)
            buttons.append([InlineKeyboardButton(
                f"{status_icon} {num_str} {p['name']} (Rp {format_rupiah(p['price'])})",
                callback_data=f"admin:edetail:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(
            query,
            f"{t('admin_edit_product_title', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_edit_select_prompt', lang)}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "edetail":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if not product:
            await _safe_edit_or_send(query, t("admin_not_found", lang, id=pid), reply_markup=get_admin_back_keyboard(lang))
            return

        status_label = "🟢 Aktif" if product["is_active"] else "🔴 Nonaktif"
        toggle_btn_label = "🔴 Nonaktifkan Produk" if product["is_active"] else "🟢 Aktifkan Produk"

        text = (
            f"✏️ *KARTU EDIT PRODUK*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *ID Produk*: #{product['id']}\n"
            f"📦 *Nama*: {escape_md(product['name'])}\n"
            f"💰 *Harga*: Rp {format_rupiah(product['price'])}\n"
            f"📝 *Deskripsi*: {escape_md(product['description']) if product['description'] else '-'}\n"
            f"Status: *{status_label}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Pilih bagian yang ingin diubah:"
        )

        buttons = [
            [
                InlineKeyboardButton("📦 Ubah Nama", callback_data=f"admin:ename:{pid}"),
                InlineKeyboardButton("📝 Ubah Deskripsi", callback_data=f"admin:edesc:{pid}"),
            ],
            [
                InlineKeyboardButton("💰 Ubah Harga", callback_data=f"admin:eprice:{pid}"),
                InlineKeyboardButton(toggle_btn_label, callback_data=f"admin:etog:{pid}"),
            ],
            [
                InlineKeyboardButton("⬅️ Kembali ke Daftar Produk", callback_data="admin:eprod"),
            ],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "ename":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if product:
            context.user_data["admin_state"] = "editproduct_name"
            context.user_data["editproduct_id"] = pid
            await _safe_edit_or_send(
                query,
                t("admin_send_new_name", lang, name=escape_md(product["name"])),
                reply_markup=get_admin_back_keyboard(lang, back_data=f"admin:edetail:{pid}"),
            )

    elif action == "edesc":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if product:
            context.user_data["admin_state"] = "editproduct_desc"
            context.user_data["editproduct_id"] = pid
            await _safe_edit_or_send(
                query,
                t("admin_send_new_desc", lang, name=escape_md(product["name"])),
                reply_markup=get_admin_back_keyboard(lang, back_data=f"admin:edetail:{pid}"),
            )

    elif action == "eprice":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if product:
            context.user_data["admin_state"] = "editproduct_price"
            context.user_data["editproduct_id"] = pid
            await _safe_edit_or_send(
                query,
                t("admin_send_new_price", lang, name=escape_md(product["name"])),
                reply_markup=get_admin_back_keyboard(lang, back_data=f"admin:edetail:{pid}"),
            )

    elif action == "etog":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if product:
            new_status = 0 if product["is_active"] else 1
            db.update_product(pid, is_active=new_status)
            status_text = "🟢 Aktif" if new_status else "🔴 Nonaktif"
            await query.answer(f"Status {product['name']} diubah -> {status_text}", show_alert=True)
            product = db.get_product(pid)
            status_label = "🟢 Aktif" if product["is_active"] else "🔴 Nonaktif"
            toggle_btn_label = "🔴 Nonaktifkan Produk" if product["is_active"] else "🟢 Aktifkan Produk"

            text = (
                f"✏️ *KARTU EDIT PRODUK*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *ID Produk*: #{product['id']}\n"
                f"📦 *Nama*: {escape_md(product['name'])}\n"
                f"💰 *Harga*: Rp {format_rupiah(product['price'])}\n"
                f"📝 *Deskripsi*: {escape_md(product['description']) if product['description'] else '-'}\n"
                f"Status: *{status_label}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Pilih bagian yang ingin diubah:"
            )

            buttons = [
                [
                    InlineKeyboardButton("📦 Ubah Nama", callback_data=f"admin:ename:{pid}"),
                    InlineKeyboardButton("📝 Ubah Deskripsi", callback_data=f"admin:edesc:{pid}"),
                ],
                [
                    InlineKeyboardButton("💰 Ubah Harga", callback_data=f"admin:eprice:{pid}"),
                    InlineKeyboardButton(toggle_btn_label, callback_data=f"admin:etog:{pid}"),
                ],
                [
                    InlineKeyboardButton("⬅️ Kembali ke Daftar Produk", callback_data="admin:eprod"),
                ],
            ]
            await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "exstock":
        products = db.get_active_products()
        if not products:
            await _safe_edit_or_send(query, t("no_products", lang), reply_markup=get_admin_back_keyboard(lang))
            return
        buttons = []
        for i, p in enumerate(products, 1):
            cnt = db.get_stock_count(p["id"])
            buttons.append([InlineKeyboardButton(
                f"📤 #{i} {p['name']} ({cnt} ready)",
                callback_data=f"admin:dlex:{p['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(
            query,
            f"{t('admin_export_stock_title', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nPilih produk yang ingin di-export file stoknya:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "dlex":
        if len(parts) < 3:
            return
        try:
            pid = int(parts[2])
        except ValueError:
            return
        product = db.get_product(pid)
        if not product:
            return
        content = db.get_stock_file_content(pid)
        if not content:
            await query.answer("Stok produk ini kosong!", show_alert=True)
            return
        import io
        bio = io.BytesIO(content.encode("utf-8"))
        bio.name = f"stok_{product['name'].replace(' ', '_')}.txt"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=bio,
            caption=f"📦 Export stok ready for *{escape_md(product['name'])}*",
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.answer("File stok berhasil dikirim!")

    elif action == "search":
        context.user_data["admin_state"] = "search_order"
        await _safe_edit_or_send(
            query,
            f"{t('admin_search_order_title', lang)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{t('admin_search_order_prompt', lang)}",
            reply_markup=get_admin_back_keyboard(lang),
        )

    elif action == "settings":
        status = "🟢 AKTIF (Normal)" if not config.MAINTENANCE_MODE else "🔴 NONAKTIF (Maintenance ON)"
        btn_maint = "🔴 Aktifkan Maintenance" if not config.MAINTENANCE_MODE else "🟢 Matikan Maintenance Mode"
        text = (
            f"{t('admin_bot_settings_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status Bot: *{status}*\n\n"
            f"Ketika Maintenance Mode *ON*, pembeli tidak dapat membuat pesanan baru."
        )
        buttons = [
            [InlineKeyboardButton(btn_maint, callback_data="admin:toggle_maint")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "toggle_maint":
        config.MAINTENANCE_MODE = not config.MAINTENANCE_MODE
        status_txt = "Maintenance Mode ON" if config.MAINTENANCE_MODE else "Maintenance Mode OFF"
        await query.answer(f"Status Bot: {status_txt}", show_alert=True)
        status = "🟢 AKTIF (Normal)" if not config.MAINTENANCE_MODE else "🔴 NONAKTIF (Maintenance ON)"
        btn_maint = "🔴 Aktifkan Maintenance" if not config.MAINTENANCE_MODE else "🟢 Matikan Maintenance Mode"
        text = (
            f"{t('admin_bot_settings_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status Bot: *{status}*\n\n"
            f"Ketika Maintenance Mode *ON*, pembeli tidak dapat membuat pesanan baru."
        )
        buttons = [
            [InlineKeyboardButton(btn_maint, callback_data="admin:toggle_maint")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "users":
        users = db.get_all_users_detail(limit=20)
        if not users:
            await _safe_edit_or_send(query, t("user_mgmt_title", lang) + "\n\nBelum ada pengguna.", reply_markup=get_admin_back_keyboard(lang))
            return

        lines = [f"{t('user_mgmt_title', lang)}\n"]
        buttons = []
        for u in users[:15]:
            name = f"@{u['username']}" if u.get("username") else u.get("first_name", str(u["user_id"]))
            ban_icon = "🚫" if u.get("is_banned") else ""
            lines.append(f"{ban_icon} {name} | {u.get('total_orders', 0)} orders | Rp {format_rupiah(u.get('total_spent', 0))}")
            buttons.append([InlineKeyboardButton(
                f"👤 {name} ({u.get('total_orders', 0)} orders)",
                callback_data=f"admin:userdetail:{u['user_id']}",
            )])

        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "userdetail":
        if len(parts) < 3:
            return
        try:
            uid = int(parts[2])
        except ValueError:
            return
        user = db.get_user_detail(uid)
        if not user:
            await query.answer("User tidak ditemukan!", show_alert=True)
            return

        ban_status = f"🚫 *DIBLOKIR* - {user.get('ban_reason', '')}" if user.get("is_banned") else "✅ Aktif"
        name = f"@{user['username']}" if user.get("username") else user.get("first_name", "N/A")

        text = (
            f"{t('user_detail_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{user['user_id']}`\n"
            f"👤 Name: *{name}*\n"
            f"📊 Status: {ban_status}\n"
            f"{t('user_total_orders', lang)}: *{user.get('total_orders', 0)}*\n"
            f"{t('user_total_spent', lang)}: *Rp {format_rupiah(user.get('total_spent', 0))}*\n"
            f"{t('user_joined', lang)}: {user.get('last_seen', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        if user.get("is_banned"):
            btn_ban = InlineKeyboardButton(t("user_unban_btn", lang), callback_data=f"admin:unban:{uid}")
        else:
            btn_ban = InlineKeyboardButton(t("user_ban_btn", lang), callback_data=f"admin:ban:{uid}")

        buttons = [
            [btn_ban],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="admin:users")],
            [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "ban":
        if len(parts) < 3:
            return
        try:
            uid = int(parts[2])
        except ValueError:
            return
        context.user_data["admin_state"] = "user_ban_reason"
        context.user_data["ban_user_id"] = uid
        await _safe_edit_or_send(query, t("user_ban_reason_prompt", lang), reply_markup=get_admin_back_keyboard(lang))

    elif action == "unban":
        if len(parts) < 3:
            return
        try:
            uid = int(parts[2])
        except ValueError:
            return
        db.unban_user(uid)
        await query.answer(t("user_unbanned_success", lang, id=uid), show_alert=True)
        user = db.get_user_detail(uid)
        if user:
            ban_status = "✅ Aktif"
            name = f"@{user['username']}" if user.get("username") else user.get("first_name", "N/A")
            text = (
                f"{t('user_detail_title', lang)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 ID: `{uid}`\n"
                f"👤 Name: *{name}*\n"
                f"📊 Status: {ban_status}\n"
                f"{t('user_total_orders', lang)}: *{user.get('total_orders', 0)}*\n"
                f"{t('user_total_spent', lang)}: *Rp {format_rupiah(user.get('total_spent', 0))}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            buttons = [
                [InlineKeyboardButton(t("user_ban_btn", lang), callback_data=f"admin:ban:{uid}")],
                [InlineKeyboardButton(t("btn_back", lang), callback_data="admin:users")],
                [InlineKeyboardButton(t("btn_admin_home", lang), callback_data="menu:admin")],
            ]
            await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "feedbacklist":
        feedbacks = db.get_all_feedback(limit=20)
        if not feedbacks:
            await _safe_edit_or_send(query, t("feedback_no_items", lang), reply_markup=get_admin_back_keyboard(lang))
            return

        lines = [f"{t('admin_feedback_list', lang)}\n"]
        buttons = []
        for fb in feedbacks[:10]:
            status_icon = "✅" if fb["status"] == "replied" else "⚪" if fb["status"] == "closed" else "🔵"
            cat = fb.get("category", "lainnya")
            lines.append(f"{status_icon} #{fb['id']} | @{fb.get('username', '?')} | {cat}")
            buttons.append([InlineKeyboardButton(
                f"{status_icon} #{fb['id']} - @{fb.get('username', '?')} ({cat})",
                callback_data=f"admin:fbdetail:{fb['id']}",
            )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "fbdetail":
        if len(parts) < 3:
            return
        try:
            fid = int(parts[2])
        except ValueError:
            return
        feedbacks = db.get_all_feedback()
        fb = next((x for x in feedbacks if x["id"] == fid), None)
        if not fb:
            await query.answer("Feedback tidak ditemukan!", show_alert=True)
            return

        status_icon = "✅" if fb["status"] == "replied" else "⚪" if fb["status"] == "closed" else "🔵"
        text = (
            f"💬 *FEEDBACK #{fb['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 @{fb.get('username', '?')} (ID: `{fb['user_id']}`)\n"
            f"📂 Kategori: *{fb.get('category', '-')}*\n"
            f"Status: {status_icon} *{fb['status'].upper()}*\n"
            f"📅 {fb.get('created_at', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 *Pesan:*\n{fb['message']}\n"
        )
        if fb.get("admin_reply"):
            text += f"\n💬 *Balasan Admin:*\n{fb['admin_reply']}\n"

        buttons = []
        if fb["status"] != "replied":
            buttons.append([InlineKeyboardButton("💬 Reply", callback_data=f"admin:fbreply:{fid}")])
        buttons.append([InlineKeyboardButton("🔒 Close", callback_data=f"admin:fbclose:{fid}")])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="admin:feedbacklist")])
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "fbreply":
        if len(parts) < 3:
            return
        try:
            fid = int(parts[2])
        except ValueError:
            return
        context.user_data["admin_state"] = "feedback_reply"
        context.user_data["feedback_reply_id"] = fid
        await _safe_edit_or_send(query, t("feedback_reply_prompt", lang), reply_markup=get_admin_back_keyboard(lang))

    elif action == "fbclose":
        if len(parts) < 3:
            return
        try:
            fid = int(parts[2])
        except ValueError:
            return
        db.close_feedback(fid)
        await query.answer("Feedback ditutup!", show_alert=True)
        await handle_admin_button(update, context)

    elif action == "commission":
        pct = db.get_commission_percent()
        min_wd = db.get_min_withdrawal()
        text = (
            f"{t('admin_commission_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('admin_commission_rate', lang)}: *{pct}%*\n"
            f"{t('admin_min_withdrawal', lang)}: *Rp {format_rupiah(min_wd)}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [InlineKeyboardButton(f"📊 {t('admin_set_commission', lang)} ({pct}%)", callback_data="admin:setcommission")],
            [InlineKeyboardButton(f"💸 {t('admin_set_min_withdraw', lang)} (Rp {format_rupiah(min_wd)})", callback_data="admin:setminwithdraw")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")],
        ]
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "setcommission":
        context.user_data["admin_state"] = "setcommission"
        text = (
            f"{t('admin_commission_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Kirimkan persentase komisi baru (1-50):"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang, back_data="admin:commission"))

    elif action == "setminwithdraw":
        context.user_data["admin_state"] = "setminwithdraw"
        text = (
            f"{t('admin_commission_title', lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Kirimkan jumlah minimal pencairan baru (minimal Rp 10.000):"
        )
        await _safe_edit_or_send(query, text, reply_markup=get_admin_back_keyboard(lang, back_data="admin:commission"))

    elif action == "withdrawals":
        withdrawals = db.get_pending_withdrawals()
        lines = [f"{t('admin_withdrawal_title', lang)}\n"]
        buttons = []
        if not withdrawals:
            lines.append(f"\n{t('admin_no_withdrawals', lang)}")
        else:
            for w in withdrawals[:10]:
                name = f"@{w['username']}" if w.get("username") else w.get("first_name", str(w["user_id"]))
                lines.append(
                    f"💸 #{w['id']} | {name} | Rp {format_rupiah(w['amount'])} | {w.get('bank_name', '-')}"
                )
                buttons.append([InlineKeyboardButton(
                    f"💸 #{w['id']} - {name} - Rp {format_rupiah(w['amount'])}",
                    callback_data=f"admin:wddetail:{w['id']}",
                )])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu:admin")])
        await _safe_edit_or_send(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "wddetail":
        if len(parts) < 3:
            return
        try:
            wd_id = int(parts[2])
        except ValueError:
            return
        wd = db.get_withdrawal_request(wd_id)
        if not wd:
            await query.answer("Withdrawal tidak ditemukan!", show_alert=True)
            return

        name = f"@{wd['username']}" if wd.get("username") else wd.get("first_name", str(wd["user_id"]))
        status_map = {"pending": "⏳ Pending", "approved": "✅ Approved", "rejected": "❌ Rejected"}
        status_label = status_map.get(wd["status"], wd["status"])

        text = t("admin_withdraw_detail", lang,
            id=wd_id, name=name, user_id=wd["user_id"],
            bank=wd.get("bank_name", "-"), account=wd.get("account_number", "-"),
            acc_name=wd.get("account_name", "-"), amount=format_rupiah(wd["amount"]),
            status=status_label, date=wd.get("created_at", "-"))

        buttons = []
        if wd["status"] == "pending":
            buttons.append([
                InlineKeyboardButton(t("admin_approve_withdraw", lang), callback_data=f"admin:wdapprove:{wd_id}"),
                InlineKeyboardButton(t("admin_reject_withdraw", lang), callback_data=f"admin:wdreject:{wd_id}"),
            ])
        buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="admin:withdrawals")])
        await _safe_edit_or_send(query, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "wdapprove":
        if len(parts) < 3:
            return
        try:
            wd_id = int(parts[2])
        except ValueError:
            return
        wd = db.get_withdrawal_request(wd_id)
        if not wd or wd["status"] != "pending":
            await query.answer("Withdrawal tidak valid!", show_alert=True)
            return

        db.process_withdrawal(wd_id, "approved", "Approved by admin")
        try:
            user_lang = db.get_user_lang(wd["user_id"])
            await context.bot.send_message(
                chat_id=wd["user_id"],
                text=t("withdraw_approved_notif", user_lang, id=wd_id, amount=format_rupiah(wd["amount"])),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

        await query.answer(f"✅ Withdrawal #{wd_id} approved!", show_alert=True)
        await handle_admin_button(update, context)

    elif action == "wdreject":
        if len(parts) < 3:
            return
        try:
            wd_id = int(parts[2])
        except ValueError:
            return
        wd = db.get_withdrawal_request(wd_id)
        if not wd or wd["status"] != "pending":
            await query.answer("Withdrawal tidak valid!", show_alert=True)
            return

        db.process_withdrawal(wd_id, "rejected", "Rejected by admin")
        try:
            user_lang = db.get_user_lang(wd["user_id"])
            await context.bot.send_message(
                chat_id=wd["user_id"],
                text=t("withdraw_rejected_notif", user_lang, id=wd_id, reason="Ditolak oleh admin"),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

        await query.answer(f"❌ Withdrawal #{wd_id} rejected!", show_alert=True)
        await handle_admin_button(update, context)

    elif action == "apv":
        if len(parts) < 3:
            return
        order_id = parts[2]
        order = db.get_order(order_id)
        if not order:
            await query.answer("Pesanan tidak ditemukan!", show_alert=True)
            return
        if order["status"] == "paid":
            await query.answer("Pesanan ini sudah dibayar!", show_alert=True)
            return

        product_id = order.get("product_id", 1)
        items = db.take_stock(order_id, order["quantity"], product_id)
        if not items:
            await query.answer("⚠️ Stok produk tidak cukup!", show_alert=True)
            return

        db.update_order_status(order_id, "paid")
        product = db.get_product(product_id)
        product_name = product["name"] if product else "Produk"
        buyer_lang = db.get_user_lang(order["user_id"])

        product_desc = (product.get("description") or "").strip() if product else ""
        txt_lines = []
        if product_desc:
            txt_lines.append("==================================================")
            txt_lines.append(f"CATATAN / PANDUAN PENGGUNAAN ({product_name}):")
            txt_lines.append(product_desc)
            txt_lines.append("==================================================\n")

        for item in items:
            em = item.get("email", "")
            pw = item.get("password", "")
            bal = item.get("balance", "")
            if pw and bal:
                txt_lines.append(f"{em}:{pw}:{bal}")
            elif pw:
                txt_lines.append(f"{em}:{pw}")
            else:
                txt_lines.append(f"{em}")

        doc_content = "\n".join(txt_lines)

        import io
        file_bytes = io.BytesIO(doc_content.encode("utf-8"))
        file_bytes.name = f"akun_{order_id}.txt"

        caption = (
            f"{t('payment_success', buyer_lang)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('order_label', buyer_lang)}: #{order_id}\n"
            f"{t('product_label', buyer_lang)}: {escape_md(product_name)}\n"
            f"{t('quantity_label_short', buyer_lang)}: {order['quantity']} {t('accounts', buyer_lang)}\n"
            f"{t('total_label', buyer_lang)}: Rp {format_rupiah(order['total'])}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t('file_attached', buyer_lang)}"
        )

        try:
            await context.bot.send_document(
                chat_id=order["user_id"],
                document=file_bytes,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard(order["user_id"], buyer_lang),
            )
        except Exception as err:
            logger.exception("Failed to send document to buyer %s: %s", order["user_id"], err)

        qris_msg_id = order.get("qris_message_id")
        if qris_msg_id:
            try:
                await context.bot.delete_message(chat_id=order["user_id"], message_id=qris_msg_id)
            except Exception:
                pass

        try:
            await send_channel_purchase_notif(context.bot, order, product_name)
        except Exception as err:
            logger.warning("Failed to send channel purchase notif: %s", err)

        # --- Apply referral commission ---
        try:
            buyer_user = db._conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (order["user_id"],)).fetchone()
            if buyer_user and buyer_user["referred_by"]:
                referrer_id = buyer_user["referred_by"]
                if not db.has_commission_for_order(order_id):
                    commission_pct = db.get_commission_percent()
                    order_amount = order.get("total", 0)
                    commission_amount = int(order_amount * commission_pct / 100)
                    if commission_amount > 0:
                        db.add_commission(referrer_id, order["user_id"], order_id, order_amount, commission_pct, commission_amount)
                        try:
                            referrer_lang = db.get_user_lang(referrer_id)
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=t("commission_notif", referrer_lang,
                                    amount=format_rupiah(commission_amount),
                                    name=order.get("first_name") or order.get("username") or str(order["user_id"]),
                                    order_id=order_id),
                                parse_mode=ParseMode.MARKDOWN,
                            )
                        except Exception:
                            pass
        except Exception as exc:
            logger.exception("Admin approve commission failed for order %s: %s", order_id, exc)

        await query.answer(f"✅ Order #{order_id} berhasil di-approve!", show_alert=True)
        await _safe_edit_or_send(query, f"✅ *Pesanan #{order_id} BERHASIL DI-APPROVE!*\n\nProduk telah dikirimkan ke pembeli.", reply_markup=get_admin_back_keyboard(lang))



