import csv
import io
from typing import Optional
from datetime import date
from fastapi import HTTPException
from app.repositories import TransactionRepository
from app.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionRead,
    StatsResponse,
    CategoryStats,
    ImportResult,
    ImportError
)

from app.logger import service_logger

class TransactionServices:

    def __init__(self):
        self.repos = TransactionRepository()

    def create(self, data: TransactionCreate) -> TransactionRead:
        if data.transaction_date > date.today():
            service_logger.warning(f"Attempt to create transaction in future: {data.transaction_date}")
            raise HTTPException(
                status_code=400,
                detail="Cannot create transaction in the future"
            )

        try:
            data_dict = data.model_dump()
            transaction_id = self.repos.create(data_dict)
            created = self.repos.get_by_id(transaction_id)
            service_logger.info(f"Transaction created successfully: id={transaction_id}")
            return TransactionRead(
                id=created["id"],
                type=created["type"],
                amount=created["amount"],
                category=created["category"],
                transaction_date=created["transaction_date"],  # ← ключ из БД
                comment=created.get("comment"),
                created_at=created["created_at"]
            )
        except Exception as e:
            service_logger.error(f"Failed to create transaction: {e}")
            raise

    def get_by_id(self, target_id):     #получить транзакцию по ID
        service_logger.debug(f"Getting transaction by id={target_id}")
        transaction = self.repos.get_by_id(target_id)

        if not transaction:
            service_logger.warning(f"Transaction not found: id={target_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Transaction with id {target_id} not found"
            )

        return TransactionRead(
            id=transaction["id"],
            type=transaction["type"],
            amount=transaction["amount"],
            category=transaction["category"],
            transaction_date=transaction["transaction_date"],
            comment=transaction.get("comment"),
            created_at=transaction["created_at"]
        )

    def get_all(self,                           #все транзакции с фильтрацией
                category: Optional[str] = None,
                start_date: Optional[date] = None,
                end_date: Optional[date] = None
                ):
        service_logger.debug(f"Getting all transactions with filters: category={category}, "
                             f"start_date={start_date}, end_date={end_date}")

        transactions = self.repos.get_all(
            category=category,
            start_date=start_date,
            end_date=end_date
        )

        result = []
        for transaction in transactions:
            result.append(TransactionRead(
                id=transaction["id"],
                type=transaction["type"],
                amount=transaction["amount"],
                category=transaction["category"],
                transaction_date=transaction["transaction_date"],  # ← ключ из БД
                comment=transaction.get("comment"),
                created_at=transaction["created_at"]
            ))
        service_logger.debug(f"Returning {len(result)} transactions")
        return result

    def update(self, target_id: int, data: TransactionUpdate) -> TransactionRead:
        service_logger.info(f"Updating transaction: id={target_id}")

        existing = self.repos.get_by_id(target_id)
        if not existing:
            service_logger.warning(f"Transaction not found for update: id={target_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Transaction with id {target_id} not found"
            )
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            service_logger.debug(f"No fields to update for transaction: id={target_id}")
            return TransactionRead(
                id=existing["id"],
                type=existing["type"],
                amount=existing["amount"],
                category=existing["category"],
                transaction_date=existing["transaction_date"],
                comment=existing.get("comment"),
                created_at=existing["created_at"]
            )

        if "transaction_date" in update_data and update_data["transaction_date"] > date.today():
            service_logger.warning(f"Attempt to update transaction to future date: id={target_id}, "
                                   f"date={update_data['transaction_date']}")
            raise HTTPException(
                status_code=400,
                detail="Cannot update transaction to future date"
            )

        self.repos.update(target_id, update_data)
        result = self.repos.get_by_id(target_id)
        service_logger.info(f"Transaction updated successfully: id={target_id}")
        return TransactionRead(
            id=result["id"],
            type=result["type"],
            amount=result["amount"],
            category=result["category"],
            transaction_date=result["transaction_date"],
            comment=result.get("comment"),
            created_at=result["created_at"]
        )

    def delete(self, target_id):        #удаление транзакций
        service_logger.info(f"Deleting transaction: id={target_id}")

        existing = self.repos.get_by_id(target_id)
        if not existing:
            service_logger.warning(f"Transaction not found for deletion: id={target_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Transaction with id {target_id} not found"
            )

        service_logger.info(f"Transaction deleted successfully: id={target_id}")
        return self.repos.delete(target_id)

    def get_stats(self, start_date: Optional[date] = None,
                  end_date: Optional[date] = None) -> StatsResponse:

        service_logger.debug(f"Getting stats: start_date={start_date}, end_date={end_date}")

        stats_data = self.repos.get_stats(
            start_date=start_date,
            end_date=end_date
        )

        by_category = {}
        for c, d in stats_data["by_category"].items():
            by_category[c] = CategoryStats(
                income=d["income"],
                expense=d["expense"]
            )

        response = StatsResponse(
            total_income=stats_data["total_income"],
            total_expense=stats_data["total_expense"],
            balance=stats_data["total_income"] - stats_data["total_expense"],
            transactions_count=stats_data["total_count"],
            by_category=by_category
        )

        service_logger.debug(f"Stats response: total_income={response.total_income}, "
                             f"total_expense={response.total_expense}, "
                             f"transactions_count={response.transactions_count}")

        return response

    def import_csv(self, content: str) -> ImportResult:     #импорт из csv
        service_logger.info("Starting CSV import")
        result = ImportResult(success=0, errors=[])

        try:
            reader = csv.DictReader(io.StringIO(content))
            required_fields = {"type", "amount", "category", "transaction_date"}

            if not required_fields.issubset(set(reader.fieldnames or [])):
                error_msg = f"CSV must have columns: {', '.join(required_fields)}"
                service_logger.error(error_msg)
                result.errors.append(ImportError(
                    row=0,
                    error=error_msg,
                    data={"headers": reader.fieldnames}
                ))
                return result

            for row_num, row in enumerate(reader, start=1):
                try:        #валидация
                    if row.get("type") not in ["income", "expense"]:
                        raise ValueError("type must be 'income' or 'expense'")

                    try:
                        amount = float(row.get("amount", 0))
                        if amount <= 0:
                            raise ValueError("amount must be greater than 0")
                    except ValueError:
                        raise ValueError("amount must be a positive number")

                    if not row.get("category", "").strip():
                        raise ValueError("category cannot be empty")

                    try:
                        transaction_date = date.fromisoformat(row.get("transaction_date", ""))
                    except ValueError:
                        raise ValueError("date must be in YYYY-MM-DD format")

                    create_data = TransactionCreate(
                        type=row["type"],
                        amount=amount,
                        category=row["category"].strip(),
                        transaction_date=transaction_date,
                        comment=row.get("comment", "").strip() or None
                    )

                    self.create(create_data)
                    result.success += 1

                except Exception as e:
                    service_logger.warning(f"Import error at row {row_num}: {e}, data={row}")
                    result.errors.append(ImportError(
                        row=row_num,
                        error=str(e),
                        data=row
                    ))
            service_logger.info(f"CSV import completed: {result.success} successful, {len(result.errors)} errors")

        except Exception as e:
            service_logger.error(f"CSV parsing error: {e}")
            result.errors.append(ImportError(
                row=0,
                error=f"CSV parsing error: {str(e)}",
                data={}
            ))

        return result

    def export_csv(self, category: Optional[str] = None,
               start_date: Optional[date] = None,
               end_date: Optional[date] = None) -> str:
        service_logger.info(f"Exporting CSV: category={category}, start_date={start_date}, end_date={end_date}")

        transactions = self.repos.get_all(
            category=category,
            start_date=start_date,
            end_date=end_date
        )

        output = io.StringIO()
        fieldnames = ["id", "type", "amount", "category", "transaction_date", "comment", "created_at"]
        writer = csv.DictWriter(output,fieldnames=fieldnames)
        writer.writeheader()

        for transaction in transactions:
            writer.writerow({
                "id": transaction["id"],
                "type": transaction["type"],
                "amount": transaction["amount"],
                "category": transaction["category"],
                "transaction_date": transaction["transaction_date"],  # ключ изменился!
                "comment": transaction.get("comment", ""),
                "created_at": transaction["created_at"]
            })

        csv_content = output.getvalue()
        service_logger.info(f"CSV exported: {len(transactions)} transactions")
        return csv_content