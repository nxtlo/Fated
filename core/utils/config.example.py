from __future__ import annotations

__all__: typing.Sequence[str] = ("Config",)

import dataclasses
import typing

from hikari import config as hikari_config


@dataclasses.dataclass(slots=True, repr=False, frozen=True)
class Config:
    """Main shared configuration between the bot, client, database and other."""

    BOT_TOKEN: str = "BOT_TOKEN"

    # This is optional. The component will not load if these field are not set.
    BUNGIE_TOKEN: str | None = None
    BUNGIE_CLIENT_ID: int | None = None
    BUNGIE_CLIENT_SECRET: str | None = None

    # postgresql stuff.
    DB_NAME: str = "NAME"
    DB_USER: str = "PSQL_USER"
    DB_PASSWORD: str | int = "PSQL_PASSWORD"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432

    # Bot's cache
    CACHE_SETTINGS: hikari_config.CacheComponents = (
        hikari_config.CacheComponents.GUILD_CHANNELS
        | hikari_config.CacheComponents.GUILDS
        | hikari_config.CacheComponents.MEMBERS
        | hikari_config.CacheComponents.ROLES
    )

    # Redis stuff
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    @classmethod
    def into_dotenv(cls) -> Config:
        """Loads the configs from `.env` file if installed and set."""
        try:
            import os as _os

            import dotenv

            dotenv.load_dotenv()
        except ImportError:
            raise

        return Config(
            BOT_TOKEN=_os.environ["BOT_TOKEN"],
            DB_NAME=_os.environ["DB_NAME"],
            DB_PASSWORD=_os.environ["DB_PASSEORD"],
            DB_HOST=_os.environ["DB_HOST"],
            DB_PORT=int(_os.environ["DB_PORT"]),
            DB_USER=_os.environ["DB_USER"],
            BUNGIE_TOKEN=_os.environ.get("BUNGIE_TOKEN", ""),
            BUNGIE_CLIENT_ID=int(_os.environ.get("BUNGIE_CLIENT_TOKEN", 0)),
            BUNGIE_CLIENT_SECRET=_os.environ.get("BUNGIE_CLIENT_SECRET", ""),
            CACHE_SETTINGS=cls.CACHE_SETTINGS,
            REDIS_HOST=_os.environ.get("REDIS_HOST", cls.REDIS_HOST),
            REDIS_PORT=int(_os.environ.get("REDIS_PORT", cls.REDIS_PORT)),
            REDIS_PASSWORD=_os.environ.get("REDIS_PASSWORD"),
        )

    def verify_bungie_tokens(self) -> bool:
        return (
            self.BUNGIE_CLIENT_ID is not None
            and self.BUNGIE_CLIENT_SECRET is not None
            and self.BUNGIE_TOKEN is not None
        )
