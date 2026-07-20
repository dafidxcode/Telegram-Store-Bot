"""SQLite database layer for SWD x Videogen Bot.

Tables:
  - products: product catalog
  - stock: email:password:balance entries ready to sell (linked to product)
  - orders: purchase records with QRIS payment tracking
  - users: Telegram users who interacted with the bot
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_conn: sqlite3.Connection | None = None

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  price INTEGER NOT NULL DEFAULT 0,
  stock_type TEXT DEFAULT 'limited',
  stock_count INTEGER DEFAULT 0,
  duration TEXT DEFAULT '',
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stock (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER DEFAULT 1,
  email TEXT NOT NULL,
  password TEXT NOT NULL,
  balance TEXT DEFAULT '',
  status TEXT DEFAULT 'ready',
  added_at TEXT DEFAULT (datetime('now')),
  sold_at TEXT,
  order_id TEXT
);

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  product_id INTEGER DEFAULT 1,
  user_id INTEGER NOT NULL,
  username TEXT,
  first_name TEXT,
  quantity INTEGER NOT NULL,
  total INTEGER NOT NULL,
  qris_nominal INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  qris_ref TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  paid_at TEXT,
  expires_at TEXT
);

CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_name TEXT,
  last_seen TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_email_product ON stock(email, product_id);
"""


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns/tables for existing databases."""
    cursor = conn.execute("PRAGMA table_info(stock)")
    cols = {row["name"] for row in cursor.fetchall()}
    if "product_id" not in cols:
        conn.execute("ALTER TABLE stock ADD COLUMN product_id INTEGER DEFAULT 1")

    cursor = conn.execute("PRAGMA table_info(orders)")
    cols = {row["name"] for row in cursor.fetchall()}
    if "product_id" not in cols:
        conn.execute("ALTER TABLE orders ADD COLUMN product_id INTEGER DEFAULT 1")
    if "qris_nominal" not in cols:
        conn.execute("ALTER TABLE orders ADD COLUMN qris_nominal INTEGER DEFAULT 0")
    if "expires_at" not in cols:
        conn.execute("ALTER TABLE orders ADD COLUMN expires_at TEXT")
    if "qris_message_id" not in cols:
        conn.execute("ALTER TABLE orders ADD COLUMN qris_message_id INTEGER")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          description TEXT DEFAULT '',
          price INTEGER NOT NULL DEFAULT 0,
          stock_type TEXT DEFAULT 'limited',
          stock_count INTEGER DEFAULT 0,
          duration TEXT DEFAULT '',
          is_active INTEGER DEFAULT 1,
          created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # --- migration: rebuild unique index from global to per-product ---
    try:
        old_idx = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_stock_email'"
        ).fetchone()
        if old_idx:
            conn.execute("DROP INDEX IF EXISTS idx_stock_email")
            logger_d = __import__("logging").getLogger(__name__)
            logger_d.info("Dropped old global unique index idx_stock_email")
    except Exception:
        pass

    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_email_product ON stock(email, product_id)"
        )
    except Exception:
        pass

    conn.commit()


def init_db(path: str) -> None:
    global _conn
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(_SCHEMA_SQL)
    _migrate(_conn)
    _conn.commit()


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def add_product(name: str, description: str, price: int, stock_type: str = "limited",
                stock_count: int = 0, duration: str = "") -> int:
    assert _conn is not None
    cur = _conn.execute(
        """INSERT INTO products (name, description, price, stock_type, stock_count, duration)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (name, description, price, stock_type, stock_count, duration),
    )
    _conn.commit()
    return cur.lastrowid


def get_product(product_id: int) -> dict | None:
    assert _conn is not None
    row = _conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return _row_to_dict(row)


def get_active_products() -> list[dict]:
    assert _conn is not None
    rows = _conn.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY id ASC").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_products() -> list[dict]:
    assert _conn is not None
    rows = _conn.execute("SELECT * FROM products ORDER BY id ASC").fetchall()
    return [_row_to_dict(r) for r in rows]


def update_product(product_id: int, **kwargs) -> bool:
    assert _conn is not None
    allowed = {"name", "description", "price", "stock_type", "stock_count", "duration", "is_active"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [product_id]
    cur = _conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", vals)
    _conn.commit()
    return cur.rowcount > 0


def delete_product(product_id: int) -> bool:
    assert _conn is not None
    cur = _conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    _conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Stock management
# ---------------------------------------------------------------------------

def add_stock_batch(lines: list[str], product_id: int = 1) -> int:
    """Parse lines of format email:password and insert ready stock."""
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
                "INSERT OR IGNORE INTO stock (product_id, email, password, balance) VALUES (?, ?, ?, ?)",
                (product_id, email, password, balance),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass
    _conn.commit()
    return count


def get_stock_count(product_id: int | None = None) -> int:
    assert _conn is not None
    if product_id is not None:
        row = _conn.execute(
            "SELECT COUNT(*) as cnt FROM stock WHERE status = 'ready' AND product_id = ?",
            (product_id,),
        ).fetchone()
    else:
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


def take_stock(order_id: str, quantity: int, product_id: int = 1) -> list[dict]:
    """Atomically mark `quantity` stock items as sold and return them."""
    assert _conn is not None
    cur = _conn.execute(
        "SELECT id, email, password, balance FROM stock WHERE status = 'ready' AND product_id = ? LIMIT ?",
        (product_id, quantity),
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
    product_id: int = 1,
    qris_nominal: int = 0,
    expires_at: str = "",
) -> None:
    assert _conn is not None
    _conn.execute(
        """INSERT INTO orders (id, product_id, user_id, username, first_name, quantity, total, qris_nominal, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (order_id, product_id, user_id, username, first_name, quantity, total, qris_nominal, expires_at),
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


def delete_order(order_id: str) -> bool:
    assert _conn is not None
    cur = _conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
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


def set_order_qris_message_id(order_id: str, message_id: int) -> bool:
    assert _conn is not None
    cur = _conn.execute(
        "UPDATE orders SET qris_message_id = ? WHERE id = ?",
        (message_id, order_id),
    )
    _conn.commit()
    return cur.rowcount > 0


def get_pending_qris_orders() -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT * FROM orders WHERE status = 'pending' AND qris_ref IS NOT NULL ORDER BY created_at ASC LIMIT 50"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_expired_pending_orders() -> list[dict]:
    """Get pending orders whose expires_at has passed."""
    assert _conn is not None
    rows = _conn.execute(
        "SELECT * FROM orders WHERE status = 'pending' AND expires_at != '' AND expires_at < datetime('now') ORDER BY created_at ASC LIMIT 50"
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
