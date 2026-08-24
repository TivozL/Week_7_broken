import sqlite3
from typing import List, Optional, Dict
from datetime import date
from app.database import get_connection
from app.logger import repos_logger


class TransactionRepository:

    def create(self, data: Dict) -> int:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions (type, amount, category, transaction_date, comment)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    data["type"],
                    data["amount"],
                    data["category"],
                    data["transaction_date"].isoformat(),
                    data.get("comment")
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            repos_logger.error(f"Failed to create transaction: {e}, data={data}")
            raise

    def get_by_id(self, target_id: int) -> Optional[Dict]:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM transactions WHERE id = ?", (target_id,))
                row = cursor.fetchone()
                if row:
                    repos_logger.debug(f"Transaction found: id={target_id}")
                    return dict(row)
                repos_logger.debug(f"Transaction not found: id={target_id}")
                return None
        except Exception as e:
            repos_logger.error(f"Failed to get transaction by id={target_id}: {e}")
            raise

    def get_all(self,
                category: Optional[str] = None,
                start_date: Optional[date] = None,
                end_date: Optional[date] = None) -> List[Dict]:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM transactions WHERE 1=1"
                params = []

                if category:
                    query += " AND category = ?"
                    params.append(category)

                if start_date:
                    query += " AND transaction_date >= ?"
                    params.append(start_date.isoformat())

                if end_date:
                    query += " AND transaction_date <= ?"
                    params.append(end_date.isoformat())

                query += " ORDER BY transaction_date DESC, id DESC"
                cursor.execute(query, params)
                result = [dict(row) for row in cursor.fetchall()]
                repos_logger.debug(f"Retrieved {len(result)} transactions with filters: category={category}, "
                                  f"start_date={start_date}, end_date={end_date}")
                return result
        except Exception as e:
            repos_logger.error(f"Failed to get transactions: {e}")
            raise

    def update(self, target_id: int, data: Dict) -> bool:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                fields = []
                values = []

                for key, value in data.items():
                    if value is None:
                        continue
                    fields.append(f"{key} = ?")
                    values.append(value)

                if not fields:
                    repos_logger.warning(f"Update called with empty data for id={target_id}")
                    return False

                values.append(target_id)
                query = f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    repos_logger.info(f"Transaction updated: id={target_id}, fields={list(data.keys())}")
                else:
                    repos_logger.warning(f"Transaction not found for update: id={target_id}")
                return success
        except Exception as e:
            repos_logger.error(f"Failed to update transaction id={target_id}: {e}")
            raise

    def delete(self, target_id: int) -> bool:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE id = ?", (target_id,))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    repos_logger.info(f"Transaction deleted: id={target_id}")
                else:
                    repos_logger.warning(f"Transaction not found for deletion: id={target_id}")
                return success
        except Exception as e:
            repos_logger.error(f"Failed to delete transaction id={target_id}: {e}")
            raise

    def get_stats(self, start_date: Optional[date] = None,
                  end_date: Optional[date] = None) -> Dict:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT 
                        COUNT(*) as total_count,
                        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
                        SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense,
                        category,
                        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as cat_income,
                        SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as cat_expense
                    FROM transactions
                    WHERE 1=1
                """
                params = []

                if start_date:
                    query += " AND transaction_date >= ?"
                    params.append(start_date.isoformat())
                if end_date:
                    query += " AND transaction_date <= ?"
                    params.append(end_date.isoformat())

                query += " GROUP BY category"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                if not rows:
                    repos_logger.debug("No transactions found for stats")
                    return {
                        "total_income": 0.0,
                        "total_expense": 0.0,
                        "total_count": 0,
                        "by_category": {}
                    }

                total_income = sum(row["total_income"] or 0 for row in rows)
                total_expense = sum(row["total_expense"] or 0 for row in rows)
                total_count = sum(row["total_count"] or 0 for row in rows)

                by_category = {}
                for row in rows:
                    category = row["category"]
                    by_category[category] = {
                        "income": row["cat_income"] or 0.0,
                        "expense": row["cat_expense"] or 0.0
                    }

                repos_logger.debug(f"Stats calculated: total_income={total_income}, total_expense={total_expense}, "
                                  f"total_count={total_count}, categories={len(by_category)}")

                return {
                    "total_income": total_income,
                    "total_expense": total_expense,
                    "total_count": total_count,
                    "by_category": by_category
                }
        except Exception as e:
            repos_logger.error(f"Failed to get stats: {e}")
            raise