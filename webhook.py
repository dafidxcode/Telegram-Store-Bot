"""FastAPI webhook server + Full Web Admin Dashboard backend.

Jalankan dengan: python webhook.py
Atau gunakan bot.py mode webhook.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import config
import db
from handlers.start import t, format_rupiah, escape_md, get_main_menu_keyboard

logger = logging.getLogger(__name__)

app = FastAPI(title="Viintools Admin")

assets_dir = Path(__file__).parent / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Admin session store (token -> telegram_user_id)
_admin_sessions: dict[str, int] = {}


def _get_admin_token(telegram_id: int) -> str:
    raw = f"{telegram_id}-{config.BOT_TOKEN[:10]}-{config.ADMIN_AUTH}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


@app.on_event("startup")
async def startup():
    db.init_db(config.DB_PATH)
    logger.info("Dashboard DB initialized at %s", config.DB_PATH)


# ---------------------------------------------------------------------------
# Auth Helper
# ---------------------------------------------------------------------------

async def _verify_admin(request: Request) -> int:
    token = request.cookies.get("admin_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token or token not in _admin_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_id = _admin_sessions[token]
    if admin_id not in config.ADMIN_IDS and admin_id != config.ADMIN_USER_ID:
        raise HTTPException(status_code=403, detail="Forbidden")
    return admin_id


# ---------------------------------------------------------------------------
# Dashboard Web UI Route
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    html_path = Path(__file__).parent / "templates" / "admin.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>templates/admin.html not found</h1>", status_code=404)


# ---------------------------------------------------------------------------
# Authentication APIs
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
async def api_auth_login(request: Request, response: Response):
    try:
        body = await request.json()
    except Exception:
        body = {}

    password = str(body.get("password", "")).strip()

    if not password or password != config.ADMIN_AUTH:
        return JSONResponse(status_code=401, content={"error": "Password ADMIN_AUTH salah!"})

    user_id = config.ADMIN_USER_ID
    token = _get_admin_token(user_id)
    _admin_sessions[token] = user_id

    res = JSONResponse(content={"success": True, "token": token, "user_id": user_id})
    res.set_cookie(key="admin_token", value=token, httponly=True, max_age=86400 * 7, path="/")
    return res


@app.post("/api/auth/logout")
async def api_auth_logout(request: Request, response: Response):
    token = request.cookies.get("admin_token")
    if token and token in _admin_sessions:
        del _admin_sessions[token]
    res = JSONResponse(content={"success": True})
    res.delete_cookie("admin_token", path="/")
    return res


@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    user_id = await _verify_admin(request)
    return {
        "user_id": user_id,
        "is_main_admin": user_id == config.ADMIN_USER_ID,
        "shop_name": config.SHOP_NAME,
        "maintenance_mode": config.MAINTENANCE_MODE,
    }


# ---------------------------------------------------------------------------
# Dashboard Overview & Stats APIs
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
async def api_dashboard_summary(request: Request):
    await _verify_admin(request)

    stock = db.get_stock_count()
    users = db.get_all_user_ids()
    orders = db.get_all_orders(limit=100)
    rep = db.get_financial_report()

    pending = len([o for o in orders if o.get("status") == "pending"])
    paid = len([o for o in orders if o.get("status") == "paid"])
    delivered = len([o for o in orders if o.get("status") == "delivered"])
    cancelled = len([o for o in orders if o.get("status") == "cancelled"])

    products = db.get_all_products()

    return {
        "stock": stock,
        "total_users": len(users),
        "total_orders": len(orders),
        "total_sold": db.get_total_sold(),
        "pending": pending,
        "paid": paid,
        "delivered": delivered,
        "cancelled": cancelled,
        "revenue": rep,
        "product_count": len(products),
        "active_product_count": len([p for p in products if p.get("is_active")]),
        "maintenance_mode": config.MAINTENANCE_MODE,
        "shop_name": config.SHOP_NAME,
    }


# ---------------------------------------------------------------------------
# Products Management APIs
# ---------------------------------------------------------------------------

@app.get("/api/products")
async def api_get_products(request: Request):
    await _verify_admin(request)
    products = db.get_all_products()
    result = []
    for p in products:
        p_dict = dict(p)
        p_dict["stock_count"] = db.get_stock_count(p["id"]) if p["stock_type"] == "limited" else "∞"
        result.append(p_dict)
    return {"products": result}


@app.post("/api/products/add")
async def api_add_product(request: Request):
    await _verify_admin(request)
    body = await request.json()
    name = str(body.get("name", "")).strip()
    price = int(body.get("price", 0))
    desc = str(body.get("description", "")).strip()
    stock_type = str(body.get("stock_type", "limited")).strip()

    if not name or price <= 0:
        return JSONResponse(status_code=400, content={"error": "Nama dan harga produk tidak valid!"})

    pid = db.add_product(name=name, description=desc, price=price, stock_type=stock_type)
    return {"success": True, "product_id": pid}


@app.post("/api/products/{pid}/update")
async def api_update_product(pid: int, request: Request):
    await _verify_admin(request)
    body = await request.json()

    name = body.get("name")
    price = body.get("price")
    description = body.get("description")
    is_active = body.get("is_active")

    kwargs = {}
    if name is not None:
        kwargs["name"] = str(name).strip()
    if price is not None:
        kwargs["price"] = int(price)
    if description is not None:
        kwargs["description"] = str(description).strip()
    if is_active is not None:
        kwargs["is_active"] = int(is_active)

    db.update_product(pid, **kwargs)
    return {"success": True}


@app.delete("/api/products/{pid}")
async def api_delete_product(pid: int, request: Request):
    await _verify_admin(request)
    product = db.get_product(pid)
    if not product:
        return JSONResponse(status_code=404, content={"error": "Produk tidak ditemukan"})
    db.delete_product(pid)
    return {"success": True}


# ---------------------------------------------------------------------------
# Stock Management APIs
# ---------------------------------------------------------------------------

@app.get("/api/stock")
async def api_get_stock_summary(request: Request):
    await _verify_admin(request)
    products = db.get_active_products()
    summary = []
    total = 0
    for p in products:
        cnt = db.get_stock_count(p["id"])
        total += cnt
        summary.append({
            "product_id": p["id"],
            "product_name": p["name"],
            "count": cnt,
            "price": p["price"],
        })
    return {"total": total, "products": summary}


@app.post("/api/stock/add")
async def api_add_stock(request: Request):
    await _verify_admin(request)
    body = await request.json()
    pid = int(body.get("product_id", 1))
    text = str(body.get("text", "")).strip()

    if not text:
        return JSONResponse(status_code=400, content={"error": "Teks stok kosong!"})

    lines = text.splitlines()
    count = db.add_stock_batch(lines, product_id=pid)
    stock = db.get_stock_count(pid)
    return {"success": True, "added": count, "total_product_stock": stock}


@app.get("/api/stock/export/{pid}")
async def api_export_stock(pid: int, request: Request):
    await _verify_admin(request)
    product = db.get_product(pid)
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

    content = db.get_stock_file_content(pid)
    filename = f"stok_{product['name'].replace(' ', '_')}.txt"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Orders & Financial Reports APIs
# ---------------------------------------------------------------------------

@app.get("/api/orders")
async def api_get_orders(request: Request, status: Optional[str] = None, query: Optional[str] = None, limit: int = 100):
    await _verify_admin(request)
    if query:
        orders = db.search_orders(query)
    else:
        orders = db.get_all_orders(limit=limit, status=status)
    return {"orders": orders}


@app.post("/api/orders/{order_id}/approve")
async def api_approve_order(order_id: str, request: Request):
    await _verify_admin(request)
    order = db.get_order(order_id)
    if not order:
        return JSONResponse(status_code=404, content={"error": "Order tidak ditemukan"})

    if order.get("status") == "paid":
        return JSONResponse(content={"success": True, "message": "Order sudah berstatus PAID sebelumnya"})

    db.update_order_status(order_id, "paid")

    delivered_count = 0
    try:
        from telegram import Bot
        quantity = order["quantity"]
        product_id = order.get("product_id", 1)
        user_id = order["user_id"]
        user_lang = db.get_user_lang(user_id)
        product = db.get_product(product_id)
        product_name = product["name"] if product else "N/A"

        stock_items = db.take_stock(order_id, quantity, product_id=product_id)
        delivered_count = len(stock_items)
        if stock_items:
            product_desc = (product.get("description") or "").strip() if product else ""
            txt_content = ""
            if product_desc:
                txt_content += f"==================================================\n"
                txt_content += f"CATATAN / PANDUAN PENGGUNAAN ({product_name}):\n"
                txt_content += f"{product_desc}\n"
                txt_content += f"==================================================\n\n"

            for item in stock_items:
                em = item.get("email", "")
                pw = item.get("password", "")
                bal = item.get("balance", "")
                if pw and bal:
                    txt_content += f"{em}:{pw}:{bal}\n"
                elif pw:
                    txt_content += f"{em}:{pw}\n"
                else:
                    txt_content += f"{em}\n"

            txt_bytes = txt_content.encode("utf-8")
            txt_file = io.BytesIO(txt_bytes)
            txt_file.name = f"accounts_{order_id}.txt"
            bot = Bot(token=config.BOT_TOKEN)

            caption = (
                f"{t('payment_success', user_lang)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{t('order_label', user_lang)}: #{order_id}\n"
                f"{t('product_label', user_lang)}: {escape_md(product_name)}\n"
                f"{t('quantity_label_short', user_lang)}: {quantity} {t('accounts', user_lang)}\n"
                f"{t('total_label', user_lang)}: Rp {format_rupiah(order.get('total', 0))}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{t('file_attached', user_lang)}"
            )

            await bot.send_document(
                chat_id=user_id,
                document=txt_file,
                caption=caption,
                reply_markup=get_main_menu_keyboard(user_id, user_lang),
            )

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

        # --- Apply referral commission ---
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
        except Exception as exc:
            logger.exception("Admin approve commission failed for order %s: %s", order_id, exc)
    except Exception as e:
        logger.exception("Failed to deliver accounts in admin approve: %s", e)

    return {"success": True, "delivered_accounts": delivered_count}


@app.post("/api/orders/{order_id}/cancel")
async def api_cancel_order(order_id: str, request: Request):
    await _verify_admin(request)
    order = db.get_order(order_id)
    if not order:
        return JSONResponse(status_code=404, content={"error": "Order tidak ditemukan"})

    db.update_order_status(order_id, "cancelled")
    released = db.release_stock(order_id)
    return {"success": True, "released_stock": released}


# ---------------------------------------------------------------------------
# Settings & Admin Management APIs
# ---------------------------------------------------------------------------

@app.post("/api/settings/maintenance")
async def api_toggle_maintenance(request: Request):
    await _verify_admin(request)
    body = await request.json()
    enabled = bool(body.get("enabled", False))
    config.MAINTENANCE_MODE = enabled
    return {"success": True, "maintenance_mode": config.MAINTENANCE_MODE}


@app.post("/api/broadcast")
async def api_send_broadcast(request: Request):
    await _verify_admin(request)
    body = await request.json()
    message_text = str(body.get("message", "")).strip()

    if not message_text:
        return JSONResponse(status_code=400, content={"error": "Pesan broadcast tidak boleh kosong!"})

    user_ids = db.get_all_user_ids()
    sent_cnt = 0
    failed_cnt = 0

    try:
        from telegram import Bot
        bot = Bot(token=config.BOT_TOKEN)
        for uid in user_ids:
            try:
                await bot.send_message(chat_id=uid, text=message_text, parse_mode="Markdown")
                sent_cnt += 1
            except Exception:
                failed_cnt += 1
    except Exception as e:
        logger.exception("Broadcast failed: %s", e)

    return {"success": True, "sent": sent_cnt, "failed": failed_cnt, "total": len(user_ids)}


@app.get("/api/admins")
async def api_get_admins(request: Request):
    await _verify_admin(request)
    return {"main_admin": config.ADMIN_USER_ID, "admins": list(config.ADMIN_IDS)}


@app.post("/api/admins/add")
async def api_add_admin(request: Request):
    await _verify_admin(request)
    body = await request.json()
    new_admin_id = body.get("telegram_id")
    if new_admin_id:
        try:
            config.ADMIN_IDS.add(int(new_admin_id))
            return {"success": True, "admins": list(config.ADMIN_IDS)}
        except ValueError:
            pass
    return JSONResponse(status_code=400, content={"error": "Telegram ID tidak valid"})


@app.post("/api/admins/remove")
async def api_remove_admin(request: Request):
    await _verify_admin(request)
    body = await request.json()
    remove_id = body.get("telegram_id")
    if remove_id:
        try:
            rid = int(remove_id)
            if rid == config.ADMIN_USER_ID:
                return JSONResponse(status_code=400, content={"error": "Tidak dapat menghapus Main Admin"})
            config.ADMIN_IDS.discard(rid)
            return {"success": True, "admins": list(config.ADMIN_IDS)}
        except ValueError:
            pass
    return JSONResponse(status_code=400, content={"error": "Telegram ID tidak valid"})


# ---------------------------------------------------------------------------
# Webhook endpoint for KlikQRIS
# ---------------------------------------------------------------------------

@app.post("/webhook/klikqris")
async def klikqris_webhook(request: Request):
    body = await request.json()
    logger.info("KlikQRIS webhook: %s", json.dumps(body))

    order_id = body.get("order_id") or body.get("merchant_order_id")
    raw_status = body.get("status") or body.get("payment_status") or ""
    status = str(raw_status).strip().upper()

    if order_id and status:
        existing = db.get_order(order_id)
        if existing and existing.get("status") == "paid":
            logger.info("Order %s already PAID, ignoring duplicate webhook", order_id)
        elif status in ("PAID", "SUCCESS"):
            db.update_order_status(order_id, "paid")
            logger.info("Order %s marked PAID via webhook", order_id)

            try:
                from telegram import Bot
                order = db.get_order(order_id)
                if order:
                    quantity = order["quantity"]
                    product_id = order.get("product_id", 1)
                    user_id = order["user_id"]
                    user_lang = db.get_user_lang(user_id)
                    product = db.get_product(product_id)
                    product_name = product["name"] if product else "N/A"

                    stock_items = db.take_stock(order_id, quantity, product_id=product_id)
                    if stock_items:
                        txt_content = ""
                        for item in stock_items:
                            em = item.get("email", "")
                            pw = item.get("password", "")
                            bal = item.get("balance", "")
                            if pw and bal:
                                txt_content += f"{em}:{pw}:{bal}\n"
                            elif pw:
                                txt_content += f"{em}:{pw}\n"
                            else:
                                txt_content += f"{em}\n"
                        txt_bytes = txt_content.encode("utf-8")
                        txt_file = io.BytesIO(txt_bytes)
                        txt_file.name = f"accounts_{order_id}.txt"
                        bot = Bot(token=config.BOT_TOKEN)

                        caption = (
                            f"{t('payment_success', user_lang)}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"{t('order_label', user_lang)}: #{order_id}\n"
                            f"{t('product_label', user_lang)}: {escape_md(product_name)}\n"
                            f"{t('quantity_label_short', user_lang)}: {quantity} {t('accounts', user_lang)}\n"
                            f"{t('total_label', user_lang)}: Rp {format_rupiah(order.get('total', 0))}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"{t('file_attached', user_lang)}"
                        )

                        await bot.send_document(
                            chat_id=user_id,
                            document=txt_file,
                            caption=caption,
                            reply_markup=get_main_menu_keyboard(user_id, user_lang),
                        )
                        logger.info("Webhook delivered %d accounts for %s", len(stock_items), order_id)

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
                            logger.warning("Webhook channel purchase notif failed: %s", e)

                    # --- Apply referral commission ---
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
                                    logger.info("Webhook commission Rp %d applied for referrer %s from order %s", commission_amount, referrer_id, order_id)
                    except Exception as exc:
                        logger.exception("Webhook commission failed for order %s: %s", order_id, exc)
            except Exception as e:
                logger.exception("Webhook delivery failed for %s: %s", order_id, e)

        elif status in ("EXPIRED", "FAILED", "CANCELLED"):
            db.update_order_status(order_id, "cancelled")
            released = db.release_stock(order_id)
            logger.info("Order %s cancelled via webhook (%s), released %d stock", order_id, status, released)

    return {"status": "ok"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "bot": config.SHOP_NAME}


# ---------------------------------------------------------------------------
# User Management APIs
# ---------------------------------------------------------------------------

@app.get("/api/users")
async def api_get_users(request: Request, query: Optional[str] = None, limit: int = 100):
    await _verify_admin(request)
    if query:
        users = db.search_users(query)
    else:
        users = db.get_all_users_detail(limit=limit)
    return {"users": users}


@app.get("/api/users/{user_id}")
async def api_get_user_detail(user_id: int, request: Request):
    await _verify_admin(request)
    user = db.get_user_detail(user_id)
    if not user:
        return JSONResponse(status_code=404, content={"error": "User tidak ditemukan"})
    orders = db.get_user_orders(user_id)
    return {"user": user, "orders": orders}


@app.post("/api/users/{user_id}/ban")
async def api_ban_user(user_id: int, request: Request):
    await _verify_admin(request)
    body = await request.json()
    reason = str(body.get("reason", "")).strip()
    db.ban_user(user_id, reason)
    return {"success": True}


@app.post("/api/users/{user_id}/unban")
async def api_unban_user(user_id: int, request: Request):
    await _verify_admin(request)
    db.unban_user(user_id)
    return {"success": True}


# ---------------------------------------------------------------------------
# Voucher Management APIs
# ---------------------------------------------------------------------------

@app.get("/api/vouchers")
async def api_get_vouchers(request: Request):
    await _verify_admin(request)
    vouchers = db.get_all_vouchers()
    return {"vouchers": vouchers}


@app.post("/api/vouchers/add")
async def api_add_voucher(request: Request):
    await _verify_admin(request)
    body = await request.json()
    code = str(body.get("code", "")).strip().upper()
    discount_type = str(body.get("discount_type", "fixed")).strip()
    discount_value = int(body.get("discount_value", 0))
    min_purchase = int(body.get("min_purchase", 0))
    max_uses = int(body.get("max_uses", 0))

    if not code or discount_value <= 0:
        return JSONResponse(status_code=400, content={"error": "Data voucher tidak valid"})

    existing = db.get_voucher(code)
    if existing:
        return JSONResponse(status_code=400, content={"error": "Kode voucher sudah ada"})

    vid = db.create_voucher(code, discount_type, discount_value, min_purchase, max_uses)
    return {"success": True, "voucher_id": vid}


@app.post("/api/vouchers/{vid}/toggle")
async def api_toggle_voucher(vid: int, request: Request):
    await _verify_admin(request)
    db.toggle_voucher(vid)
    return {"success": True}


@app.delete("/api/vouchers/{vid}")
async def api_delete_voucher(vid: int, request: Request):
    await _verify_admin(request)
    db.delete_voucher(vid)
    return {"success": True}


# ---------------------------------------------------------------------------
# Feedback APIs
# ---------------------------------------------------------------------------

@app.get("/api/feedback")
async def api_get_feedback(request: Request, status: Optional[str] = None):
    await _verify_admin(request)
    feedbacks = db.get_all_feedback(status=status)
    return {"feedback": feedbacks}


@app.post("/api/feedback/{fid}/reply")
async def api_reply_feedback(fid: int, request: Request):
    await _verify_admin(request)
    body = await request.json()
    reply_text = str(body.get("reply", "")).strip()
    if not reply_text:
        return JSONResponse(status_code=400, content={"error": "Balasan kosong"})

    fb = db.get_all_feedback()
    fb_item = next((f for f in fb if f["id"] == fid), None)
    if not fb_item:
        return JSONResponse(status_code=404, content={"error": "Feedback tidak ditemukan"})

    db.reply_feedback(fid, reply_text)

    try:
        from telegram import Bot
        bot = Bot(token=config.BOT_TOKEN)
        await bot.send_message(
            chat_id=fb_item["user_id"],
            text=f"💬 *Balasan Admin*\n\nFeedback Anda telah ditinjau:\n\n{reply_text}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Failed to send feedback reply: %s", e)

    return {"success": True}


@app.post("/api/feedback/{fid}/close")
async def api_close_feedback(fid: int, request: Request):
    await _verify_admin(request)
    db.close_feedback(fid)
    return {"success": True}


# ---------------------------------------------------------------------------
# Purchase Detail APIs
# ---------------------------------------------------------------------------

@app.get("/api/purchases/{order_id}")
async def api_get_purchase_detail(order_id: str, request: Request):
    await _verify_admin(request)
    detail = db.get_purchase_detail(order_id)
    order = db.get_order(order_id)
    return {"detail": detail, "order": order}


# ---------------------------------------------------------------------------
# Channel Settings APIs
# ---------------------------------------------------------------------------

@app.get("/api/settings/channel")
async def api_get_channel_settings(request: Request):
    await _verify_admin(request)
    return {
        "channel_id": config.get_channel_id(),
        "channel_link": config.get_channel_link(),
    }


@app.post("/api/settings/channel")
async def api_set_channel_settings(request: Request):
    await _verify_admin(request)
    body = await request.json()
    cid = body.get("channel_id")
    clink = body.get("channel_link")

    if cid is not None:
        db.set_setting("channel_id", str(cid).strip())
    if clink is not None:
        db.set_setting("channel_link", str(clink).strip())

    return {
        "success": True,
        "channel_id": config.get_channel_id(),
        "channel_link": config.get_channel_link(),
    }


# ---------------------------------------------------------------------------
# Commission Settings APIs
# ---------------------------------------------------------------------------

@app.get("/api/settings/commission")
async def api_get_commission_settings(request: Request):
    await _verify_admin(request)
    return {
        "commission_percent": db.get_commission_percent(),
        "min_withdrawal": db.get_min_withdrawal(),
    }


@app.post("/api/settings/commission")
async def api_set_commission_settings(request: Request):
    await _verify_admin(request)
    body = await request.json()
    pct = body.get("commission_percent")
    min_wd = body.get("min_withdrawal")

    if pct is not None:
        pct = int(pct)
        if 1 <= pct <= 50:
            db.set_setting("commission_percent", str(pct))
    if min_wd is not None:
        min_wd = int(min_wd)
        if min_wd >= 10000:
            db.set_setting("min_withdrawal", str(min_wd))

    return {
        "success": True,
        "commission_percent": db.get_commission_percent(),
        "min_withdrawal": db.get_min_withdrawal(),
    }


# ---------------------------------------------------------------------------
# Withdrawal Management APIs
# ---------------------------------------------------------------------------

@app.get("/api/withdrawals")
async def api_get_withdrawals(request: Request, status: Optional[str] = None):
    await _verify_admin(request)
    if status == "pending":
        withdrawals = db.get_pending_withdrawals()
    else:
        withdrawals = db.get_all_withdrawals()
    return {"withdrawals": withdrawals}


@app.post("/api/withdrawals/{wd_id}/approve")
async def api_approve_withdrawal(wd_id: int, request: Request):
    await _verify_admin(request)
    wd = db.get_withdrawal_request(wd_id)
    if not wd:
        return JSONResponse(status_code=404, content={"error": "Withdrawal tidak ditemukan"})
    if wd["status"] != "pending":
        return JSONResponse(status_code=400, content={"error": "Withdrawal sudah diproses"})

    db.process_withdrawal(wd_id, "approved", "Approved via dashboard")

    try:
        from telegram import Bot
        bot = Bot(token=config.BOT_TOKEN)
        user_lang = db.get_user_lang(wd["user_id"])
        await bot.send_message(
            chat_id=wd["user_id"],
            text=t("withdraw_approved_notif", user_lang, id=wd_id, amount=format_rupiah(wd["amount"])),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Failed to notify user about approved withdrawal: %s", e)

    return {"success": True}


@app.post("/api/withdrawals/{wd_id}/reject")
async def api_reject_withdrawal(wd_id: int, request: Request):
    await _verify_admin(request)
    body = await request.json()
    reason = str(body.get("reason", "Ditolak oleh admin")).strip()

    wd = db.get_withdrawal_request(wd_id)
    if not wd:
        return JSONResponse(status_code=404, content={"error": "Withdrawal tidak ditemukan"})
    if wd["status"] != "pending":
        return JSONResponse(status_code=400, content={"error": "Withdrawal sudah diproses"})

    db.process_withdrawal(wd_id, "rejected", reason)

    try:
        from telegram import Bot
        bot = Bot(token=config.BOT_TOKEN)
        user_lang = db.get_user_lang(wd["user_id"])
        await bot.send_message(
            chat_id=wd["user_id"],
            text=t("withdraw_rejected_notif", user_lang, id=wd_id, reason=reason),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Failed to notify user about rejected withdrawal: %s", e)

    return {"success": True}


def run_webhook():
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info("Starting webhook server on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_webhook()
