import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "CodeEcho"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    # Database
    DATABASE_URL: str = "sqlite:///./codeecho.db"
    
    # Frontend Serving (Production Container)
    SERVE_FRONTEND: bool = False
    FRONTEND_DIST_DIR: str = str(Path("./frontend/dist").resolve())
    
    # Mining Limits & Constraints
    MAX_COMMITS_DEFAULT: int = 100
    MAX_COMMITS_HARD_LIMIT: int = 500
    MAX_FILE_SIZE_BYTES: int = 200 * 1024  # 200 KB per file
    CLONE_TIMEOUT_SECONDS: int = 60
    TEMP_DIR_ROOT: str = str(Path("./temp_clones").resolve())
    
    # Supported File Extensions (Starting with Python for MVP)
    SUPPORTED_EXTENSIONS: list[str] = [".py"]
    
    # AI Explanation Settings
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    EXPLANATION_PROVIDER: str = "fallback"  # 'gemini', 'openai', or 'fallback'
    
    # Embedding Configuration
    DEFAULT_EMBEDDER: str = "tfidf"  # 'tfidf' or 'codebert'

settings = Settings()
