# -*- cofing: utf-8 -*-
# MIT License
#
# Copyright (c) 2021 - Present nxtlo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""The bot's configuration."""

from __future__ import annotations

__all__: typing.Sequence[str] = ("Config",)

import typing

import attr
import hikari


@attr.define(repr=False, weakref_slot=False, slots=True)
class Config:
    """Handle the bot's configs."""

    BOT_TOKEN: typing.Final[str] = attr.field(default="TOKEN")
    """The bot's token."""

    BUNGIE_TOKEN: typing.Final[str | None] = attr.field(default=None)
    """Bungie api key for interacting with aiobungie."""

    DB_USER: typing.Final[str] = attr.field(default="PSQL_USER")
    """Your database username."""

    DB_PASSWORD: typing.Final[str | int] = attr.field(default=":SQL_PASSWORD")
    """Your database password. this can be an int or a string."""

    DB_HOST: typing.Final[str] = attr.field(default="127.0.0.1")
    """Your database host. default to `127.0.0.1`"""

    DB_PORT: typing.Final[int] = attr.field(default=5432)
    """Your database's port. Defaults to 5432."""

    RAPID_TOKEN: typing.Final[str | None] = attr.field(default=None)
    """Rapid api token for urban def command."""

    CACHE: hikari.CacheComponents = attr.field(
        default=(
            hikari.CacheComponents.GUILD_CHANNELS
            | hikari.CacheComponents.GUILDS
            | hikari.CacheComponents.MEMBERS
            | hikari.CacheComponents.ROLES
        )
    )
    """The bot's cache settings."""
