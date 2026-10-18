
import sqlite3
from config import DATABASE_NAME

#======================================
#DATABASE CONNECTION FUNCTION
#======================================
def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

#======================================
#DATABASE TABLE CREATION FUNCTION
#======================================
def create_table():
    with get_db() as conn:

        # Visitor tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visitor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT,
                user_agent TEXT,
                page_path TEXT,
                visited_at TEXT,
                visitor_token TEXT UNIQUE,
                device_type TEXT,
                browser TEXT,
                operating_system TEXT,
                latitude REAL,
                longitude REAL,
                accuracy REAL
            )
        """)

        # Users / Admin login table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                user_type TEXT NOT NULL DEFAULT 'user'
            )
        """)

#======================================
#DATABASE MIGRATION FUNCTION
#======================================
def migrate_database():
    with get_db() as conn:
        existing = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(visitor_logs)"
            ).fetchall()
        }

        new_columns = {
            "visitor_token": "TEXT",
            "device_type": "TEXT",
            "browser": "TEXT",
            "operating_system": "TEXT",
            "latitude": "REAL",
            "longitude": "REAL",
            "accuracy": "REAL"
        }

        for column, data_type in new_columns.items():
            if column not in existing:
                conn.execute(
                    f"ALTER TABLE visitor_logs "
                    f"ADD COLUMN {column} {data_type}"
                )
