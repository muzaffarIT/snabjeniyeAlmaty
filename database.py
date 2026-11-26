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

# Фото выполненной работы: без него заявка не закрывается
_exec("ALTER TABLE requests ADD COLUMN IF NOT EXISTS done_photo_file_id TEXT")

# Сообщения бота «пришлите фото» → какая заявка и какая карточка в группе
_exec("""
CREATE TABLE IF NOT EXISTS done_prompts (
    prompt_message_id BIGINT PRIMARY KEY,
    req_id INTEGER NOT NULL,
    card_message_id BIGINT NOT NULL,
    card_has_caption BOOLEAN NOT NULL
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


def close_request(req_id: int, photo_file_id: str) -> bool:
    """Закрывает заявку с фото результата. False — уже была закрыта (например, второе фото из альбома)."""
    row = _exec(
        """
        UPDATE requests SET status = 'Решено', done_photo_file_id = %s
        WHERE id = %s AND status <> 'Решено'
        RETURNING id
        """,
        (photo_file_id, req_id),
        fetch="one",
    )
    return row is not None


def get_request(req_id: int):
    """(branch_id, category_id, urgency, description, status) или None."""
    return _exec(
        """
        SELECT branch_id, category_id, urgency, description, status
        FROM requests
        WHERE id = %s
        """,
        (req_id,),
        fetch="one",
    )


def add_done_prompt(prompt_message_id: int, req_id: int, card_message_id: int, card_has_caption: bool):
    _exec(
        """
        INSERT INTO done_prompts (prompt_message_id, req_id, card_message_id, card_has_caption)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (prompt_message_id) DO NOTHING
        """,
        (prompt_message_id, req_id, card_message_id, card_has_caption),
    )


def get_done_prompt(prompt_message_id: int):
    """(req_id, card_message_id, card_has_caption) или None."""
    return _exec(
        """
        SELECT req_id, card_message_id, card_has_caption
        FROM done_prompts
        WHERE prompt_message_id = %s
        """,
        (prompt_message_id,),
        fetch="one",
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
        SELECT id, description, status, created_at
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
        SELECT id, description, branch_id, created_at
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


def get_request_author(req_id: int):
    """Возвращает (user_id, branch_id, category_id, description) автора заявки."""
    return _exec(
        """
        SELECT user_id, branch_id, category_id, description
        FROM requests
        WHERE id = %s
        """,
        (req_id,),
        fetch="one",
    )


def get_requests_by_category(category_id: int):
    return _exec(
        """
        SELECT id, description, status, created_at
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
