from __future__ import annotations

__all__: typing.Sequence[str] = ("Config",)

import dataclasses
import typing

from hikari import config as hikari_config


@dataclasses.dataclass(repr=False, frozen=True, slots=True)
class Config:
    """Main shared configuration between the bot, client, database and other."""

    BOT_TOKEN: str = "..."

    BUNGIE_TOKEN: str | None = None
    BUNGIE_CLIENT_ID: int | None = None
    BUNGIE_CLIENT_SECRET: str | None = None

    DB_NAME: str = "..."
    DB_USER: str = "..."
    DB_PASSWORD: str | int = "..."
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432

    CACHE: hikari_config.CacheComponents = (
            hikari_config.CacheComponents.GUILD_CHANNELS
            | hikari_config.CacheComponents.GUILDS
            | hikari_config.CacheComponents.MEMBERS
            | hikari_config.CacheComponents.ROLES
        )

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
            CACHE=cls.CACHE,
            REDIS_HOST=_os.environ.get("REDIS_HOST", cls.REDIS_HOST),
            REDIS_PORT=int(_os.environ.get("REDIS_PORT", cls.REDIS_PORT)),
            REDIS_PASSWORD=_os.environ.get("REDIS_PASSWORD"),
        )

    def verify_bungie_tokens(self) -> bool:
        return all((self.BUNGIE_CLIENT_ID, self.BUNGIE_TOKEN, self.BUNGIE_CLIENT_SECRET))

