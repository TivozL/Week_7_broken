import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.database import get_db
from app.models import Base


@pytest.fixture(scope="function")
def client():
    os.environ["APP_ENV"] = "test"

    import importlib
    import app.settings
    importlib.reload(app.settings)

    from app.settings import settings
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()

    app = create_app(env="test")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    session.close()
    app.dependency_overrides.clear()
    os.environ["APP_ENV"] = "dev"
