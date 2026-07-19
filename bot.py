"""Main entry point for SWD x Videogen Bot."""

import logging
import threading

from telegram import Update
from telegram.ext import ApplicationBuilder

import config
import db
from handlers import start, admin, buy
from jobs import poller
from payments import klikqris

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

DASHBOARD_PORT = 8080
WEBHOOK_PORT = 8443


def main():
    db.init_db(config.DB_PATH)
    logger.info("Database siap: %s", config.DB_PATH)
    logger.info("Bot: @%s | Admin: %s | Harga: Rp %s/akun", config.SHOP_NAME, config.ADMIN_USER_ID, config.HARGA_PER_AKUN)
    logger.info("Admin IDs: %s", config.ADMIN_IDS)

    if config.KLIKQRIS_ACTIVE:
        klikqris.init(
            api_key=config.KLIKQRIS_API_KEY,
            merchant_id=config.KLIKQRIS_MERCHANT_ID,
            mode=config.KLIKQRIS_MODE,
        )
        logger.info("KlikQRIS: aktif (mode %s)", config.KLIKQRIS_MODE)
    else:
        logger.warning("KlikQRIS: non-aktif.")

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    start.register(app)
    admin.register(app)
    buy.register(app)

    if config.KLIKQRIS_ACTIVE and app.job_queue is not None:
        app.job_queue.run_repeating(
            poller.check_payments,
            interval=poller.POLL_INTERVAL,
            first=poller.POLL_INTERVAL,
            name="klikqris_poller",
        )
        logger.info("QRIS poller aktif (interval %ds)", poller.POLL_INTERVAL)

    if config.USE_WEBHOOK and config.WEBHOOK_URL:
        _run_webhook_mode(app)
    else:
        logger.info("Starting in POLLING mode...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


def _run_webhook_mode(app):
    """Run FastAPI dashboard + PTB webhook on separate ports."""
    from webhook import app as fastapi_app

    def run_fastapi():
        import uvicorn
        logger.info("FastAPI dashboard: http://0.0.0.0:%d", DASHBOARD_PORT)
        uvicorn.run(fastapi_app, host="0.0.0.0", port=DASHBOARD_PORT)

    t = threading.Thread(target=run_fastapi, daemon=True)
    t.start()

    webhook_url = f"{config.WEBHOOK_URL}/webhook/telegram"
    logger.info("PTB webhook: %s (port %d)", webhook_url, WEBHOOK_PORT)

    app.run_webhook(
        listen="0.0.0.0",
        port=WEBHOOK_PORT,
        url_path="webhook/telegram",
        webhook_url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
