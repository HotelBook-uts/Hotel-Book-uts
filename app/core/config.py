import os
from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "HotelBook")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    # HU-002: intentos fallidos seguidos permitidos antes de bloquear la cuenta
    MAX_INTENTOS_FALLIDOS: int = int(os.getenv("MAX_INTENTOS_FALLIDOS", "3"))


settings = Settings()