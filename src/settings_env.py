from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")
    
    # Development
    DEV_MODE: bool = Field(default=True, description="Enable debug mode")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./parking.db", description="Database connection URL")
    ASYNC_DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./parking.db", description="Async database URL")
    
    # FastAPI
    FASTAPI_HOST: str = Field(default="localhost", description="FastAPI host")
    FASTAPI_PORT: int = Field(default=8080, description="FastAPI port")
    
    # Streamlit
    STREAMLIT_PORT: int = Field(default=8501, description="Streamlit port")
    
    # Parking Configuration
    HOURLY_RATE: float = Field(default=5.0, description="Hourly parking rate")
    PARKING_FLOORS: int = Field(default=3, description="Number of parking floors")
    SPOTS_PER_FLOOR: int = Field(default=20, description="Spots per floor")
    
    # LLM Configuration (for CrewAI)
    OPENAI_API_BASE: Optional[str] = Field(default="http://localhost:11434/v1", description="OpenAI API base URL")
    OPENAI_MODEL_NAME: str = Field(default="ollama/qwen2.5:0.5b", description="Model name")
    OPENAI_API_KEY: str = Field(default="sk-111111111111111111111111111111111111111111111111", description="API key")


# Create settings instance
settings = Settings()