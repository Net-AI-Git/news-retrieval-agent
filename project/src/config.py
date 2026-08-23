import typing

from dotenv import load_dotenv
from logging import config
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()

log_config = {"version": 1, "disable_existing_loggers": False, "handlers": {"console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "verbose"}}, "formatters": {"verbose": {"format": "%(asctime)s %(levelname)s module=%(module)s, process_id=%(process)d, %(message)s"}}, "loggers": {"app": {"handlers": ["console"], "level": "DEBUG", "propagate": False}}}
config.dictConfig(log_config)


class Settings(BaseSettings):
    docs_user: str
    docs_pass: str
    description: str = ""
    version: str = "0.1.0"
    project_name: str = "Template AI APP"

    model_config = SettingsConfigDict(extra="allow")


class APISettings(BaseSettings):
    port: int = 8000
    prefix: str = "/api"
    disable_docs: bool = False
    openapi_prefix: str = ""
    openapi_url: typing.Optional[str] = "/openapi.json"
    docs_url: typing.Optional[str] = None
    redoc_url: typing.Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")


settings = Settings()
api_settings = APISettings()