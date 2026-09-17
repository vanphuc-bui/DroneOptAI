from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DroneOptAI API"
    database_url: str = "sqlite:///./droneoptai.db"
    jwt_secret: str = "change-me-in-production"
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
