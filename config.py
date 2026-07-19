"""Load .env dan expose konstanta konfigurasi bot."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")


def _require_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise SystemExit(f"{key} tidak ditemukan di .env")
    return value


def _require_int_env(key: str) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        raise SystemExit(f"{key} tidak ditemukan di .env")
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"{key} harus berupa angka integer yang valid di .env")


BOT_TOKEN: str = _require_env("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID: int = _require_int_env("ADMIN_USER_ID")
HARGA_PER_AKUN: int = _require_int_env("HARGA_PER_AKUN")

SHOP_NAME: str = os.getenv("SHOP_NAME", "SWD x Videogen")
DB_PATH: str = os.getenv("DB_PATH", "data/bot.db")

KLIKQRIS_API_KEY: str = os.getenv("KLIKQRIS_API_KEY", "").strip()
KLIKQRIS_MERCHANT_ID: str = os.getenv("KLIKQRIS_MERCHANT_ID", "").strip()
KLIKQRIS_MODE: str = os.getenv("KLIKQRIS_MODE", "sandbox").strip().lower()

KLIKQRIS_ACTIVE: bool = bool(KLIKQRIS_API_KEY) and bool(KLIKQRIS_MERCHANT_ID)

# Webhook config
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8080"))
USE_WEBHOOK: bool = os.getenv("USE_WEBHOOK", "false").lower() == "true"

# Admin IDs (mutable set for adding/removing admins at runtime)
ADMIN_IDS: set[int] = {ADMIN_USER_ID}
_extra_admins = os.getenv("EXTRA_ADMIN_IDS", "").strip()
if _extra_admins:
    for _id in _extra_admins.split(","):
        _id = _id.strip()
        if _id.isdigit():
            ADMIN_IDS.add(int(_id))
