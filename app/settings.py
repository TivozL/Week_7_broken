from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_path:  str = "data/app.db"
    debug: bool = False
    log_level: str = "INFO"
    log_file_path: str = "logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()