from __future__ import annotations

__all__: typing.Sequence[str] = ("Config",)

import dataclasses
import typing

from hikari import config as hikari_config


@dataclasses.dataclass(slots=True, repr=False, eq=False, frozen=True)
class Config:
    """Handle the bot's configs."""

    BOT_TOKEN: typing.Final[str] = dataclasses.field(default="TOKEN")
    """The bot's token."""

    DB_NAME: typing.Final[str] = dataclasses.field(default="NAME")
    """Your database name."""

    BUNGIE_TOKEN: typing.Final[str | None] = dataclasses.field(default=None)
    """Bungie api key for interacting with aiobungie."""

    BUNGIE_CLIENT_ID: typing.Final[int] = dataclasses.field(default=0)
    """Bungie Application client id for account syncing."""

    BUNGIE_CLIENT_SECRET: typing.Final[str] = dataclasses.field(default="")
    """Bungie Application client secret for account syncing."""

    DB_USER: typing.Final[str] = dataclasses.field(default="PSQL_USER")
    """Your database username."""

    DB_PASSWORD: typing.Final[str | int] = dataclasses.field(default="PSQL_PASSWORD")
    """Your database password. this can be an int or a string."""

    DB_HOST: typing.Final[str] = dataclasses.field(default="127.0.0.1")
    """Your database host. default to `127.0.0.1`"""

    DB_PORT: typing.Final[int] = dataclasses.field(default=5432)
    """Your database's port. Defaults to 5432."""

    CACHE: hikari_config.CacheComponents = dataclasses.field(
        default=(
            hikari_config.CacheComponents.GUILD_CHANNELS
            | hikari_config.CacheComponents.GUILDS
            | hikari_config.CacheComponents.MEMBERS
            | hikari_config.CacheComponents.ROLES
        )
    )
    """The bot's cache settings."""

    REDIS_HOST: typing.Final[str] = dataclasses.field(default="127.0.0.1")
    """The redis server host."""

    REDIS_PORT: typing.Final[int] = dataclasses.field(default=6379)
    """The redis server port."""

    REDIS_PASSWORD: typing.Final[str | None] = dataclasses.field(default=None)
    """The redis server password, This can be left None."""
