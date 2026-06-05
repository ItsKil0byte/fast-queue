from dataclasses import dataclass
import os


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    api_url: str = os.getenv(
        "API_SERVICE_URL",
        "http://localhost:8000"
    )


config = Config()