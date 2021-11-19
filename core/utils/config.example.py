from __future__ import annotations

__all__: typing.Sequence[str] = ("Config",)

import typing

import attr
from hikari import config as hikari_config


@attr.frozen(repr=False, weakref_slot=False)
class Config:
    """Handle the bot's configs."""

    BOT_TOKEN: typing.Final[str] = attr.field(default="TOKEN")
    """The bot's token."""

    DB_NAME: typing.Final[str] = attr.field(default="NAME")
    """Your database name."""

    BUNGIE_TOKEN: typing.Final[str | None] = attr.field(default=None)
    """Bungie api key for interacting with aiobungie."""

    DB_USER: typing.Final[str] = attr.field(default="PSQL_USER")
    """Your database username."""

    DB_PASSWORD: typing.Final[str | int] = attr.field(default="PSQL_PASSWORD")
    """Your database password. this can be an int or a string."""

    DB_HOST: typing.Final[str] = attr.field(default="127.0.0.1")
    """Your database host. default to `127.0.0.1`"""

    DB_PORT: typing.Final[int] = attr.field(default=5432)
    """Your database's port. Defaults to 5432."""

    CACHE: hikari_config.CacheComponents = attr.field(
        default=(
            hikari_config.CacheComponents.GUILD_CHANNELS
            | hikari_config.CacheComponents.GUILDS
            | hikari_config.CacheComponents.MEMBERS
            | hikari_config.CacheComponents.ROLES
        )
    )
    """The bot's cache settings."""

    REDIS_HOST: typing.Final[str] = attr.field(default="127.0.0.1")
    """The redis server host."""

    REDIS_PORT: typing.Final[int] = attr.field(default=6379)
    """The redis server port."""

    REDIS_PASSWORD: typing.Final[str | None] = attr.field(default=None)
    """The redis server password, This can be left None."""
