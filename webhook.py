"""FastAPI webhook server + admin dashboard.

Jalankan dengan: python webhook.py
Atau gunakan bot.py mode webhook.
"""

import hashlib
import hmac
import json
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
import db

logger = logging.getLogger(__name__)

app = FastAPI(title="SWD x Videogen Bot Dashboard")

# Admin session store (simple token-based)
_admin_sessions: dict[str, int] = {}  # token -> telegram_user_id


def _get_admin_token(telegram_id: int) -> str:
    raw = f"{telegram_id}-{config.BOT_TOKEN[:10]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@app.on_event("startup")
async def startup():
    db.init_db(config.DB_PATH)
    logger.info("Dashboard DB initialized")


# ---------------------------------------------------------------------------
# Auth middleware - check Telegram user ID
# ---------------------------------------------------------------------------

async def _verify_admin(request: Request) -> int:
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    admin_id = _admin_sessions.get(token)
    if admin_id is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    if admin_id not in config.ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Not admin")
    return admin_id


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    token = request.cookies.get("admin_token")
    if token and _admin_sessions.get(token) in config.ADMIN_IDS:
        html_path = Path(__file__).parent / "templates" / "admin.html"
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

    # Login page
    return HTMLResponse(content=_login_page())


@app.get("/admin/login/{token}")
async def admin_login(token: str):
    """Login via Telegram bot deep link."""
    admin_id = _admin_sessions.pop(f"pending:{token}", None)
    if admin_id is None:
        return HTMLResponse(content="<h1>Invalid or expired link</h1>", status_code=401)

    session_token = _get_admin_token(admin_id)
    _admin_sessions[session_token] = admin_id

    response = HTMLResponse(content="<script>window.location.href='/admin';</script>")
    response.set_cookie("admin_token", session_token, httponly=True, max_age=86400 * 7)
    return response


def _login_page() -> str:
    return """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SWD x Videogen - Admin Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f23; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-box { background: #1a1a2e; padding: 40px; border-radius: 16px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.4); max-width: 400px; width: 90%; }
        .login-box h1 { color: #00d4ff; margin-bottom: 10px; font-size: 24px; }
        .login-box p { color: #888; margin-bottom: 20px; }
        .login-box .icon { font-size: 48px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="icon">🔒</div>
        <h1>SWD x Videogen</h1>
        <p>Admin Dashboard<br>Akses hanya untuk admin yang terdaftar.<br><br>Buka link login dari Telegram bot.</p>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
async def api_dashboard(request: Request):
    await _verify_admin(request)
    stock = db.get_stock_count()
    orders = db.get_all_orders(limit=50)
    users = db.get_all_user_ids()
    pending = len([o for o in orders if o.get("status") == "pending"])
    paid = len([o for o in orders if o.get("status") == "paid"])
    delivered = len([o for o in orders if o.get("status") == "delivered"])
    cancelled = len([o for o in orders if o.get("status") == "cancelled"])
    total_revenue = sum(o.get("total", 0) for o in orders if o.get("status") in ("paid", "delivered"))

    return {
        "stock": stock,
        "total_users": len(users),
        "total_orders": len(orders),
        "pending": pending,
        "paid": paid,
        "delivered": delivered,
        "cancelled": cancelled,
        "total_revenue": total_revenue,
        "harga_per_akun": config.HARGA_PER_AKUN,
        "shop_name": config.SHOP_NAME,
        "admins": list(config.ADMIN_IDS),
    }


@app.get("/api/orders")
async def api_orders(request: Request, status: str = None, limit: int = 50):
    await _verify_admin(request)
    orders = db.get_all_orders(limit=limit, status=status)
    return {"orders": orders}


@app.get("/api/stock")
async def api_stock(request: Request):
    await _verify_admin(request)
    count = db.get_stock_count()
    return {"stock": count, "harga": config.HARGA_PER_AKUN}


@app.post("/api/stock/add")
async def api_add_stock(request: Request):
    await _verify_admin(request)
    body = await request.json()
    text = body.get("text", "")
    lines = text.splitlines()
    count = db.add_stock_batch(lines)
    stock = db.get_stock_count()
    return {"added": count, "total": stock}


@app.post("/api/price")
async def api_set_price(request: Request):
    await _verify_admin(request)
    body = await request.json()
    new_price = body.get("price", 0)
    if new_price > 0:
        config.HARGA_PER_AKUN = new_price
        return {"price": new_price}
    return JSONResponse(status_code=400, content={"error": "Invalid price"})


@app.post("/api/admins/add")
async def api_add_admin(request: Request):
    await _verify_admin(request)
    body = await request.json()
    new_admin_id = body.get("telegram_id")
    if new_admin_id:
        config.ADMIN_IDS.add(int(new_admin_id))
        return {"success": True, "admins": list(config.ADMIN_IDS)}
    return JSONResponse(status_code=400, content={"error": "Missing telegram_id"})


@app.post("/api/admins/remove")
async def api_remove_admin(request: Request):
    await _verify_admin(request)
    body = await request.json()
    remove_id = body.get("telegram_id")
    if remove_id:
        remove_id = int(remove_id)
        if remove_id == config.ADMIN_USER_ID:
            return JSONResponse(status_code=400, content={"error": "Cannot remove main admin"})
        config.ADMIN_IDS.discard(remove_id)
        return {"success": True, "admins": list(config.ADMIN_IDS)}
    return JSONResponse(status_code=400, content={"error": "Missing telegram_id"})


@app.post("/api/broadcast")
async def api_broadcast(request: Request):
    await _verify_admin(request)
    body = await request.json()
    message = body.get("message", "")
    if not message:
        return JSONResponse(status_code=400, content={"error": "Empty message"})
    user_ids = db.get_all_user_ids()
    return {"message": message, "total_users": len(user_ids), "status": "queued"}


@app.post("/api/orders/{order_id}/status")
async def api_update_order_status(order_id: str, request: Request):
    await _verify_admin(request)
    body = await request.json()
    new_status = body.get("status", "")
    if new_status in ("pending", "paid", "cancelled", "delivered"):
        db.update_order_status(order_id, new_status)
        return {"success": True}
    return JSONResponse(status_code=400, content={"error": "Invalid status"})


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

            # Try to deliver accounts
            try:
                import io
                from telegram import Bot
                order = db.get_order(order_id)
                if order:
                    quantity = order["quantity"]
                    product_id = order.get("product_id", 1)
                    user_id = order["user_id"]
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
                        bot = Bot(token=config.BOT_TOKEN)
                        await bot.send_document(
                            chat_id=user_id,
                            document=txt_file,
                            caption=(
                                f"✅ PAYMENT SUCCESSFUL!\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"🆔 Order: #{order_id}\n"
                                f"🔢 Quantity: {quantity} accounts\n"
                                f"💰 Total: Rp {order.get('total', 0):,}\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                f"📁 Your account file is attached.\n"
                                f"Keep it safe! 🔐"
                            ),
                        )
                        logger.info("Webhook delivered %d accounts for %s", len(stock_items), order_id)
                    else:
                        logger.warning("Webhook order %s paid but stock insufficient!", order_id)
                        from telegram import Bot
                        bot = Bot(token=config.BOT_TOKEN)
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"Payment successful for Order *#{order_id}*!\n\nHowever, stock is insufficient. Admin will process manually.",
                            parse_mode="Markdown",
                        )
            except Exception as e:
                logger.exception("Webhook delivery failed for %s: %s", order_id, e)

        elif status in ("EXPIRED", "FAILED", "CANCELLED"):
            db.update_order_status(order_id, "cancelled")
            released = db.release_stock(order_id)
            logger.info("Order %s cancelled via webhook (%s), released %d stock", order_id, status, released)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "bot": config.SHOP_NAME}


def run_webhook():
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info("Starting webhook server on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_webhook()
