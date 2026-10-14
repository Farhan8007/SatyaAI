"""
Central configuration for SATYA AI backend.
All values can be overridden via a .env file (see .env.example).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "SATYA AI"
    environment: str = "development"

    # Mongo
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "satya_ai"

    # Auth
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION_super_secret_key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours

    # Encryption (AES-256 key for paper encryption, 32 bytes, base64 in real env)
    aes_secret_key: str = "0123456789abcdef0123456789abcdef"  # 32 chars = 256 bit

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Email (SMTP) -- used to send real invite emails to new users.
    # Leave blank to disable email sending (invites just won't be emailed).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
