import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.settings import settings
from app.routers import router
from app.logger import setup_logging,app_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app_logger.info('Start Finance Tracker')
    app_logger.info(f'Starting {settings.app_name}')
    app_logger.info(f"Debug mode: {settings.debug}")
    app_logger.info(f"Database: {settings.DATABASE_URL}")
    app_logger.info("Schema managed by Alembic")

    yield

    app_logger.info("Shutting down Finance Tracker")

def create_app(env: str = "dev") -> FastAPI:    #фабрика приложения
    from app.settings import get_settings
    env_settings = get_settings(env)        #подрубаем нужные настройки среды

    app = FastAPI(
            title=env_settings.app_name,
            description="API for financial accounting",
            debug=env_settings.debug,
            lifespan=lifespan,
            docs_url="/docs" if env_settings.debug else None,
            redoc_url="/redoc" if env_settings.debug else None,
        )

    app.include_router(router)

    @app.get('/')
    async def root():
        app_logger.debug("Root endpoint accessed")
        return {
            "service": env_settings.app_name,
            "environment": env,
            "status": "running",
            "docs": "/docs" if env_settings.debug else None,
            "endpoints": {
                "transactions": "/transactions",
                "stats": "/transactions/stats",
            }
        }

    @app.get("/health")
    async def check():
        app_logger.debug("Health check requested")
        return {"status": "ok",
                "environment": env}

    @app.get("/info")
    async def info():
        return {
            "app": env_settings.app_name,
            "environment": env,
            "debug": env_settings.debug,
            "log_level": env_settings.log_level,
            "database_url": env_settings.DATABASE_URL,
            "schema_management": "alembic"
        }

    return app

app = create_app()

if __name__ == "__main__":
    import sys

    env = "dev"
    if len(sys.argv) > 1 and sys.argv[1] in ["dev", "test", "prod"]:
        env = sys.argv[1]

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
