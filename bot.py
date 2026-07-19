"""Main entry point for SWD x Videogen Bot."""

import logging

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

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
