from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
MIN_PRODUCTION_SECRET_LENGTH = 32


class DatabaseSettings(BaseModel):
    url: str
    echo: bool = False
    pool_size: int = Field(default=20, ge=1)
    max_overflow: int = Field(default=10, ge=0)
    pool_recycle: int = Field(default=3600, ge=1)


class JwtSettings(BaseModel):
    secret_key: str = Field(min_length=16)
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=1440, ge=1)


class ReadonlySettings(BaseModel):
    enabled: int = 0


class LogSettings(BaseModel):
    request_body_limit: int = Field(default=4096, ge=0, le=65536)
    retention_days: int = Field(default=90, ge=1)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database: DatabaseSettings
    jwt: JwtSettings
    readonly: ReadonlySettings = ReadonlySettings()
    log: LogSettings = LogSettings()

    @model_validator(mode="after")
    def validate_production_secret(self) -> Self:
        secret = self.jwt.secret_key
        if self.environment == "production" and (
            secret == "your-secret-key-here"
            or len(secret) < MIN_PRODUCTION_SECRET_LENGTH
        ):
            raise ValueError("生产环境 JWT secret_key 必须至少 32 字符")
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(
                settings_cls,
                yaml_file=CONFIG_PATH,
                yaml_file_encoding="utf-8",
            ),
            file_secret_settings,
        )


settings = Settings()

SECRET_KEY = settings.jwt.secret_key
ALGORITHM = settings.jwt.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt.access_token_expire_minutes
READONLY_ENABLED = settings.readonly.enabled
