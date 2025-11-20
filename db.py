import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = "hms.db"
SCHEMA_FILE = "schema.sql"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name: row["email"]
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """
    Create database tables from schema.sql and seed default data
    on first run.
    """
    first_time = not Path(DB_PATH).exists()

    # Create/ensure tables
    conn = get_db()
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
        conn.executescript(sql)
    conn.commit()
    conn.close()

    if first_time:
        seed_default_data()


def seed_default_data():
    """
    Insert default admin user.
    Called only on first DB creation.
    """
    conn = get_db()
    cur = conn.cursor()

    # Default admin
    admin_email = "admin@hospital.com"
    admin_password = "admin123"
    password_hash = generate_password_hash(admin_password)

    cur.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    existing_admin = cur.fetchone()

    if not existing_admin:
        cur.execute(
            "INSERT INTO users (email, password_hash, role, status) "
            "VALUES (?, ?, 'admin', 'active')",
            (admin_email, password_hash),
        )
        print(f"[DB] Created default admin: {admin_email} / {admin_password}")
    else:
        print("[DB] Admin already exists, skipping admin creation.")

    conn.commit()
    conn.close()
    print("[DB] Default admin seeded.")
