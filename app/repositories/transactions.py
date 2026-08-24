from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, datetime
from typing import Optional, List, Dict
from app.models import Transaction, TransactionType
from app.schemas import TransactionCreate, TransactionUpdate, StatsResponse, CategoryStats
from app.logger import db_logger

class TransactionRepository:

    def __init__(self,db: Session):
        self.db = db

    def create(self, transaction_data: TransactionCreate) -> Transaction:
        try:
            data = transaction_data.model_dump()        #pydantic модель -> dict
            db_transaction = Transaction(**data)        #объект класса Transaction
            self.db.add(db_transaction)
            self.db.commit()
            self.db.refresh(db_transaction)

            db_logger.info(f"Created transaction: id = {db_transaction.id}, type = {db_transaction.type}, amount = {db_transaction.amount}")
            return db_transaction
        except Exception as e:
            self.db.rollback()
            db_logger.error(f"Error creating transaction: {str(e)}")
            raise

    def get_by_id(self, target_id: int) -> Optional[Transaction]:       #поиск по id
        try:
            target = self.db.query(Transaction).filter(
                getattr(Transaction, 'id') == target_id
            ).first()

            if target:
                db_logger.info(f"Found transaction by id={target_id}")
            else:
                db_logger.debug(f"Transaction with id={target_id} not found")
            return target
        except Exception as e:
            db_logger.error(f"Error getting transaction by id {target_id}: {str(e)}")
            raise

    def _build_filtered_list(
            self,
            category: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
        ):
        query = self.db.query(Transaction)

        if category:
            query = query.filter(Transaction.category == category)

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)

        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        return query

    def list(           #получить список с фильтрами
            self,
            skip: int = 0,
            limit: int = 100,
            category: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            sort_by: Optional[str] = "created_at",
            sort_desc: bool = True
             ) -> List[Transaction]:
        try:
            query = self._build_filtered_list(
                category = category,
                start_date = start_date,
                end_date = end_date
            )

            if sort_by:
                sort_column = getattr(Transaction, sort_by, Transaction.created_at)
                if sort_desc:
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
            else:
                query = query.order_by(desc(Transaction.created_at))

            transactions = query.offset(skip).limit(limit).all()    #пагинация
            db_logger.debug(f"Retrieved {len(transactions)} transactions (skip={skip}, limit={limit})")
            return transactions

        except Exception as e:
            db_logger.error(f"Error listing transactions: {str(e)}")
            raise

    def update(         #обновление транзакции по id
            self,
            target_id: int,
            update_data: TransactionUpdate
        ) -> Optional[Transaction]:
        try:
            transaction = self.get_by_id(target_id)
            if not transaction:
                db_logger.warning(f"Transaction with id={target_id} not found for update")
                return None

            update_dict = update_data.model_dump(exclude_unset=True)

            for key,value in update_dict.items():
                setattr(transaction,key,value)

            self.db.commit()
            self.db.refresh(transaction)

            db_logger.info(f"Updated transaction: id={target_id}")
            return transaction

        except Exception as e:
            self.db.rollback()
            db_logger.error(f"Error updating transaction {target_id}: {str(e)}")
            raise

    def delete(self,target_id: int) -> bool:
        try:
            transaction = self.get_by_id(target_id)
            if not transaction:
                db_logger.warning(f"Transaction with id={target_id} not found for delete")
                return False

            self.db.delete(transaction)
            self.db.commit()

            db_logger.info(f"Deleted transaction: id={target_id}")
            return True

        except Exception as e:
            self.db.rollback()
            db_logger.error(f"Error deleting transaction {target_id}: {str(e)}")
            raise

    def stats(
            self,
            category: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> StatsResponse:
        try:
            query = self._build_filtered_list(
                category=category,
                start_date=start_date,
                end_date=end_date
            )

            # Получаем все транзакции
            transactions = query.all()

            if not transactions:
                return StatsResponse(
                    total_income=0.0,
                    total_expense=0.0,
                    balance=0.0,
                    transactions_count=0,
                    by_category={}
                )


            total_income = query.filter(Transaction.type == TransactionType.INCOME) \
                               .with_entities(func.sum(Transaction.amount)) \
                               .scalar() or 0.0

            total_expense = query.filter(Transaction.type == TransactionType.EXPENSE) \
                                .with_entities(func.sum(Transaction.amount)) \
                                .scalar() or 0.0

            total_count = query.count()

            categories = query.with_entities(Transaction.category).distinct().all()
            categories = [c[0] for c in categories]
            category_stats = {}

            for c in categories:
                c_query = query.filter(Transaction.category == c)

                c_income = c_query.filter(Transaction.type == TransactionType.INCOME) \
                               .with_entities(func.sum(Transaction.amount)) \
                               .scalar() or 0.0

                c_expense = c_query.filter(Transaction.type == TransactionType.EXPENSE) \
                                .with_entities(func.sum(Transaction.amount)) \
                                .scalar() or 0.0

                category_stats[c] = CategoryStats(
                    income=c_income,
                    expense=c_expense
                )

            stats = StatsResponse(
                total_income=total_income,
                total_expense=total_expense,
                balance=total_income - total_expense,
                transactions_count=total_count,
                by_category=category_stats
            )

            db_logger.debug(
                f"Generated stats: total_income={total_income}, "
                f"total_expense={total_expense}, count={total_count}"
            )
            return stats

        except Exception as e:
            db_logger.error(f"Error getting stats: {str(e)}")
            raise
