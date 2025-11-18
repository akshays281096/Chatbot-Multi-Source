"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings"""
    
    # LLM API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    
    # Default LLM Provider
    DEFAULT_LLM_PROVIDER: Literal["OPENAI", "ANTHROPIC", "GEMINI"] = "OPENAI"
    DEFAULT_MODEL: str = "gpt-5"
    
    # Vector Database
    VECTOR_DB_PATH: str = "./data/vector_db"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Server Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/chatbot.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/chatbot.log"
    
    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

