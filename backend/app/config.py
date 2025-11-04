from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    claude_data_path: str = "~/.claude"
    database_path: str = "./data/analytics.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False

    def validate_openai_config(self) -> None:
        """Validate that OpenAI API key is configured"""
        if not self.openai_api_key or self.openai_api_key == "":
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Please set it in your .env file or environment variables."
            )


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    # Expand the user path
    settings.claude_data_path = os.path.expanduser(settings.claude_data_path)
    return settings
