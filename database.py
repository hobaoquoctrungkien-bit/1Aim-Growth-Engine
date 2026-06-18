import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path("data/growth_engine.db")


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT,
        type TEXT,
        strength TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        full_name TEXT NOT NULL,
        email TEXT,
        wechat TEXT,
        phone TEXT,
        title TEXT,
        source TEXT,
        relationship_score INTEGER DEFAULT 5,
        last_touch_at TEXT,
        next_touch_at TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        title TEXT NOT NULL,
        route TEXT,
        commodity TEXT,
        volume TEXT,
        mode TEXT,
        status TEXT DEFAULT 'new',
        inquiry_text TEXT,
        inquiry_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(contact_id) REFERENCES contacts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER,
        quote_no TEXT,
        quote_date TEXT,
        valid_until TEXT,
        currency TEXT DEFAULT 'USD',
        sell_amount REAL,
        status TEXT DEFAULT 'draft',
        follow_up_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        opportunity_id INTEGER,
        quotation_id INTEGER,
        activity_type TEXT,
        summary TEXT,
        activity_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        opportunity_id INTEGER,
        quotation_id INTEGER,
        task_type TEXT,
        title TEXT NOT NULL,
        channel TEXT,
        campaign_name TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'open',
        priority TEXT DEFAULT 'normal',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT
    )
    """)

    try:
        cur.execute("ALTER TABLE tasks ADD COLUMN channel TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE tasks ADD COLUMN campaign_name TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def create_inquiry(inquiry_text):
    today = date.today().isoformat()
    clean_text = inquiry_text.strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO opportunities (title, inquiry_text, status, inquiry_date)
        VALUES (?, ?, ?, ?)
        """,
        (clean_text[:80], clean_text, "new", today),
    )

    opportunity_id = cur.lastrowid

    cur.execute(
        """
        INSERT INTO tasks (
            opportunity_id,
            task_type,
            title,
            due_date,
            status,
            priority
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            opportunity_id,
            "prepare_quote",
            "Prepare quote: " + clean_text[:60],
            today,
            "open",
            "high",
        ),
    )

    cur.execute(
        """
        INSERT INTO activities (opportunity_id, activity_type, summary)
        VALUES (?, ?, ?)
        """,
        (
            opportunity_id,
            "inquiry_received",
            "New inquiry received",
        ),
    )

    conn.commit()
    conn.close()


def get_open_tasks():
    conn = get_connection()

    tasks = conn.execute(
        """
        SELECT *
        FROM tasks
        WHERE status = 'open'
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                ELSE 3
            END,
            due_date,
            created_at DESC
        """
    ).fetchall()

    conn.close()
    return tasks


def get_task_counts_by_type():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT task_type, COUNT(*) AS task_count
        FROM tasks
        WHERE status = 'open'
        GROUP BY task_type
        """
    ).fetchall()

    conn.close()
    return {
        row["task_type"]: row["task_count"]
        for row in rows
    }
