"""Settings read from the environment or `.env` (like `IOptions<T>` bound from configuration).

The app's database is `WATCH_TONIGHT_MONGODB_URI`, which defaults to the local container.
`MONGODB_URI` in `.env` is the cloud M0 cluster of spike 09 and is never read by default
(owner, 2026-11-25).
"""

from typing import Final
from urllib.parse import urlsplit

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_MONGODB_URI: Final[str] = "mongodb://localhost:27017/?directConnection=true"
_LOCAL_HOSTS: Final = frozenset({"localhost", "127.0.0.1", "::1"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WATCH_TONIGHT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mongodb_uri: SecretStr = SecretStr(LOCAL_MONGODB_URI)
    mongodb_database: str = "watch_tonight"
    # TMDB's key keeps the name the spikes use (no prefix).
    tmdb_api_key: SecretStr | None = Field(default=None, validation_alias="TMDB_API_KEY")


def _host_name(host: str) -> str:
    """`localhost:27017` → `localhost`; `[::1]:27017` → `::1`."""
    if host.startswith("["):
        return host[1 : host.index("]")]
    return host.split(":", 1)[0]


def is_local_mongodb(uri: str) -> bool:
    """True when every host in the URI is this machine. `mongodb+srv` is never local."""
    parts = urlsplit(uri)
    if parts.scheme != "mongodb":
        return False
    hosts = [h for h in parts.netloc.rsplit("@", 1)[-1].split(",") if h]
    return bool(hosts) and all(_host_name(h) in _LOCAL_HOSTS for h in hosts)
