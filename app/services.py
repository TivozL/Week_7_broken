import csv
import io
from typing import Optional, List
from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.transactions import TransactionRepository
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

    def __init__(self, db: Session):
        self.repos = TransactionRepository(db)

    def create(self, data: TransactionCreate) -> TransactionRead:
        if data.transaction_date > date.today():
            service_logger.warning(f"Attempt to create transaction in future: {data.transaction_date}")
            raise HTTPException(
                status_code=400,
                detail="Cannot create transaction in the future"
            )

        try:
            transaction = self.repos.create(data)
            service_logger.info(f"Transaction created successfully: id={transaction.id}")

            return TransactionRead(
                id=transaction.id,
                type=transaction.type.value,
                amount=transaction.amount,
                category=transaction.category,
                transaction_date=transaction.transaction_date,
                comment=transaction.comment,
                created_at=transaction.created_at
            )
        except Exception as e:
            service_logger.error(f"Failed to create transaction: {e}")
            raise

    def get_by_id(self, target_id: int) -> TransactionRead:
        service_logger.debug(f"Getting transaction by id={target_id}")
        transaction = self.repos.get_by_id(target_id)

        if not transaction:
            service_logger.warning(f"Transaction not found: id={target_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Transaction with id {target_id} not found"
            )

        return TransactionRead(
            id=transaction.id,
            type=transaction.type.value,
            amount=transaction.amount,
            category=transaction.category,
            transaction_date=transaction.transaction_date,
            comment=transaction.comment,
            created_at=transaction.created_at
        )

    def get_all(
            self,
            category: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[TransactionRead]:
        service_logger.debug(f"Getting all transactions with filters: category={category}, "
                             f"start_date={start_date}, end_date={end_date}")

        transactions = self.repos.list(
            category=category,
            start_date=start_date,
            end_date=end_date
        )

        result = []
        for transaction in transactions:
            result.append(TransactionRead(
                id=transaction.id,
                type=transaction.type.value,
                amount=transaction.amount,
                category=transaction.category,
                transaction_date=transaction.transaction_date,
                comment=transaction.comment,
                created_at=transaction.created_at
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

        if data.transaction_date and data.transaction_date > date.today():
            service_logger.warning(f"Attempt to update transaction to future date: id={target_id}, "
                                   f"date={data.transaction_date}")
            raise HTTPException(
                status_code=400,
                detail="Cannot update transaction to future date"
            )

        updated = self.repos.update(target_id, data)
        service_logger.info(f"Transaction updated successfully: id={target_id}")

        return TransactionRead(
            id=updated.id,
            type=updated.type.value,
            amount=updated.amount,
            category=updated.category,
            transaction_date=updated.transaction_date,
            comment=updated.comment,
            created_at=updated.created_at
        )

    def delete(self, target_id: int) -> bool:
        service_logger.info(f"Deleting transaction: id={target_id}")

        existing = self.repos.get_by_id(target_id)
        if not existing:
            service_logger.warning(f"Transaction not found for deletion: id={target_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Transaction with id {target_id} not found"
            )

        result = self.repos.delete(target_id)
        service_logger.info(f"Transaction deleted successfully: id={target_id}")
        return result

    def get_stats(
            self,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> StatsResponse:
        service_logger.debug(f"Getting stats: start_date={start_date}, end_date={end_date}")

        stats = self.repos.stats(
            category=None,
            start_date=start_date,
            end_date=end_date
        )

        service_logger.debug(f"Stats response: total_income={stats.total_income}, "
                             f"total_expense={stats.total_expense}, "
                             f"transactions_count={stats.transactions_count}")

        return stats

    def import_csv(self, content: str) -> ImportResult:
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
                try:
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

    def export_csv(
            self,
            category: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> str:
        service_logger.info(f"Exporting CSV: category={category}, start_date={start_date}, end_date={end_date}")

        transactions = self.repos.list(
            category=category,
            start_date=start_date,
            end_date=end_date
        )

        output = io.StringIO()
        fieldnames = ["id", "type", "amount", "category", "transaction_date", "comment", "created_at"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for transaction in transactions:
            writer.writerow({
                "id": transaction.id,
                "type": transaction.type.value,
                "amount": transaction.amount,
                "category": transaction.category,
                "transaction_date": transaction.transaction_date.isoformat(),
                "comment": transaction.comment or "",
                "created_at": transaction.created_at.isoformat()
            })

        csv_content = output.getvalue()
        service_logger.info(f"CSV exported: {len(transactions)} transactions")
        return csv_content
