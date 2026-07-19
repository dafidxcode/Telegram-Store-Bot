"""Main entry point for SWD x Videogen Bot.

Supports both polling mode (default) and webhook mode.
Set USE_WEBHOOK=true in .env for webhook mode.
"""

import logging

from telegram import Update
from telegram.ext import ApplicationBuilder

import config
import db
from handlers import start, admin, buy
from jobs import poller
from payments import klikqris


def main():
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

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
        logger.warning("KlikQRIS: non-aktif. Set KLIKQRIS_API_KEY & KLIKQRIS_MERCHANT_ID di .env.")

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
        # Webhook mode - run FastAPI + bot webhook together
        logger.info("Starting in WEBHOOK mode: %s", config.WEBHOOK_URL)
        _run_webhook_mode(app)
    else:
        # Polling mode (default, for local development)
        logger.info("Starting in POLLING mode...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    if config.KLIKQRIS_ACTIVE:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(klikqris.shutdown())
        except Exception:
            pass


def _run_webhook_mode(app):
    """Run bot via webhook + FastAPI server."""
    import asyncio
    import threading
    from webhook import app as fastapi_app

    # Start FastAPI in a separate thread
    def run_fastapi():
        import uvicorn
        port = config.WEBHOOK_PORT
        uvicorn.run(fastapi_app, host="0.0.0.0", port=port)

    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    # Set Telegram webhook
    webhook_url = f"{config.WEBHOOK_URL}/webhook/telegram"
    logger.info("Setting webhook: %s", webhook_url)

    app.bot.set_webhook(url=webhook_url)
    logger.info("Webhook set. Bot running via webhook.")

    # Run the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
