import pytest
from fastapi.testclient import TestClient


class TestTransactions:     #тесты транзакций

#==== Добавление транзакций=====================

#валидные данные

    def test_create_transaction_valid(self, client: TestClient):
        data = {
            "type": "income",
            "amount": 50000,
            "category": "Salary",
            "transaction_date": "2026-07-26",
            "comment": "July salary"
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["type"] == data["type"]
        assert result["amount"] == data["amount"]
        assert result["category"] == data["category"]
        assert result["transaction_date"] == data["transaction_date"]
        assert "id" in result
        assert "created_at" in result

#невалидные данные

    def test_create_transaction_invalid_type(self, client: TestClient):
        data = {
            "type": "invalid",  #невалидный тип
            "amount": 1000,
            "category": "Test",
            "transaction_date": "2026-07-26"
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 422

    def test_create_transaction_negative_amount(self, client: TestClient):
        data = {
            "type": "expense",
            "amount": -100, #отрицательная сумма
            "category": "Test",
            "transaction_date": "2026-07-26"
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 422


    def test_create_transaction_future_date(self, client: TestClient):
        data = {
            "type": "income",
            "amount": 1000,
            "category": "Test",
            "transaction_date": "2099-07-26",       #дата из будущего
            "comment": "Test"
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 400
        assert "future" in response.json()["detail"]

#======== показать все транзакции =================

    def test_get_all_transactions_empty(self, client: TestClient):
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_transactions_with_data(self, client: TestClient, sample_transactions):
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 3
        assert result[0]["category"] == "Food"
        assert result[1]["category"] == "Rent"
        assert result[2]["category"] == "Salary"

    def test_get_all_transactions_with_filter_category(self, client: TestClient, sample_transactions):
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

        response = client.get("/api/v1/transactions?category=Food")
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["category"] == "Food"

    def test_get_all_transactions_with_filter_date_range(self, client: TestClient, sample_transactions):
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

        response = client.get("/api/v1/transactions?start_date=2026-07-27&end_date=2026-07-27")
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["transaction_date"] == "2026-07-27"

#======== показать транзакцию по id ===========

    def test_get_transaction_by_id_found(self, client: TestClient):
        data = {
            "type": "income",
            "amount": 50000,
            "category": "Salary",
            "transaction_date": "2026-07-26"
        }
        create_response = client.post("/api/v1/transactions", json=data)
        transaction_id = create_response.json()["id"]

        response = client.get(f"/api/v1/transactions/{transaction_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == transaction_id
        assert result["amount"] == 50000

    #невалидный id
    def test_get_transaction_by_id_not_found(self, client: TestClient):
        response = client.get("/api/v1/transactions/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

#============= обновление транзакции =============

    def test_update_transaction_valid(self, client: TestClient):
        data = {
            "type": "expense",
            "amount": 1000,
            "category": "Test",
            "transaction_date": "2026-07-26"
        }
        create_response = client.post("/api/v1/transactions", json=data)
        transaction_id = create_response.json()["id"]

        update_data = {"amount": 2000, "comment": "Updated"}
        response = client.patch(f"/api/v1/transactions/{transaction_id}", json=update_data)
        assert response.status_code == 200
        result = response.json()
        assert result["amount"] == 2000
        assert result["comment"] == "Updated"
        assert result["type"] == data["type"]

    #обновление несуществующей транзакции

    def test_update_transaction_not_found(self, client: TestClient):
        response = client.patch("/api/v1/transactions/999", json={"amount": 1000})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_transaction_future_date(self, client: TestClient):
        data = {
            "type": "expense",
            "amount": 1000,
            "category": "Test",
            "transaction_date": "2026-07-26"        #обновление на дату из будущего
        }
        create_response = client.post("/api/v1/transactions", json=data)
        transaction_id = create_response.json()["id"]

        response = client.patch(f"/api/v1/transactions/{transaction_id}", json={"transaction_date": "2099-07-26"})
        assert response.status_code == 400
        assert "future" in response.json()["detail"]


#======= тест удаления===============

    def test_delete_transaction_success(self, client: TestClient):
        data = {
            "type": "income",
            "amount": 1000,
            "category": "Test",
            "transaction_date": "2026-07-26"
        }
        create_response = client.post("/api/v1/transactions", json=data)
        transaction_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/transactions/{transaction_id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/transactions/{transaction_id}")
        assert get_response.status_code == 404

    #несуществующая транзакция
    def test_delete_transaction_not_found(self, client: TestClient):
        response = client.delete("/api/v1/transactions/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

#======================== полный сценарий ============

    def test_full_scrypt(self, client: TestClient):
        """
        Полный сценарий:
        1. Создать 3 транзакции
        2. Получить список
        3. Посчитать статистику
        4. Экспортировать отчёт
        """
            # 1
        transactions_data = [
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

        created_ids = []
        for data in transactions_data:
            response = client.post("/api/v1/transactions", json=data)
            assert response.status_code == 201
            result = response.json()
            assert "id" in result
            created_ids.append(result["id"])

        assert len(created_ids) == 3

        # 2
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) == 3

        response_ids = [t["id"] for t in transactions]
        assert sorted(response_ids) == sorted(created_ids)

        # 3
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        stats = response.json()

        assert stats["total_income"] == 50000.0
        assert stats["total_expense"] == 18000.0
        assert stats["balance"] == 32000.0
        assert stats["transactions_count"] == 3

        assert "Salary" in stats["by_category"]
        assert "Rent" in stats["by_category"]
        assert "Food" in stats["by_category"]
        assert stats["by_category"]["Salary"]["income"] == 50000.0
        assert stats["by_category"]["Rent"]["expense"] == 15000.0
        assert stats["by_category"]["Food"]["expense"] == 3000.0

        # 4
        response = client.get("/api/v1/export")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=transactions_" in response.headers["content-disposition"]

        content = response.text
        import csv
        import io
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 3

        rows_sorted = sorted(rows, key=lambda x: float(x["amount"]))
        assert rows_sorted[0]["type"] == "expense"
        assert float(rows_sorted[0]["amount"]) == 3000.0
        assert rows_sorted[0]["category"] == "Food"
        assert rows_sorted[1]["type"] == "expense"
        assert float(rows_sorted[1]["amount"]) == 15000.0
        assert rows_sorted[1]["category"] == "Rent"
        assert rows_sorted[2]["type"] == "income"
        assert float(rows_sorted[2]["amount"]) == 50000.0
        assert rows_sorted[2]["category"] == "Salary"