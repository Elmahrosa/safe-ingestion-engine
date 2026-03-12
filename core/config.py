from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    data_dir: str = "data"
    pii_salt: str = "change-me"
    dashboard_admin_password: str = ""
    user_agent: str = "SafeIngestion/1.0"
    
    # API Server Settings
    cors_origins: str = ""
    sheet_webhook_url: str = ""
    sheet_api_secret: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
