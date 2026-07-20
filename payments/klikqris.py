"""KlikQRIS payment gateway client — PG KlikQRIS mode (production).

Base URL  : https://klikqris.com/api
Create    : POST /qris/create
Status    : GET  /qris/status/{order_id}

Module-level singleton: `init()` dipanggil dari bot.py, lalu `get()`
mengembalikan instance yang siap pakai.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class KlikQRISError(Exception):
    pass


class KlikQRIS:
    """Wrapper API KlikQRIS PG mode — production."""

    BASE_URL = "https://klikqris.com/api"

    def __init__(self, api_key: str, merchant_id: str, mode: str = "production",
                 timeout: int = 30, callback_url: str = ""):
        self.api_key = api_key
        self.merchant_id = merchant_id
        self.mode = mode
        self.timeout = timeout
        self.base_url = self.BASE_URL
        self.callback_url = callback_url
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("KlikQRIS initialized — mode: %s, base: %s, callback: %s",
                     mode, self.base_url, callback_url or "(not set)")

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "x-api-key": self.api_key,
                    "id_merchant": self.merchant_id,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def create_qris(self, order_id: str, amount: int, keterangan: str = "") -> dict[str, Any]:
        """Buat QRIS baru.

        Returns dict with keys like: status, data.qris_image, data.qris_url,
        data.total_amount, data.expired_at, data.signature, etc.
        """
        payload = {
            "order_id": order_id,
            "amount": amount,
            "id_merchant": self.merchant_id,
            "keterangan": keterangan,
        }
        if self.callback_url:
            payload["callback_url"] = self.callback_url
        logger.info("Create QRIS: %s amount=%d mode=%s", order_id, amount, self.mode)
        try:
            r = await self.client.post(f"{self.base_url}/qris/create", json=payload)
            r.raise_for_status()
            data = r.json()
            logger.info("KlikQRIS create response status=%s keys=%s", data.get("status"), list(data.get("data", {}).keys()))
            if data.get("status") is not True:
                raise KlikQRISError(data.get("message", "Unknown error"))
            return data
        except httpx.HTTPStatusError as e:
            raise KlikQRISError(f"HTTP {e.response.status_code}: {e.response.text[:200]}") from e
        except httpx.RequestError as e:
            raise KlikQRISError(f"Network error: {e}") from e

    async def check_status(self, order_id: str) -> dict[str, Any]:
        """Cek status QRIS.

        Returns dict with data.payment_status in: PENDING, SUCCESS, EXPIRED.
        """
        try:
            r = await self.client.get(f"{self.base_url}/qris/status/{order_id}")
            r.raise_for_status()
            data = r.json()
            if data.get("status") is not True:
                return {"status": False, "data": {"payment_status": "PENDING"}}
            return data
        except httpx.HTTPStatusError as e:
            raise KlikQRISError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise KlikQRISError(f"Network error: {e}") from e

    def verify_webhook(self, payload: dict, signature: str) -> bool:
        data = json.dumps(payload, sort_keys=True)
        expected = hmac.new(self.api_key.encode(), data.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def decode_qris_image(raw: str) -> Optional[bytes]:
        """Decode base64 data-URI dari field qris_image menjadi bytes PNG."""
        if not raw:
            return None
        if raw.startswith("data:"):
            try:
                _, b64part = raw.split(",", 1)
                return base64.b64decode(b64part)
            except Exception:
                return None
        # Jika sudah raw base64 tanpa prefix
        try:
            return base64.b64decode(raw)
        except Exception:
            return None


# Module-level singleton
_client: Optional[KlikQRIS] = None


def init(api_key: str, merchant_id: str, mode: str = "production",
         timeout: int = 30, callback_url: str = "") -> KlikQRIS:
    global _client
    _client = KlikQRIS(api_key=api_key, merchant_id=merchant_id, mode=mode,
                       timeout=timeout, callback_url=callback_url)
    return _client


def get() -> KlikQRIS:
    if _client is None:
        raise RuntimeError("KlikQRIS belum diinisialisasi. Panggil klikqris.init() dulu.")
    return _client


def is_active() -> bool:
    return _client is not None


async def shutdown() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None
