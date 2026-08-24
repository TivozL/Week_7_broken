import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import router
from app.logger import setup_logging,app_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app_logger.info('Start Finance Tracker')

    try:
        init_db()
        app_logger.info("Database initialized")
    except Exception as e:
        app_logger.error(f"Failed to initialize database {e}")
        raise

    yield

    app_logger.info("Shutting down Finance Tracker")

app = FastAPI(
    title="Finance Tracker",
    description="API for financial accounting",
    lifespan=lifespan
)

app.include_router(router)

@app.get("/health")
async def check():
    app_logger.debug("Health check requested")
    return {"status": "ok"}

@app.get("/")
async def root():       #корневой end-point
    app_logger.debug("Root endpoint accessed")
    return {
        "service": "Finance Tracker API",
        "docs": "/docs",
        "endpoints": {
            "transactions": "/api/v1/transactions",
            "stats": "/api/v1/stats",
            "import": "/api/v1/import",
            "export": "/api/v1/export"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )