from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import Optional, List
from datetime import date
from fastapi.responses import Response

from app.services import TransactionServices
from app.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionRead,
    StatsResponse,
    ImportResult, is_valid_date_range
)

from app.logger import router_logger

router = APIRouter(
    prefix="/api/v1",
    tags=["transactions"]
)

def get_service() -> TransactionServices:
    return TransactionServices()

async def validate_dates(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
) -> tuple[Optional[date], Optional[date]]:
    #Dependency для валидации дат в query параметрах

    try:
        is_valid_date_range(start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return start_date, end_date


#=======end-points========

@router.post(       #создание новой транзакции
    "/transactions",
    response_model=TransactionRead,
    status_code=201,
    summary="Create new transactions",
    description="Creates a new income or expense transaction"
)
def create_transaction(
        data:TransactionCreate,
        service: TransactionServices = Depends(get_service)
):
    router_logger.info(f"POST /transactions - Creating transaction: type={data.type}, amount={data.amount}")
    return service.create(data)


@router.get(        #получить транзакции с фильтрацией
    "/transactions",
    response_model=List[TransactionRead],
    summary="Get all transactions",
    description="Returns all transactions with optional filters"
)
def get_transactions(
    category: Optional[str] = None,
    dates: tuple[Optional[date], Optional[date]] = Depends(validate_dates),
    service: TransactionServices = Depends(get_service)
):
    start_date, end_date = dates
    router_logger.debug(f"GET /transactions - Filters: category={category}, start={start_date}, end={end_date}")
    return service.get_all(
        category = category,
        start_date = start_date,
        end_date = end_date
    )


@router.get(        #получить транзакцию по id
    "/transactions/{transaction_id}",
    response_model=TransactionRead,
    summary="Get transactions by ID",
    description="Returns transaction by ID"
)
def get_transaction_by_id(
        transaction_id: int,
        service: TransactionServices = Depends(get_service)
):
    router_logger.debug(f"GET /transactions/{transaction_id}")
    return service.get_by_id(transaction_id)


@router.patch(      #обновить транзакцию
    "/transactions/{transaction_id}",
    response_model=TransactionRead,
    summary="Update transaction",
    description="Partially update transaction by ID"
)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    service: TransactionServices = Depends(get_service)
):
    router_logger.info(f"PATCH /transactions/{transaction_id} - Updating transaction")
    return service.update(transaction_id, data)


@router.delete(         #удаление транзакции
"/transactions/{transaction_id}",
    status_code=204,
    summary="Delete transaction",
    description="Deletes a transaction by ID"
)
def delete_transaction(
    transaction_id: int,
    service: TransactionServices = Depends(get_service)
):
    router_logger.info(f"DELETE /transactions/{transaction_id} - Deleting transaction")
    service.delete(transaction_id)
    return None


@router.get(        #получить статистику
"/stats",
    response_model=StatsResponse,
    summary="Get statistics",
    description="Returns statistics for all transactions"
)
def get_stats(
    dates: tuple[Optional[date], Optional[date]] = Depends(validate_dates),
    service: TransactionServices = Depends(get_service)
):
    start_date, end_date = dates
    router_logger.debug(f"GET /stats - Filters: start={start_date}, end={end_date}")
    return service.get_stats(
        start_date=start_date,
        end_date=end_date
    )


@router.post(
"/import",
    response_model=ImportResult,
    summary="Import transactions from CSV",
    description="Upload a CSV file to import transactions"
)
def import_csv(
        file: UploadFile = File(..., description="CSV file with transactions"),
        service: TransactionServices = Depends(get_service)
):
    router_logger.info(f"POST /import - Importing CSV file: {file.filename}")
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be CSV format"
        )

    content = file.file.read().decode('utf-8')
    return service.import_csv(content)


@router.get("/export", summary="Export transactions to CSV")
def export_csv(
    category: Optional[str] = None,
    dates: tuple[Optional[date], Optional[date]] = Depends(validate_dates),
    service: TransactionServices = Depends(get_service)
):
    start_date, end_date = dates
    router_logger.info(f"GET /export - Exporting CSV: category={category}, start={start_date}, end={end_date}")
    csv_data = service.export_csv(
        category=category,
        start_date=start_date,
        end_date=end_date
    )
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{date.today()}.csv"
        }
    )