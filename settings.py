from functools import lru_cache

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
    allowed_hosts: list = ["*"]
    debug: bool = False

    class ConfigDict:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
