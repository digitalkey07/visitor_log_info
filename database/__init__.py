from genericpath import isfile
import os
import sqlite3
from config import DATABASE_NAME


DATABASE = os.path.join(
    os.environ.get("DATA_DIR", "."),
    DATABASE_NAME
)
# if os.path.isfile(DATABASE):
#     os.remove(DATABASE)
# os.makedirs(os.path.dirname(DATABASE) or ".", exist_ok=True)

#======================================
#DATABASE CONNECTION FUNCTION
#======================================
def get_db():
    conn = sqlite3.connect(DATABASE)
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
                user_type TEXT NOT NULL DEFAULT 'user',
                "shared_id" TEXT NOT NULL UNIQUE
            )
        """)    

#======================================
#DATABASE MIGRATION FUNCTION
#======================================
def migrate_database():
    with get_db() as conn:
        existing_visitor_logs = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(visitor_logs)"
            ).fetchall()
        }
        existing_users = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        visitor_new_columns = {
            "visitor_token": "TEXT",
            "device_type": "TEXT",
            "browser": "TEXT",
            "operating_system": "TEXT",
            "latitude": "REAL",
            "longitude": "REAL",
            "accuracy": "REAL"
        }
        users_new_columns = {
            "shared_id": "TEXT"
        }

        for column, data_type in visitor_new_columns.items():
            if column not in existing_visitor_logs:
                conn.execute(
                    f"ALTER TABLE visitor_logs "
                    f"ADD COLUMN {column} {data_type}"
                )
        for column ,data_type in users_new_columns.items():
            if column not in existing_users:
                conn.execute(
                    f"ALTER TABLE users "
                    f"ADD COLUMN {column} {data_type}"
                )
         # shared_id ko unique banane ke liye index
        # conn.execute("""
        #     CREATE UNIQUE INDEX IF NOT EXISTS
        #     idx_users_shared_id
        #     ON users(shared_id)
        # """)