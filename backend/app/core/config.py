import os
import re
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MezFlow"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "temporary-dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # PostgreSQL Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "mezflow_db"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/mezflow_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    @field_validator("DEBUG", mode="after")
    @classmethod
    def validate_debug(cls, v: bool, info) -> bool:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production":
            return False
        return v

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and ("dev" in v.lower() or "temporary" in v.lower() or len(v) < 32):
            raise ValueError(
                "In production, SECRET_KEY must be a secure random key of at least 32 characters."
            )
        return v

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def use_asyncpg_driver(cls, v: str) -> str:
        # Neon / Vercel Marketplace hand out postgres://...?sslmode=require&channel_binding=require; asyncpg needs its own scheme and ?ssl=
        v = re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", v)
        v = re.sub(r"[?&]channel_binding=[^&]*", "", v).replace("sslmode=", "ssl=")
        return v if "?" in v or "&" not in v else v.replace("&", "?", 1)

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
