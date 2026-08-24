from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from typing import Optional,List,Dict,Literal


def is_valid_date_range(start_date: Optional[date] = None,
                        end_date: Optional[date] = None) -> bool:

    if start_date and start_date > date.today():
        raise ValueError(f"Start date cannot be in the future: {start_date}")

    if end_date and end_date > date.today():
        raise ValueError(f"End date cannot be in the future: {end_date}")

    if start_date and end_date and start_date > end_date:
        raise ValueError(f"Start date ({start_date}) must be before or equal to end date ({end_date})")

    return True


class TransactionBase(BaseModel):       #базовая модель
    type: Literal["income","expense"] = Field(..., description="Transaction type: income or expense")
    amount: float = Field(..., gt=0, description="Amount (greater than 0)")
    category: str = Field(..., min_length=1,max_length=50, description="Category")
    transaction_date: date = Field(..., description="Transaction date")
    comment: Optional[str] = Field(None, max_length=200, description="Transaction comment")

    @field_validator('transaction_date')
    @classmethod
    def validate_date(cls, v: date) -> date:
        is_valid_date_range(start_date=v, end_date=v)
        return v

class TransactionCreate(TransactionBase):   #для создания
    pass

class TransactionUpdate(BaseModel):     #для обновления (PATCH)
    type: Optional[Literal["income", "expense"]] = Field(None, description="Transaction type: income or expense")
    amount: Optional[float] = Field(None, gt=0, description="Amount (greater than 0)")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="Category")
    transaction_date: Optional[date] = Field(None, description="Transaction date")
    comment: Optional[str] = Field(None, max_length=200, description="Transaction comment")

    @field_validator('transaction_date')
    @classmethod
    def validate_date(cls, v: Optional[date]) -> Optional[date]:
        if v:
            is_valid_date_range(start_date=v, end_date=v)
        return v

class TransactionRead(TransactionBase):     #для чтения
    id: int = Field(..., description="Transaction ID")
    created_at: datetime = Field(..., description="Transaction creating time")


class CategoryStats(BaseModel):         #статистика по категории
    income: float = Field(0.0, description="Income in category")
    expense: float = Field(0.0, description="Expense in category")

class StatsResponse(BaseModel):          #базовый ответ
    total_income: float = Field(..., description="Full income")
    total_expense: float = Field(..., description="Full expense")
    balance: float = Field(..., description="Current balance")
    transactions_count: int = Field(..., description="Number of transactions")
    by_category: Dict[str, CategoryStats] = Field(default_factory=dict, description="Statistics by category")


class ImportError(BaseModel):       #ошибка импорта строки
    row: int = Field(..., description="Line with error (start from 1)")
    error: str = Field(..., description="Error description")
    data: Optional[dict] = Field(None, description="Line data")

class ImportResult(BaseModel):      #импорт csv
    success: int= Field(0, description="Number of added transactions")
    errors: List[ImportError] = Field(default_factory=list, description="Errors list")

    @property
    def total(self) -> int:     #всго операций
        return self.success + len(self.errors)

class TransactionFilter(BaseModel):
    category: Optional[str] = Field(None, description="Filter by category")
    start_date: Optional[date] = Field(None, description="Strat time")
    end_date: Optional[date] = Field(None, description="End time")

