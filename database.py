import threading
from datetime import datetime

import psycopg2
from psycopg2.extras import DictCursor

from config import DATABASE_URL


# ================== CONNECTION ==================

_lock = threading.Lock()


def _connect():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.autocommit = True
    return conn


_conn = _connect()


def _cursor():
    """Return a live cursor, reconnecting if the connection dropped."""
    global _conn
    try:
        if _conn.closed:
            _conn = _connect()
    except Exception:
        _conn = _connect()
    return _conn.cursor()


def _exec(query: str, params: tuple = (), fetch: str | None = None):
    """Run a query with a single auto-reconnect retry on connection errors."""
    global _conn
    with _lock:
        for attempt in range(2):
            try:
                cur = _cursor()
                cur.execute(query, params)
                if fetch == "one":
                    row = cur.fetchone()
                elif fetch == "all":
                    row = cur.fetchall()
                else:
                    row = None
                cur.close()
                return row
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                if attempt == 1:
                    raise
                _conn = _connect()


# ================== TABLES ==================

_exec("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    branch_id INTEGER NOT NULL
)
""")

_exec("""
CREATE TABLE IF NOT EXISTS requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    branch_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    urgency TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deadline TEXT,
    group_message_id BIGINT
)
""")


# ================== USERS ==================

def set_user_branch(user_id: int, branch_id: int):
    _exec(
        """
        INSERT INTO users (user_id, branch_id) VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET branch_id = EXCLUDED.branch_id
        """,
        (user_id, branch_id),
    )


def get_user_branch(user_id: int):
    row = _exec(
        "SELECT branch_id FROM users WHERE user_id = %s",
        (user_id,),
        fetch="one",
    )
    return row[0] if row else None


# ================== REQUESTS ==================

def add_request(data: tuple):
    """
    data:
    (user_id, branch_id, category_id, urgency,
     description, status, created_at, deadline)
    """
    row = _exec(
        """
        INSERT INTO requests
        (user_id, branch_id, category_id, urgency,
         description, status, created_at, deadline)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        data,
        fetch="one",
    )
    return row[0]


def update_status(req_id: int, status: str):
    _exec(
        "UPDATE requests SET status = %s WHERE id = %s",
        (status, req_id),
    )


def set_group_msg(req_id: int, msg_id: int):
    _exec(
        "UPDATE requests SET group_message_id = %s WHERE id = %s",
        (msg_id, req_id),
    )


# ================== SELECTS ==================

def get_requests_by_branch(branch_id: int):
    return _exec(
        """
        SELECT id, description, status
        FROM requests
        WHERE branch_id = %s
        ORDER BY id DESC
        """,
        (branch_id,),
        fetch="all",
    )


def get_requests_by_status(status: str):
    return _exec(
        """
        SELECT id, description, branch_id
        FROM requests
        WHERE status = %s
        ORDER BY id DESC
        """,
        (status,),
        fetch="all",
    )


def get_overdue_requests():
    return _exec(
        """
        SELECT id, description, branch_id
        FROM requests
        WHERE status != 'Решено'
          AND deadline IS NOT NULL
          AND deadline < %s
        ORDER BY deadline ASC
        """,
        (datetime.now().isoformat(),),
        fetch="all",
    )


def get_all_requests():
    return _exec(
        """
        SELECT id, user_id, branch_id, category_id,
               urgency, description, status,
               created_at, deadline
        FROM requests
        ORDER BY id DESC
        """,
        fetch="all",
    )


def get_requests_by_category(category_id: int):
    return _exec(
        """
        SELECT id, description, status
        FROM requests
        WHERE category_id = %s
        ORDER BY id DESC
        """,
        (category_id,),
        fetch="all",
    )


STATUS_NEW = "Новая"
STATUS_WORK = "В обработке"
STATUS_DONE = "Решено"
