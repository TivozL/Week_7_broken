import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.settings import settings


@pytest.fixture(scope="function")
def test_db():

    test_db_dir = Path("test_data")
    test_db_dir.mkdir(exist_ok=True)
    test_db_path = test_db_dir / "test_app.db"  # тестовая БД
    original_path = settings.database_path      #сохранение исходного пути
    settings.database_path = str(test_db_path)


    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS transactions") #удаление если уже есть

    cursor.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            amount REAL NOT NULL CHECK(amount > 0),
            category TEXT NOT NULL,
            transaction_date DATE NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX idx_transactions_category ON transactions(category)")
    cursor.execute("CREATE INDEX idx_transactions_transaction_date ON transactions(transaction_date)")

    conn.commit()
    conn.close()

    yield

    settings.database_path = original_path      #восстанавление исходного пути


@pytest.fixture(scope="function")
def client(test_db):
    return TestClient(app)


@pytest.fixture(scope="function")
def sample_transactions():
    return [
        {
            "type": "income",
            "amount": 50000,
            "category": "Salary",
            "transaction_date": "2026-07-26",
            "comment": "July salary"
        },
        {
            "type": "expense",
            "amount": 15000,
            "category": "Rent",
            "transaction_date": "2026-07-26",
            "comment": "Monthly rent"
        },
        {
            "type": "expense",
            "amount": 3000,
            "category": "Food",
            "transaction_date": "2026-07-27",
            "comment": "Groceries"
        }
    ]