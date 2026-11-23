from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./blackbox.db"
    SECRET_KEY: str = "dev-secret-key"
    UPLOAD_DIR: str = "uploads"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    GITHUB_TOKEN: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
