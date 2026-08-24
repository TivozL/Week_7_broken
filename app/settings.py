from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    database_path: str = "data/app.db"
    app_name: str = "Transaction API"
    debug: bool = False
    api_key: Optional[str] = None
    log_level: str = "INFO"
    log_file_path: str = "logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.database_path}"


def get_settings(env: str = "dev") -> Settings:
    if env == "test":
        return Settings(
            database_path=":memory:",
            debug=False,
            log_level="WARNING",
            app_name="Transaction API (Test)"
        )
    elif env == "prod":
        return Settings(
            debug=False,
            log_level="WARNING",
            app_name="Transaction API (Production)"
        )
    else:  # dev
        return Settings(
            debug=True,
            log_level="DEBUG",
            app_name="Transaction API (Development)"
        )


_env = os.getenv("APP_ENV", "dev")      #НАСТРОЙКИ НА ОСНОВЕ ОКРУЖЕНИЯ
settings = get_settings(_env)
