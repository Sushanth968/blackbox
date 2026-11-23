from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./blackbox.db"
    SECRET_KEY: str = "dev-secret-key"
    UPLOAD_DIR: str = "uploads"
    # Evidence upload limits. MAX_UPLOAD_BYTES guards against unbounded writes
    # (DoS); ALLOWED_UPLOAD_EXTENSIONS restricts uploads to parseable text
    # formats. "" permits extensionless files (treated as plain logs).
    MAX_UPLOAD_BYTES: int = 52_428_800  # 50 MiB
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = [
        "json", "jsonl", "ndjson", "csv", "log", "txt",
        "git", "cicd", "yml", "yaml", "syslog", "",
    ]
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    GITHUB_TOKEN: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
