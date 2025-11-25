from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class YoutubeSettings(BaseSettings):
    client_id: str
    redirect_uri: str
    client_secret: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "youtube_settings.env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_youtube_settings():
    return YoutubeSettings()
