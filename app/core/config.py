from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str

    DATABASE_URL: str

    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cloudflare R2 Settings
    R2_BUCKET_NAME: str
    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY: str
    R2_SECRET_KEY: str
    R2_PUBLIC_URL: str = ""

    # Huggingface  Settings
    HF: str

    class Config:
        env_file = ".env"
        extra = "ignore"
        # env_file_encoding = "utf-8"


settings = Settings()
