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
  instruction TEXT DEFAULT '',
  price INTEGER NOT NULL DEFAULT 0,
  stock_type TEXT DEFAULT 'limited',
  stock_count INTEGER DEFAULT 0,
  duration TEXT DEFAULT '',
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS admin_sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  feedback_id INTEGER NOT NULL,
  sender TEXT NOT NULL,
  sender_id INTEGER DEFAULT 0,
  message TEXT NOT NULL,
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
  original_total INTEGER DEFAULT 0,
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
  lang TEXT DEFAULT 'en',
  referral_code TEXT DEFAULT '',
  referred_by INTEGER DEFAULT 0,
  is_banned INTEGER DEFAULT 0,
  ban_reason TEXT DEFAULT '',
  last_seen TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS referrals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  referrer_id INTEGER NOT NULL,
  referred_id INTEGER NOT NULL,
  reward_granted INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  username TEXT DEFAULT '',
  category TEXT DEFAULT 'saran',
  message TEXT NOT NULL,
  admin_reply TEXT DEFAULT '',
  status TEXT DEFAULT 'open',
  created_at TEXT DEFAULT (datetime('now')),
  replied_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS purchase_details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  product_name TEXT DEFAULT '',
  accounts_delivered TEXT DEFAULT '',
  delivered_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bot_settings (
  key TEXT PRIMARY KEY,
  value TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS referral_commissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  referrer_id INTEGER NOT NULL,
  referred_id INTEGER NOT NULL,
  order_id TEXT NOT NULL,
  order_amount INTEGER NOT NULL DEFAULT 0,
  commission_percent INTEGER NOT NULL DEFAULT 10,
  commission_amount INTEGER NOT NULL DEFAULT 0,
  status TEXT DEFAULT 'earned',
  created_at TEXT DEFAULT (datetime('now')),
  paid_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS withdrawal_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  amount INTEGER NOT NULL DEFAULT 0,
  bank_name TEXT DEFAULT '',
  account_number TEXT DEFAULT '',
  account_name TEXT DEFAULT '',
  status TEXT DEFAULT 'pending',
  admin_note TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  processed_at TEXT DEFAULT ''
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

    cursor = conn.execute("PRAGMA table_info(users)")
    cols = {row["name"] for row in cursor.fetchall()}
    if "lang" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'en'")
    if "referral_code" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN referral_code TEXT DEFAULT ''")
    if "referred_by" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
    if "is_banned" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    if "ban_reason" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT DEFAULT ''")

    cursor = conn.execute("PRAGMA table_info(products)")
    cols = {row["name"] for row in cursor.fetchall()}
    if "instruction" not in cols:
        conn.execute("ALTER TABLE products ADD COLUMN instruction TEXT DEFAULT ''")

    for tbl in ("referrals", "feedback", "purchase_details", "referral_commissions", "withdrawal_requests", "bot_settings", "admin_sessions", "feedback_messages"):
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {tbl} (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        """)

    conn.commit()


def init_db(path: str) -> None:
    global _conn
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL;")
    _conn.execute("PRAGMA busy_timeout=5000;")
    _conn.executescript(_SCHEMA_SQL)
    _migrate(_conn)
    _conn.commit()
    try:
        renumber_products()
    except Exception:
        pass



# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def add_product(name: str, description: str, price: int, stock_type: str = "limited",
                stock_count: int = 0, duration: str = "", instruction: str = "") -> int:
    assert _conn is not None
    cur = _conn.execute(
        """INSERT INTO products (name, description, instruction, price, stock_type, stock_count, duration)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, description, instruction, price, stock_type, stock_count, duration),
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
    allowed = {"name", "description", "instruction", "price", "stock_type", "stock_count", "duration", "is_active"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [product_id]
    cur = _conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", vals)
    _conn.commit()
    return cur.rowcount > 0


def swap_products(id1: int, id2: int) -> bool:
    """Swap IDs and associated foreign key data of two products."""
    assert _conn is not None
    try:
        p1 = get_product(id1)
        p2 = get_product(id2)
        if not p1 or not p2:
            return False

        temp_id = -9999

        for tbl in ["stock", "orders"]:
            try:
                _conn.execute(f"UPDATE {tbl} SET product_id = ? WHERE product_id = ?", (temp_id, id1))
                _conn.execute(f"UPDATE {tbl} SET product_id = ? WHERE product_id = ?", (id1, id2))
                _conn.execute(f"UPDATE {tbl} SET product_id = ? WHERE product_id = ?", (id2, temp_id))
            except Exception:
                pass

        _conn.execute("UPDATE products SET id = ? WHERE id = ?", (temp_id, id1))
        _conn.execute("UPDATE products SET id = ? WHERE id = ?", (id1, id2))
        _conn.execute("UPDATE products SET id = ? WHERE id = ?", (id2, temp_id))

        _conn.commit()
        return True
    except Exception as e:
        logger_d = __import__("logging").getLogger(__name__)
        logger_d.exception("Error swapping products %s and %s: %s", id1, id2, e)
        return False


def delete_product(product_id: int) -> bool:
    assert _conn is not None
    cur = _conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    _conn.commit()
    if cur.rowcount > 0:
        renumber_products()
    return cur.rowcount > 0


def renumber_products() -> bool:
    """Renumber all existing products sequentially (1, 2, 3...) and update foreign keys in stock, orders."""
    assert _conn is not None
    try:
        rows = _conn.execute("SELECT id FROM products ORDER BY id ASC").fetchall()
        if not rows:
            _conn.execute("DELETE FROM sqlite_sequence WHERE name = 'products'")
            _conn.commit()
            return True

        old_ids = [r["id"] for r in rows]

        # Step 0: Isolate orphan stock (stock belonging to deleted products) to product_id = 0 so they don't contaminate active products
        if old_ids:
            placeholders = ",".join("?" for _ in old_ids)
            _conn.execute(f"UPDATE stock SET product_id = 0 WHERE product_id NOT IN ({placeholders}) AND product_id > 0", old_ids)

        # Step 1: Map old_id to temporary negative ID (-idx) to prevent unique constraint conflicts
        for idx, old_id in enumerate(old_ids, 1):
            temp_id = -idx
            if old_id != idx:
                _conn.execute("UPDATE stock SET product_id = ? WHERE product_id = ?", (temp_id, old_id))
                _conn.execute("UPDATE orders SET product_id = ? WHERE product_id = ?", (temp_id, old_id))
                _conn.execute("UPDATE products SET id = ? WHERE id = ?", (temp_id, old_id))

        # Step 2: Map temporary negative ID (-idx) to target positive ID (idx)
        for idx in range(1, len(old_ids) + 1):
            temp_id = -idx
            new_id = idx
            _conn.execute("UPDATE stock SET product_id = ? WHERE product_id = ?", (new_id, temp_id))
            _conn.execute("UPDATE orders SET product_id = ? WHERE product_id = ?", (new_id, temp_id))
            _conn.execute("UPDATE products SET id = ? WHERE id = ?", (new_id, temp_id))

        # Step 3: Reset autoincrement sequence
        _conn.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'products'", (len(old_ids),))
        _conn.commit()
        return True
    except Exception as e:
        logger_d = __import__("logging").getLogger(__name__)
        logger_d.exception("Error renumbering products: %s", e)
        return False




# ---------------------------------------------------------------------------
# Stock management
# ---------------------------------------------------------------------------

def add_stock_batch(lines: list[str], product_id: int = 1) -> int:
    """Parse lines of stock (1 line per item/account) and insert ready stock."""
    assert _conn is not None
    count = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line and ":" not in line:
            line = line.replace("|", ":")
        parts = line.split(":", 2)
        if len(parts) >= 2:
            email = parts[0].strip()
            password = parts[1].strip()
            balance = parts[2].strip() if len(parts) > 2 else ""
        else:
            email = line
            password = ""
            balance = ""
        if not email:
            continue
        try:
            cur = _conn.execute(
                "INSERT OR IGNORE INTO stock (product_id, email, password, balance) VALUES (?, ?, ?, ?)",
                (product_id, email, password, balance),
            )
            if cur.rowcount > 0:
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
        row = _conn.execute(
            "SELECT COUNT(*) as cnt FROM stock s JOIN products p ON s.product_id = p.id WHERE s.status = 'ready' AND p.is_active = 1"
        ).fetchone()
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


def get_stock_items(
    product_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Retrieve stock items joined with product names with optional filters, search, and pagination."""
    assert _conn is not None
    where_clauses = []
    params: list = []

    if product_id is not None:
        if product_id == 0:
            where_clauses.append("(s.product_id = 0 OR s.product_id NOT IN (SELECT id FROM products))")
        elif product_id > 0:
            where_clauses.append("s.product_id = ?")
            params.append(product_id)

    if status and status in ("ready", "sold"):
        where_clauses.append("s.status = ?")
        params.append(status)

    if search:
        search_pat = f"%{search.strip()}%"
        where_clauses.append("(s.email LIKE ? OR s.password LIKE ? OR s.balance LIKE ? OR s.order_id LIKE ?)")
        params.extend([search_pat, search_pat, search_pat, search_pat])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_sql = f"SELECT COUNT(*) as cnt FROM stock s {where_sql}"
    total_row = _conn.execute(count_sql, params).fetchone()
    total = total_row["cnt"] if total_row else 0

    offset = max(0, (page - 1) * limit)
    query_sql = f"""
        SELECT s.*, p.name as product_name
        FROM stock s
        LEFT JOIN products p ON s.product_id = p.id
        {where_sql}
        ORDER BY s.id DESC
        LIMIT ? OFFSET ?
    """
    rows = _conn.execute(query_sql, params + [limit, offset]).fetchall()
    items = [_row_to_dict(r) for r in rows]
    return items, total


def delete_stock_item(stock_id: int) -> bool:
    """Delete a single stock entry by ID."""
    assert _conn is not None
    cur = _conn.execute("DELETE FROM stock WHERE id = ?", (stock_id,))
    _conn.commit()
    return cur.rowcount > 0


def delete_stock_items_bulk(stock_ids: list[int]) -> int:
    """Delete multiple stock entries by IDs."""
    assert _conn is not None
    if not stock_ids:
        return 0
    placeholders = ",".join("?" for _ in stock_ids)
    cur = _conn.execute(f"DELETE FROM stock WHERE id IN ({placeholders})", stock_ids)
    _conn.commit()
    return cur.rowcount


def update_stock_item_status(stock_id: int, status: str) -> bool:
    """Set status of a stock entry to 'ready' or 'sold'."""
    assert _conn is not None
    if status not in ("ready", "sold"):
        return False
    if status == "sold":
        cur = _conn.execute(
            "UPDATE stock SET status = 'sold', sold_at = datetime('now') WHERE id = ?",
            (stock_id,),
        )
    else:
        cur = _conn.execute(
            "UPDATE stock SET status = 'ready', sold_at = NULL, order_id = NULL WHERE id = ?",
            (stock_id,),
        )
    _conn.commit()
    return cur.rowcount > 0


def update_stock_items_status_bulk(stock_ids: list[int], status: str) -> int:
    """Set status of multiple stock entries."""
    assert _conn is not None
    if not stock_ids or status not in ("ready", "sold"):
        return 0
    placeholders = ",".join("?" for _ in stock_ids)
    if status == "sold":
        sql = f"UPDATE stock SET status = 'sold', sold_at = datetime('now') WHERE id IN ({placeholders})"
    else:
        sql = f"UPDATE stock SET status = 'ready', sold_at = NULL, order_id = NULL WHERE id IN ({placeholders})"
    cur = _conn.execute(sql, stock_ids)
    _conn.commit()
    return cur.rowcount


def move_stock_items_bulk(stock_ids: list[int], target_product_id: int) -> int:
    """Move specified stock IDs to target product ID."""
    assert _conn is not None
    if not stock_ids:
        return 0
    placeholders = ",".join("?" for _ in stock_ids)
    cur = _conn.execute(
        f"UPDATE stock SET product_id = ? WHERE id IN ({placeholders})",
        [target_product_id] + stock_ids,
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
    original_total: int = 0,
) -> None:
    assert _conn is not None
    _conn.execute(
        """INSERT INTO orders (id, product_id, user_id, username, first_name, quantity, total, original_total, qris_nominal, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (order_id, product_id, user_id, username, first_name, quantity, total, original_total, qris_nominal, expires_at),
    )
    _conn.commit()


def save_order_qris_message_id(order_id: str, message_id: int) -> None:
    """Save the Telegram QRIS photo message_id for deleting upon successful payment."""
    assert _conn is not None
    _conn.execute("UPDATE orders SET qris_message_id = ? WHERE id = ?", (message_id, order_id))
    _conn.commit()



def get_order(order_id: str) -> dict | None:
    assert _conn is not None
    row = _conn.execute(
        "SELECT o.*, p.name as product_name, p.stock_type FROM orders o LEFT JOIN products p ON o.product_id = p.id WHERE o.id = ?",
        (order_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_user_orders(user_id: int) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT o.*, p.name as product_name, p.stock_type FROM orders o LEFT JOIN products p ON o.product_id = p.id WHERE o.user_id = ? ORDER BY o.created_at DESC LIMIT 20",
        (user_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_orders(limit: int = 50, status: str | None = None) -> list[dict]:
    assert _conn is not None
    sql = "SELECT o.*, p.name as product_name, p.stock_type FROM orders o LEFT JOIN products p ON o.product_id = p.id"
    if status is None:
        rows = _conn.execute(
            f"{sql} ORDER BY o.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = _conn.execute(
            f"{sql} WHERE o.status = ? ORDER BY o.created_at DESC LIMIT ?",
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
    existing = _conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
    lang = existing["lang"] if existing and existing["lang"] else "en"
    _conn.execute(
        """INSERT OR REPLACE INTO users (user_id, username, first_name, lang, last_seen)
        VALUES (?, ?, ?, ?, datetime('now'))""",
        (user_id, username, first_name, lang),
    )
    _conn.commit()


def save_lang(user_id: int, lang: str) -> None:
    assert _conn is not None
    _conn.execute(
        "INSERT INTO users (user_id, lang, last_seen) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang, last_seen = excluded.last_seen",
        (user_id, lang),
    )
    _conn.commit()


def get_user_lang(user_id: int) -> str:
    assert _conn is not None
    row = _conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row and row["lang"]:
        lang = row["lang"]
        return "id" if lang == "ms" else lang
    return "id"



def get_all_user_ids() -> list[int]:
    assert _conn is not None
    rows = _conn.execute("SELECT user_id FROM users").fetchall()
    return [int(row["user_id"]) for row in rows]


def get_users_paginated(
    search: str | None = None,
    filter_by: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> tuple[list[dict], int]:
    """Retrieve paginated users with filtering and sorting (spent_desc, orders_desc, newest, oldest, banned)."""
    assert _conn is not None
    offset = max(0, (page - 1) * limit)
    where_clauses = []
    params: list = []

    if search:
        s = search.strip().lstrip("@")
        if s.isdigit():
            where_clauses.append("(u.user_id = ? OR u.username LIKE ?)")
            params.extend([int(s), f"%{s}%"])
        else:
            where_clauses.append("(u.username LIKE ? OR u.first_name LIKE ?)")
            params.extend([f"%{s}%", f"%{s}%"])

    if filter_by == "banned":
        where_clauses.append("u.is_banned = 1")

    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    order_by_clause = "ORDER BY total_spent DESC, u.last_seen DESC"
    if filter_by == "orders_desc":
        order_by_clause = "ORDER BY total_orders DESC, u.last_seen DESC"
    elif filter_by == "newest":
        order_by_clause = "ORDER BY u.last_seen DESC"
    elif filter_by == "oldest":
        order_by_clause = "ORDER BY u.user_id ASC"
    elif filter_by == "spent_desc":
        order_by_clause = "ORDER BY total_spent DESC, u.last_seen DESC"

    count_sql = f"SELECT COUNT(*) as cnt FROM users u {where_str}"
    count_row = _conn.execute(count_sql, params).fetchone()
    total = count_row["cnt"] if count_row else 0

    data_sql = f"""
        SELECT u.*,
               COALESCE((SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id AND o.status IN ('paid','delivered')), 0) as total_orders,
               COALESCE((SELECT SUM(o.total) FROM orders o WHERE o.user_id = u.user_id AND o.status IN ('paid','delivered')), 0) as total_spent
        FROM users u
        {where_str}
        {order_by_clause}
        LIMIT ? OFFSET ?
    """
    rows = _conn.execute(data_sql, params + [limit, offset]).fetchall()
    return ([_row_to_dict(r) for r in rows], total)


def get_financial_report() -> dict:
    """Calculate sales revenue metrics (today, 7 days, 30 days, total all time, best seller)."""
    assert _conn is not None

    today_row = _conn.execute(
        "SELECT COALESCE(SUM(total), 0) as rev, COUNT(*) as cnt FROM orders WHERE status = 'paid' AND date(paid_at) = date('now')"
    ).fetchone()

    week_row = _conn.execute(
        "SELECT COALESCE(SUM(total), 0) as rev, COUNT(*) as cnt FROM orders WHERE status = 'paid' AND paid_at >= datetime('now', '-7 days')"
    ).fetchone()

    month_row = _conn.execute(
        "SELECT COALESCE(SUM(total), 0) as rev, COUNT(*) as cnt FROM orders WHERE status = 'paid' AND paid_at >= datetime('now', '-30 days')"
    ).fetchone()

    total_row = _conn.execute(
        "SELECT COALESCE(SUM(total), 0) as rev, COUNT(*) as cnt FROM orders WHERE status = 'paid'"
    ).fetchone()

    best_row = _conn.execute(
        """SELECT p.name, SUM(o.quantity) as total_qty, COUNT(o.id) as order_count
           FROM orders o
           JOIN products p ON o.product_id = p.id
           WHERE o.status = 'paid'
           GROUP BY o.product_id
           ORDER BY total_qty DESC LIMIT 1"""
    ).fetchone()

    best_product = _row_to_dict(best_row) if best_row else None

    return {
        "today_revenue": today_row["rev"] if today_row else 0,
        "today_orders": today_row["cnt"] if today_row else 0,
        "week_revenue": week_row["rev"] if week_row else 0,
        "week_orders": week_row["cnt"] if week_row else 0,
        "month_revenue": month_row["rev"] if month_row else 0,
        "month_orders": month_row["cnt"] if month_row else 0,
        "total_revenue": total_row["rev"] if total_row else 0,
        "total_orders": total_row["cnt"] if total_row else 0,
        "best_product": best_product,
    }


def get_stock_file_content(product_id: int) -> str:
    """Get ready stock lines for export as text file."""
    assert _conn is not None
    rows = _conn.execute(
        "SELECT email, password, balance FROM stock WHERE product_id = ? AND status = 'ready' ORDER BY id ASC",
        (product_id,),
    ).fetchall()
    lines = []
    for r in rows:
        if r["balance"]:
            lines.append(f"{r['email']}:{r['password']}:{r['balance']}")
        elif r["password"]:
            lines.append(f"{r['email']}:{r['password']}")
        else:
            lines.append(r["email"])
    return "\n".join(lines)


def search_orders(query: str) -> list[dict]:
    """Search orders by order ID (partial/exact) or Telegram user_id / username."""
    assert _conn is not None
    query = query.strip()
    sql = "SELECT o.*, p.name as product_name, p.stock_type FROM orders o LEFT JOIN products p ON o.product_id = p.id"
    if query.isdigit():
        rows = _conn.execute(
            f"{sql} WHERE o.user_id = ? OR o.id = ? ORDER BY o.created_at DESC LIMIT 20",
            (int(query), query),
        ).fetchall()
    else:
        clean_q = query.lstrip("@")
        rows = _conn.execute(
            f"{sql} WHERE o.id LIKE ? OR o.username LIKE ? ORDER BY o.created_at DESC LIMIT 20",
            (f"%{query}%", f"%{clean_q}%"),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Referrals
# ---------------------------------------------------------------------------

def generate_referral_code(user_id: int) -> str:
    """Generate and save a unique referral code for a user."""
    assert _conn is not None
    row = _conn.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row and row["referral_code"]:
        return row["referral_code"]
    import secrets
    code = f"REF{user_id}{secrets.token_hex(3).upper()}"
    _conn.execute("UPDATE users SET referral_code = ? WHERE user_id = ?", (code, user_id))
    _conn.commit()
    return code


def get_user_by_referral_code(code: str) -> dict | None:
    assert _conn is not None
    row = _conn.execute("SELECT * FROM users WHERE referral_code = ?", (code,)).fetchone()
    return _row_to_dict(row)


def set_referred_by(user_id: int, referrer_id: int) -> bool:
    assert _conn is not None
    existing = _conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if existing and existing["referred_by"]:
        return False
    _conn.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
    _conn.execute(
        "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
        (referrer_id, user_id),
    )
    _conn.commit()
    return True


def get_referral_count(user_id: int) -> int:
    assert _conn is not None
    row = _conn.execute("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ?", (user_id,)).fetchone()
    return row["cnt"] if row else 0


def get_referral_list(user_id: int) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT r.*, u.username, u.first_name FROM referrals r LEFT JOIN users u ON r.referred_id = u.user_id WHERE r.referrer_id = ? ORDER BY r.created_at DESC",
        (user_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]

# ---------------------------------------------------------------------------
# Admin Sessions (Persistent 30 days)
# ---------------------------------------------------------------------------

def create_admin_session(token: str, user_id: int, duration_days: int = 30) -> str:
    assert _conn is not None
    _conn.execute(
        "INSERT INTO admin_sessions (token, user_id, expires_at) VALUES (?, ?, datetime('now', ?)) "
        "ON CONFLICT(token) DO UPDATE SET expires_at = excluded.expires_at",
        (token, user_id, f"+{duration_days} days"),
    )
    _conn.commit()
    return token


def validate_admin_session(token: str) -> int | None:
    assert _conn is not None
    row = _conn.execute(
        "SELECT user_id FROM admin_sessions WHERE token = ? AND expires_at > datetime('now')",
        (token,),
    ).fetchone()
    return row["user_id"] if row else None


def delete_admin_session(token: str) -> None:
    assert _conn is not None
    _conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))
    _conn.commit()


# ---------------------------------------------------------------------------
# Feedback / Kritik Saran (Multi-Turn Thread Inbox)
# ---------------------------------------------------------------------------

def add_feedback(user_id: int, username: str, category: str, message: str) -> int:
    assert _conn is not None
    existing = get_user_active_feedback(user_id)
    if existing:
        fb_id = existing["id"]
        add_feedback_message(fb_id, "user", user_id, message)
        return fb_id

    cur = _conn.execute(
        "INSERT INTO feedback (user_id, username, category, message, status) VALUES (?, ?, ?, ?, 'open')",
        (user_id, username, category, message),
    )
    fb_id = cur.lastrowid
    add_feedback_message(fb_id, "user", user_id, message)
    _conn.commit()
    return fb_id


def get_user_active_feedback(user_id: int) -> dict | None:
    assert _conn is not None
    row = _conn.execute(
        "SELECT * FROM feedback WHERE user_id = ? AND status != 'closed' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_feedback(feedback_id: int) -> dict | None:
    assert _conn is not None
    row = _conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    return _row_to_dict(row)


def add_feedback_message(feedback_id: int, sender: str, sender_id: int, message: str) -> int:
    assert _conn is not None
    cur = _conn.execute(
        "INSERT INTO feedback_messages (feedback_id, sender, sender_id, message) VALUES (?, ?, ?, ?)",
        (feedback_id, sender, sender_id, message),
    )
    if sender == "admin":
        _conn.execute(
            "UPDATE feedback SET admin_reply = ?, status = 'replied', replied_at = datetime('now') WHERE id = ?",
            (message, feedback_id),
        )
    else:
        _conn.execute(
            "UPDATE feedback SET message = ?, status = 'open' WHERE id = ?",
            (message, feedback_id),
        )
    _conn.commit()
    return cur.lastrowid


def get_feedback_messages(feedback_id: int) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT * FROM feedback_messages WHERE feedback_id = ? ORDER BY id ASC",
        (feedback_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_feedback(status: str | None = None, limit: int = 50) -> list[dict]:
    assert _conn is not None
    if status and status.strip():
        rows = _conn.execute(
            "SELECT * FROM feedback WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status.strip(), limit),
        ).fetchall()
    else:
        rows = _conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def reply_feedback(feedback_id: int, admin_reply: str, admin_id: int = 0) -> bool:
    assert _conn is not None
    add_feedback_message(feedback_id, "admin", admin_id, admin_reply)
    return True


def close_feedback(feedback_id: int) -> bool:
    assert _conn is not None
    cur = _conn.execute(
        "UPDATE feedback SET status = 'closed' WHERE id = ?",
        (feedback_id,),
    )
    _conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Purchase Details
# ---------------------------------------------------------------------------

def save_purchase_detail(order_id: str, user_id: int, product_name: str, accounts_delivered: str) -> None:
    assert _conn is not None
    _conn.execute(
        "INSERT INTO purchase_details (order_id, user_id, product_name, accounts_delivered) VALUES (?, ?, ?, ?)",
        (order_id, user_id, product_name, accounts_delivered),
    )
    _conn.commit()


def get_purchase_detail(order_id: str) -> dict | None:
    assert _conn is not None
    row = _conn.execute(
        "SELECT * FROM purchase_details WHERE order_id = ?",
        (order_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_user_purchase_details(user_id: int, limit: int = 20) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT * FROM purchase_details WHERE user_id = ? ORDER BY delivered_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# User Management (Admin)
# ---------------------------------------------------------------------------

def get_all_users_detail(limit: int = 100, offset: int = 0) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        """SELECT u.*, 
           (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_orders,
           (SELECT COALESCE(SUM(total), 0) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_spent
           FROM users u ORDER BY u.last_seen DESC LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_user_detail(user_id: int) -> dict | None:
    assert _conn is not None
    row = _conn.execute(
        """SELECT u.*,
           (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_orders,
           (SELECT COALESCE(SUM(total), 0) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_spent
           FROM users u WHERE u.user_id = ?""",
        (user_id,),
    ).fetchone()
    return _row_to_dict(row)


def ban_user(user_id: int, reason: str = "") -> bool:
    assert _conn is not None
    cur = _conn.execute(
        "UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?",
        (reason, user_id),
    )
    _conn.commit()
    return cur.rowcount > 0


def unban_user(user_id: int) -> bool:
    assert _conn is not None
    cur = _conn.execute(
        "UPDATE users SET is_banned = 0, ban_reason = '' WHERE user_id = ?",
        (user_id,),
    )
    _conn.commit()
    return cur.rowcount > 0


def is_user_banned(user_id: int) -> bool:
    assert _conn is not None
    row = _conn.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row and row["is_banned"])


def search_users(query: str) -> list[dict]:
    assert _conn is not None
    q = query.strip()
    if q.isdigit():
        rows = _conn.execute(
            """SELECT u.*,
               (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_orders,
               (SELECT COALESCE(SUM(total), 0) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_spent
               FROM users u WHERE u.user_id = ? LIMIT 20""",
            (int(q),),
        ).fetchall()
    else:
        clean = q.lstrip("@")
        rows = _conn.execute(
            """SELECT u.*,
               (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_orders,
               (SELECT COALESCE(SUM(total), 0) FROM orders WHERE user_id = u.user_id AND status = 'paid') as total_spent
               FROM users u WHERE u.username LIKE ? OR u.first_name LIKE ? LIMIT 20""",
            (f"%{clean}%", f"%{clean}%"),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Bot Settings (key-value store)
# ---------------------------------------------------------------------------

def get_setting(key: str, default: str = "") -> str:
    assert _conn is not None
    row = _conn.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    assert _conn is not None
    _conn.execute(
        "INSERT INTO bot_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    _conn.commit()


def get_commission_percent() -> int:
    val = get_setting("commission_percent", "10")
    try:
        p = int(val)
        return max(1, min(50, p))
    except ValueError:
        return 10


def get_min_withdrawal() -> int:
    val = get_setting("min_withdrawal", "50000")
    try:
        return max(10000, int(val))
    except ValueError:
        return 50000


# ---------------------------------------------------------------------------
# Referral Commissions
# ---------------------------------------------------------------------------

def add_commission(referrer_id: int, referred_id: int, order_id: str,
                   order_amount: int, commission_percent: int, commission_amount: int) -> int:
    assert _conn is not None
    cur = _conn.execute(
        """INSERT INTO referral_commissions (referrer_id, referred_id, order_id, order_amount, commission_percent, commission_amount)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (referrer_id, referred_id, order_id, order_amount, commission_percent, commission_amount),
    )
    _conn.commit()
    return cur.lastrowid


def has_commission_for_order(order_id: str) -> bool:
    assert _conn is not None
    row = _conn.execute("SELECT 1 FROM referral_commissions WHERE order_id = ? LIMIT 1", (order_id,)).fetchone()
    return row is not None


def get_user_commission_balance(user_id: int) -> int:
    assert _conn is not None
    row = _conn.execute(
        "SELECT COALESCE(SUM(commission_amount), 0) as total FROM referral_commissions WHERE referrer_id = ? AND status = 'earned'",
        (user_id,),
    ).fetchone()
    total_earned = row["total"] if row else 0

    row2 = _conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM withdrawal_requests WHERE user_id = ? AND status IN ('pending', 'approved')",
        (user_id,),
    ).fetchone()
    withdrawn = row2["total"] if row2 else 0
    return max(0, total_earned - withdrawn)


def get_user_total_commission(user_id: int) -> int:
    assert _conn is not None
    row = _conn.execute(
        "SELECT COALESCE(SUM(commission_amount), 0) as total FROM referral_commissions WHERE referrer_id = ?",
        (user_id,),
    ).fetchone()
    return row["total"] if row else 0


def get_user_commissions(user_id: int, limit: int = 20) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        """SELECT rc.*, u.username as referred_username, u.first_name as referred_name
           FROM referral_commissions rc
           LEFT JOIN users u ON rc.referred_id = u.user_id
           WHERE rc.referrer_id = ? ORDER BY rc.created_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Withdrawal Requests
# ---------------------------------------------------------------------------

def create_withdrawal_request(user_id: int, amount: int, bank_name: str,
                               account_number: str, account_name: str) -> int:
    assert _conn is not None
    cur = _conn.execute(
        """INSERT INTO withdrawal_requests (user_id, amount, bank_name, account_number, account_name)
        VALUES (?, ?, ?, ?, ?)""",
        (user_id, amount, bank_name, account_number, account_name),
    )
    _conn.commit()
    return cur.lastrowid


def get_pending_withdrawals() -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        """SELECT wr.*, u.username, u.first_name
           FROM withdrawal_requests wr
           LEFT JOIN users u ON wr.user_id = u.user_id
           WHERE wr.status = 'pending' ORDER BY wr.created_at DESC""",
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_withdrawals(limit: int = 50) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        """SELECT wr.*, u.username, u.first_name
           FROM withdrawal_requests wr
           LEFT JOIN users u ON wr.user_id = u.user_id
           ORDER BY wr.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_user_withdrawals(user_id: int, limit: int = 20) -> list[dict]:
    assert _conn is not None
    rows = _conn.execute(
        "SELECT * FROM withdrawal_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def process_withdrawal(request_id: int, status: str, admin_note: str = "") -> bool:
    assert _conn is not None
    cur = _conn.execute(
        "UPDATE withdrawal_requests SET status = ?, admin_note = ?, processed_at = datetime('now') WHERE id = ?",
        (status, admin_note, request_id),
    )
    _conn.commit()
    return cur.rowcount > 0


def get_withdrawal_request(request_id: int) -> dict | None:
    assert _conn is not None
    row = _conn.execute(
        """SELECT wr.*, u.username, u.first_name
           FROM withdrawal_requests wr
           LEFT JOIN users u ON wr.user_id = u.user_id
           WHERE wr.id = ?""",
        (request_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_pending_preorders() -> list[dict]:
    """Get orders that are paid and belong to a preorder product, but not yet delivered."""
    assert _conn is not None
    rows = _conn.execute(
        """SELECT o.*, p.name as product_name, p.description as product_desc
           FROM orders o
           JOIN products p ON o.product_id = p.id
           WHERE (o.status = 'paid' OR o.status = 'preorder_paid')
             AND p.stock_type = 'preorder'
             AND o.id NOT IN (SELECT order_id FROM purchase_details)
           ORDER BY o.created_at ASC"""
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_chart_analytics() -> dict:
    """Calculate realtime sales chart analytics (hourly, daily, monthly, yearly)."""
    assert _conn is not None
    from datetime import datetime, timedelta

    # 1. Hourly (Today 00:00 - 23:00)
    hourly_rows = _conn.execute("""
        SELECT strftime('%H', paid_at) as hr, COALESCE(SUM(total), 0) as rev
        FROM orders
        WHERE status = 'paid' AND date(paid_at) = date('now')
        GROUP BY hr ORDER BY hr ASC
    """).fetchall()
    hourly_map = {r["hr"]: r["rev"] for r in hourly_rows if r["hr"]}
    hourly_labels = [f"{h:02d}:00" for h in range(24)]
    hourly_data = [hourly_map.get(f"{h:02d}", 0) for h in range(24)]

    # 2. Daily (Last 7 days)
    daily_rows = _conn.execute("""
        SELECT date(paid_at) as dt, COALESCE(SUM(total), 0) as rev
        FROM orders
        WHERE status = 'paid' AND paid_at >= datetime('now', '-6 days', 'start of day')
        GROUP BY dt ORDER BY dt ASC
    """).fetchall()
    daily_map = {r["dt"]: r["rev"] for r in daily_rows if r["dt"]}
    today_dt = datetime.now()
    daily_labels = []
    daily_data = []
    for i in range(6, -1, -1):
        d_obj = today_dt - timedelta(days=i)
        d_str = d_obj.strftime("%Y-%m-%d")
        d_label = d_obj.strftime("%d %b")
        daily_labels.append(d_label)
        daily_data.append(daily_map.get(d_str, 0))

    # 3. Monthly (Current Year Jan..Dec)
    monthly_rows = _conn.execute("""
        SELECT strftime('%m', paid_at) as mth, COALESCE(SUM(total), 0) as rev
        FROM orders
        WHERE status = 'paid' AND strftime('%Y', paid_at) = strftime('%Y', 'now')
        GROUP BY mth ORDER BY mth ASC
    """).fetchall()
    monthly_map = {r["mth"]: r["rev"] for r in monthly_rows if r["mth"]}
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    monthly_labels = month_names
    monthly_data = [monthly_map.get(f"{m:02d}", 0) for m in range(1, 13)]

    # 4. Yearly (Last 5 Years)
    yearly_rows = _conn.execute("""
        SELECT strftime('%Y', paid_at) as yr, COALESCE(SUM(total), 0) as rev
        FROM orders
        WHERE status = 'paid'
        GROUP BY yr ORDER BY yr ASC
    """).fetchall()
    yearly_map = {r["yr"]: r["rev"] for r in yearly_rows if r["yr"]}
    curr_yr = today_dt.year
    yearly_labels = [str(y) for y in range(curr_yr - 4, curr_yr + 1)]
    yearly_data = [yearly_map.get(str(y), 0) for y in range(curr_yr - 4, curr_yr + 1)]

    return {
        "jam": {"labels": hourly_labels, "data": hourly_data},
        "hari": {"labels": daily_labels, "data": daily_data},
        "bulan": {"labels": monthly_labels, "data": monthly_data},
        "tahun": {"labels": yearly_labels, "data": yearly_data},
    }

