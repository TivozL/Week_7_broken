from fastapi.testclient import TestClient


class TestTransactions:

    # ============ CREATE ============

    def test_create_transaction_valid(self, client: TestClient, sample_transaction):        #Создание транзакции с валидными данными
        response = client.post("/api/v1/transactions", json=sample_transaction)

        assert response.status_code == 201
        result = response.json()
        assert result["type"] == sample_transaction["type"]
        assert result["amount"] == sample_transaction["amount"]
        assert result["category"] == sample_transaction["category"]
        assert result["transaction_date"] == sample_transaction["transaction_date"]
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_create_transaction_invalid_type(self, client: TestClient):     #Создание с невалидным типом
        data = {
            "type": "invalid",
            "amount": 1000,
            "category": "Test",
            "transaction_date": "2026-07-26"
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 422

    def test_create_transaction_negative_amount(self, client: TestClient):      #Создание с отрицательной суммой
        data = {
            "type": "expense",
            "amount": -100,
            "category": "Test",
            "transaction_date": "2026-07-26"
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 422

    def test_create_transaction_zero_amount(self, client: TestClient):      #Создание с нулевой суммой
        data = {
            "type": "income",
            "amount": 0,
            "category": "Test",
            "transaction_date": "2026-07-26"
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 422

    def test_create_transaction_missing_fields(self, client: TestClient):       #Создание с отсутствующими обязательными полями
        data = {
            "type": "income",
            "amount": 1000
            # нет category и transaction_date
        }
        response = client.post("/api/v1/transactions", json=data)
        assert response.status_code == 422

    # ============ LIST ============

    def test_get_transactions_empty(self, client: TestClient):      #Получение списка когда нет транзакций
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_transactions_with_data(self, client: TestClient, sample_transactions):     #Получение списка с данными
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 3

        # Проверяем сортировку (по умолчанию по created_at DESC)
        assert result[0]["category"] == "Food"
        assert result[1]["category"] == "Rent"
        assert result[2]["category"] == "Salary"

    def test_get_transactions_filter_by_category(self, client: TestClient, sample_transactions):    #Фильтрация по категории
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

        response = client.get("/api/v1/transactions?category=Food")
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["category"] == "Food"

    def test_get_transactions_filter_by_date_range(self, client: TestClient, sample_transactions):      #Фильтрация по диапазону дат
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

        response = client.get("/api/v1/transactions?start_date=2026-07-27&end_date=2026-07-27")
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["transaction_date"] == "2026-07-27"

    def test_get_transactions_pagination(self, client: TestClient, sample_transactions):
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

        response = client.get("/api/v1/transactions?skip=0&limit=2")
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 2

    # ============ GET BY ID ============

    def test_get_transaction_by_id_found(self, client: TestClient, sample_transaction):     #получение по id
        create_response = client.post("/api/v1/transactions", json=sample_transaction)
        transaction_id = create_response.json()["id"]

        response = client.get(f"/api/v1/transactions/{transaction_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == transaction_id
        assert result["amount"] == sample_transaction["amount"]
        assert result["category"] == sample_transaction["category"]

    def test_get_transaction_by_id_not_found(self, client: TestClient):     #по несуществующей id
        response = client.get("/api/v1/transactions/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    # ============ UPDATE ============

    def test_update_transaction_valid(self, client: TestClient, sample_transaction):
        create_response = client.post("/api/v1/transactions", json=sample_transaction)
        transaction_id = create_response.json()["id"]

        update_data = {"amount": 200.0, "comment": "Updated comment"}
        response = client.patch(f"/api/v1/transactions/{transaction_id}", json=update_data)

        assert response.status_code == 200
        result = response.json()
        assert result["amount"] == 200.0
        assert result["comment"] == "Updated comment"
        assert result["category"] == sample_transaction["category"]  # не изменилось

    def test_update_transaction_partial(self, client: TestClient, sample_transaction):
        create_response = client.post("/api/v1/transactions", json=sample_transaction)
        transaction_id = create_response.json()["id"]

        response = client.patch(f"/api/v1/transactions/{transaction_id}", json={"category": "Bonus"})

        assert response.status_code == 200
        result = response.json()
        assert result["category"] == "Bonus"
        assert result["amount"] == sample_transaction["amount"]  # не изменилось

    def test_update_transaction_not_found(self, client: TestClient):        #Обновление несуществующей транзакции
        response = client.patch("/api/v1/transactions/999", json={"amount": 1000})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_transaction_future_date(self, client: TestClient, sample_transaction):      #Обновление на дату из будущего
        create_response = client.post("/api/v1/transactions", json=sample_transaction)
        transaction_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/transactions/{transaction_id}",
            json={"transaction_date": "2099-07-26"}
        )
        assert response.status_code == 400
        assert "future" in response.json()["detail"].lower()

    # ============ DELETE ============

    def test_delete_transaction_success(self, client: TestClient, sample_transaction):      #успешное удаление
        create_response = client.post("/api/v1/transactions", json=sample_transaction)
        transaction_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/transactions/{transaction_id}")
        assert response.status_code == 204

        # Проверяем, что транзакция удалена
        get_response = client.get(f"/api/v1/transactions/{transaction_id}")
        assert get_response.status_code == 404

    def test_delete_transaction_not_found(self, client: TestClient):    #несуществующая транзакция
        response = client.delete("/api/v1/transactions/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    # ============ STATS ============

    def test_stats_with_data(self, client: TestClient, sample_transactions):    #Статистика с данными
        for t in sample_transactions:
            client.post("/api/v1/transactions", json=t)

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

    def test_stats_empty(self, client: TestClient):     #стата по пустому списку
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        stats = response.json()

        assert stats["total_income"] == 0.0
        assert stats["total_expense"] == 0.0
        assert stats["balance"] == 0.0
        assert stats["transactions_count"] == 0
        assert stats["by_category"] == {}

    # ============ FULL SCENARIO ============

    def test_full_scenario(self, client: TestClient):
        """
        Полный сценарий:
        1. Создать 3 транзакции
        2. Получить список
        3. Получить статистику
        4. Экспортировать CSV
        """
        # 1
        transactions_data = [
            {
                "type": "income",
                "amount": 50000.0,
                "category": "Salary",
                "transaction_date": "2026-07-26",
                "comment": "July salary"
            },
            {
                "type": "expense",
                "amount": 15000.0,
                "category": "Rent",
                "transaction_date": "2026-07-26",
                "comment": "Monthly rent"
            },
            {
                "type": "expense",
                "amount": 3000.0,
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

        # 4
        response = client.get("/api/v1/export")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=transactions_" in response.headers["content-disposition"]
