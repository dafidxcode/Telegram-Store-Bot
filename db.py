"""SQLite database layer for VideoGen Bot.

Tables:
  - stock: email:password:balance entries ready to sell
  - orders: purchase records with QRIS payment tracking
  - users: Telegram users who interacted with the bot
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_conn: sqlite3.Connection | None = None

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stock (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  balance TEXT DEFAULT '',
  status TEXT DEFAULT 'ready',
  added_at TEXT DEFAULT (datetime('now')),
  sold_at TEXT,
  order_id TEXT
);

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  username TEXT,
  first_name TEXT,
  quantity INTEGER NOT NULL,
  total INTEGER NOT NULL,
  status TEXT DEFAULT 'pending',
  qris_ref TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  paid_at TEXT
);

CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_name TEXT,
  last_seen TEXT DEFAULT (datetime('now'))
);
"""


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def init_db(path: str) -> None:
    global _conn
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(_SCHEMA_SQL)
    _conn.commit()


# ---------------------------------------------------------------------------
# Stock management
# ---------------------------------------------------------------------------

def add_stock_batch(lines: list[str]) -> int:
    """Parse lines of format email:password:balance and insert ready stock.
    Returns count of successfully added entries."""
    assert _conn is not None
    count = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 2:
            continue
        email = parts[0].strip()
        password = parts[1].strip()
        balance = parts[2].strip() if len(parts) > 2 else ""
        if not email or not password:
            continue
        try:
            _conn.execute(
                "INSERT OR IGNORE INTO stock (email, password, balance) VALUES (?, ?, ?)",
                (email, password, balance),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass
    _conn.commit()
    return count


def get_stock_count() -> int:
    assert _conn is not None
    row = _conn.execute("SELECT COUNT(*) as cnt FROM stock WHERE status = 'ready'").fetchone()
    return row["cnt"] if row else 0


def get_total_sold() -> int:
    assert _conn is not None
    row = _conn.execute("SELECT COUNT(*) as cnt FROM stock WHERE status = 'sold'").fetchone()
    return row["cnt"] if row else 0


def get_user_order_count(user_id: int) -> int:
    assert _conn is not None
    row = _conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE user_id = ?", (user_id,)).fetchone()
    return row["cnt"] if row else 0


def get_total_users() -> int:
    assert _conn is not None
    row = _conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    return row["cnt"] if row else 0


def take_stock(order_id: str, quantity: int) -> list[dict]:
    """Atomically mark `quantity` stock items as sold and return them.
    Uses a transaction to prevent race conditions."""
    assert _conn is not None
    cur = _conn.execute(
        "SELECT id, email, password, balance FROM stock WHERE status = 'ready' LIMIT ?",
        (quantity,),
    )
    items = [_row_to_dict(r) for r in cur.fetchall()]

    if not items:
        return []

    now_fn = "datetime('now')"
    for item in items:
        _conn.execute(
            "UPDATE stock SET status = 'sold', sold_at = {}, order_id = ? WHERE id = ?".format(now_fn),
            (order_id, item["id"]),
        )
    _conn.commit()
    return items


def release_stock(order_id: str) -> int:
    """Release stock items back to ready status for a cancelled/expired order."""
    assert _conn is not None
    cur = _conn.execute(
        "UPDATE stock SET status = 'ready', sold_at = NULL, order_id = NULL WHERE order_id = ? AND status = 'sold'",
        (order_id,),
    )
    _conn.commit()
    return cur.rowcount


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def create_order(
    order_id: str,
    user_id: int,
    username: str | None,
    first_name: str | None,
    quantity: int,
    total: int,
) -> None:
    assert _conn is not None
    _conn.execute(
        """INSERT INTO orders (id, user_id, username, first_name, quantity, total)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (order_id, user_id, username, first_name, quantity, total),
    )
    _conn.commit()


def get_order(order_id: str) -> dict | None:
    assert _conn is not None
    row = _conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return _row_to_dict(row)


def get_user_orders(user_id: int) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_orders(limit: int = 50, status: str | None = None) -> list[dict]:
    assert _conn is not None
    if status is None:
        rows = _conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = _conn.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_order_status(order_id: str, status: str) -> bool:
    assert _conn is not None
    extra = ""
    params: list = [status]
    if status == "paid":
        extra = ", paid_at = datetime('now')"
    cur = _conn.execute(
        f"UPDATE orders SET status = ?{extra} WHERE id = ?",
        [*params, order_id],
    )
    _conn.commit()
    return cur.rowcount > 0


def set_order_qris_ref(order_id: str, qris_ref: str) -> bool:
    assert _conn is not None
    cur = _conn.execute(
        "UPDATE orders SET qris_ref = ? WHERE id = ?",
        (qris_ref, order_id),
    )
    _conn.commit()
    return cur.rowcount > 0


def get_pending_qris_orders() -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT * FROM orders WHERE status = 'pending' AND qris_ref IS NOT NULL ORDER BY created_at ASC LIMIT 50"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    assert _conn is not None
    _conn.execute(
        """INSERT OR REPLACE INTO users (user_id, username, first_name, last_seen)
        VALUES (?, ?, ?, datetime('now'))""",
        (user_id, username, first_name),
    )
    _conn.commit()


def get_all_user_ids() -> list[int]:
    assert _conn is not None
    rows = _conn.execute("SELECT user_id FROM users").fetchall()
    return [int(row["user_id"]) for row in rows]
