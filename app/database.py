from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.settings import settings
from app.logger import db_logger


def get_engine():
    return create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )


def get_session_local():
    engine = get_engine()
    return sessionmaker(autoflush=False, autocommit=False, bind=engine)


def get_db() -> Session:
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
