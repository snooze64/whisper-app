"""
Application configuration using Pydantic Settings
"""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Project info
    PROJECT_NAME: str = "Whisper Transcription API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str] | None) -> List[str]:
        if v is None or v == "":
            return ["http://localhost:3000", "http://localhost:5173"]
        if isinstance(v, str):
            if v.startswith("["):
                # JSON array string
                import json
                return json.loads(v)
            # Comma-separated string
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:password@postgres:5432/whisper",
        description="PostgreSQL database URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis URL for Celery"
    )

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://redis:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/0",
        description="Celery result backend URL"
    )

    # LDAP Authentication
    LDAP_SERVER: str = Field(
        default="ldap://ldap-server:389",
        description="LDAP server URL"
    )
    LDAP_BASE_DN: str = Field(
        default="dc=example,dc=com",
        description="LDAP base DN"
    )
    LDAP_USER_DN_TEMPLATE: str = Field(
        default="uid={username},ou=users,dc=example,dc=com",
        description="LDAP user DN template"
    )
    USE_MOCK_AUTH: bool = Field(
        default=False,
        description="Use mock authentication for development (bypasses LDAP)"
    )

    # JWT
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File Storage
    UPLOAD_DIR: str = "/data/uploads"
    RESULT_DIR: str = "/data/results"
    TEMP_DIR: str = "/data/temp"
    MAX_FILE_SIZE: int = 1073741824  # 1GB in bytes
    FILE_RETENTION_HOURS: int = 24
    ALLOWED_AUDIO_FORMATS: List[str] = ["mp3", "wav"]
    ALLOWED_VIDEO_FORMATS: List[str] = ["mp4"]

    # Whisper Settings
    DEFAULT_WHISPER_MODEL: str = "large-v3-turbo"
    AVAILABLE_WHISPER_MODELS: List[str] = ["large-v3", "large-v3-turbo"]
    DEFAULT_LANGUAGE: str = "ja"

    # GPU Settings
    CUDA_VISIBLE_DEVICES: str = "0"
    GPU_MEMORY_THRESHOLD_MB: int = 10000  # Minimum free memory to start task

    # Future: OpenAI API for LLM integration
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Create global settings instance
settings = Settings()
