import sqlite3
from sqlite3 import Connection
from app.settings import settings
from app.logger import db_logger
from pathlib import Path


def get_connection() -> Connection:     #создание и возврат подключения к БД
    try:
        db_dir = Path(settings.database_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(settings.database_path)
        conn.row_factory = sqlite3.Row
        db_logger.debug(f"Database connection established: {settings.database_path}")
        return conn
    except Exception as e:
        db_logger.error(f"Failed to connect to database: {e}")
        raise


def init_db():
    db_logger.info(f"Initializing database at: {settings.database_path}")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                transaction_date DATE NOT NULL, 
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_transaction_date ON transactions(transaction_date)")

        conn.commit()
        conn.close()
        db_logger.info("Database initialized successfully")
    except Exception as e:
        db_logger.error(f"Database initialization failed: {e}")
        raise