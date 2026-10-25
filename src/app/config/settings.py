from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.constants import env_defaults
from app.constants.database import POSTGRES_SCHEMES, PSYCOPG_SCHEME
from app.constants.http import ORIGIN_SCHEMES
from app.constants.limits import MAX_PORT, MIN_SECRET_LENGTH, PG_INT_MAX
from app.enums.clasificador_modo import ClasificadorModo
from app.enums.log_level import LogLevel
from app.enums.node_env import NodeEnv

type PositiveInt = Annotated[int, Field(ge=1)]
type PgInt = Annotated[int, Field(ge=1, le=PG_INT_MAX)]
type Secret = Annotated[SecretStr, Field(min_length=MIN_SECRET_LENGTH)]


def _split_list(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _is_origin(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in ORIGIN_SCHEMES and bool(parts.netloc) and value == f"{parts.scheme}://{parts.netloc}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    node_env: NodeEnv = NodeEnv.PRODUCTION
    port: int = Field(default=env_defaults.DEFAULT_PORT, ge=1, le=MAX_PORT)
    log_level: LogLevel = LogLevel.INFO
    database_url: SecretStr
    cookie_secret: Secret
    cookie_secret_previous: Annotated[list[Secret], NoDecode] = []
    cors_origins: Annotated[list[str], NoDecode] = []
    trust_proxy: bool = False
    clasificador_modo: ClasificadorModo = ClasificadorModo.EXTERNO
    db_pool_max: PgInt = env_defaults.DEFAULT_DB_POOL_MAX
    db_idle_timeout_ms: PgInt = env_defaults.DEFAULT_DB_IDLE_TIMEOUT_MS
    db_connection_timeout_ms: PgInt = env_defaults.DEFAULT_DB_CONNECTION_TIMEOUT_MS
    db_statement_timeout_ms: PgInt = env_defaults.DEFAULT_DB_STATEMENT_TIMEOUT_MS
    session_idle_minutes: PositiveInt = env_defaults.DEFAULT_SESSION_IDLE_MINUTES
    session_absolute_hours: PositiveInt = env_defaults.DEFAULT_SESSION_ABSOLUTE_HOURS
    vigencia_resolucion_dias: PositiveInt = env_defaults.DEFAULT_VIGENCIA_RESOLUCION_DIAS
    plazo_aviso_horas: PositiveInt = env_defaults.DEFAULT_PLAZO_AVISO_HORAS
    archivado_interval_seconds: PositiveInt = env_defaults.DEFAULT_ARCHIVADO_INTERVAL_SECONDS
    archivado_lote: PositiveInt = env_defaults.DEFAULT_ARCHIVADO_LOTE
    rate_limit_window_seconds: PositiveInt = env_defaults.DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    rate_limit_auth_capacity: PositiveInt = env_defaults.DEFAULT_RATE_LIMIT_AUTH_CAPACITY
    rate_limit_anon_capacity: PositiveInt = env_defaults.DEFAULT_RATE_LIMIT_ANON_CAPACITY
    rate_limit_login_window_seconds: PositiveInt = env_defaults.DEFAULT_RATE_LIMIT_LOGIN_WINDOW_SECONDS
    rate_limit_login_capacity: PositiveInt = env_defaults.DEFAULT_RATE_LIMIT_LOGIN_CAPACITY
    rate_limit_login_ip_capacity: PositiveInt = env_defaults.DEFAULT_RATE_LIMIT_LOGIN_IP_CAPACITY

    @field_validator("cookie_secret_previous", "cors_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value: object) -> object:
        return _split_list(value)

    @field_validator("cors_origins")
    @classmethod
    def check_origins(cls, value: list[str]) -> list[str]:
        if not all(_is_origin(origin) for origin in value):
            message = "debe ser un origen válido (esquema, dominio y puerto, sin ruta ni comodín)"
            raise ValueError(message)
        return value

    @field_validator("trust_proxy", mode="before")
    @classmethod
    def check_trust_proxy(cls, value: object) -> object:
        if value not in {"true", "false", True, False}:
            message = "debe ser true o false"
            raise ValueError(message)
        return value == "true" if isinstance(value, str) else value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        for scheme in POSTGRES_SCHEMES:
            if value.startswith(scheme):
                return PSYCOPG_SCHEME + value.removeprefix(scheme)
        if value.startswith(PSYCOPG_SCHEME):
            return value
        message = "DATABASE_URL debe ser una URL de PostgreSQL"
        raise ValueError(message)

    @property
    def docs_enabled(self) -> bool:
        return self.node_env != NodeEnv.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()
