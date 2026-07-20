"""Main entry point for SWD x Videogen Bot."""

import logging
import os
import threading

import uvicorn
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
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def _start_webhook_server():
    """Run the FastAPI webhook server in a background thread."""
    from webhook import app
    port = int(os.getenv("PORT", "8080"))
    logger.info("Starting webhook server on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)


def main():
    db.init_db(config.DB_PATH)
    logger.info("Database siap: %s", config.DB_PATH)
    logger.info("Bot: @%s | Admin: %s | Harga: Rp %s/akun", config.SHOP_NAME, config.ADMIN_USER_ID, config.HARGA_PER_AKUN)
    logger.info("Admin IDs: %s", config.ADMIN_IDS)

    if config.KLIKQRIS_ACTIVE:
        klikqris.init(
            api_key=config.KLIKQRIS_API_KEY,
            merchant_id=config.KLIKQRIS_MERCHANT_ID,
            mode="production",
            callback_url=config.KLIKQRIS_CALLBACK_URL,
        )
        logger.info("KlikQRIS: aktif (mode production, PG KlikQRIS)")
    else:
        logger.warning("KlikQRIS: non-aktif.")

    # Start webhook server in background thread
    webhook_thread = threading.Thread(target=_start_webhook_server, daemon=True)
    webhook_thread.start()

    app = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

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

    logger.info("Starting bot + webhook server...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
