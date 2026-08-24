from sqlalchemy import Column, Integer, Float, String, Enum, Date, DateTime, Index, func
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    category = Column(String, nullable=False)
    comment = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_transaction_date', 'transaction_date'),
        Index('idx_category', 'category'),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount}, category='{self.category}')>"
