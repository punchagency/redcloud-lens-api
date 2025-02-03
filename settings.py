from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USERNAME: str = None
    DB_PASSWORD: str = None
    DB_HOST: str = None
    DB_NAME: str = None
    OPENAI_API_KEY: str = None
    GCP_PROJECT_ID: str = None
    INFERENCE_API_TOKEN: str = None
    GCP_AUTH_TOKEN: str = None
    VISION_PREDICTION_KEY: str = None
    VISION_PREDICTION_ENDPOINT: str = None
    VISION_PROJECT_ID: str = None
    VISION_ITERATION_NAME: str = None
    GRAPH_API_ACCESS_TOKEN: str = None
    WEBHOOK_VERIFY_TOKEN: str = None
    allowed_hosts: list = ["*"]
    debug: bool = False
    APP_ENV: str = "prod"
    LOG_ENABLED_VALUE: Optional[str] = None

    @property
    def log_enabled(self):
        TRUTHY_VALUES = ["1", "true", "True", "TRUE", "t", "T", "y", "Y", "yes", "Yes", "YES"]
        if self.LOG_ENABLED_VALUE is None:
            return False
        return self.LOG_ENABLED_VALUE in TRUTHY_VALUES

    class ConfigDict:
        env_file = ".env"


@lru_cache(maxsize=None)
def get_settings():
    return Settings()
