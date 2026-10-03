from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    serpapi_api_key: str = ""
    gemini_api_key: str = ""
    # Tried in order; the next one is used when a model is overloaded or errors.
    gemini_models: str = "gemini-3.5-flash,gemini-flash-latest,gemini-3.5-flash-lite"

    # Max live SerpApi searches one scan may spend. Cache hits are free.
    scan_search_budget: int = 15
    max_followups: int = 3
    max_rivals: int = 2

    cache_dir: Path = BACKEND_DIR / ".cache" / "serp"
    demos_dir: Path = BACKEND_DIR / "demos"
    database_url: str = f"sqlite+aiosqlite:///{(BACKEND_DIR / 'rivalyze.db').as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    serpapi_mcp_url: str = "https://mcp.serpapi.com/mcp"

    @property
    def live(self) -> bool:
        """False means replay mode: only cached searches and recorded demos work."""
        return bool(self.serpapi_api_key)


settings = Settings()
