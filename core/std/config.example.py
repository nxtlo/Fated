# -*- config: utf-8 -*-
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

from __future__ import annotations

__all__: tuple[str] = ("Config",)

import functools

import attrs
from hikari.api import config as hikari_config


@attrs.frozen
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

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    @classmethod
    @functools.cache
    def into_dotenv(cls) -> Config:
        """Loads the configs from `.env` file if installed and set."""
        import os as _os

        import dotenv

        dotenv.load_dotenv()

        return Config(
            BOT_TOKEN=_os.environ["BOT_TOKEN"],
            DB_NAME=_os.environ["DB_NAME"],
            DB_PASSWORD=_os.environ["DB_PASSWORD"],
            DB_HOST=_os.environ["DB_HOST"],
            DB_PORT=int(_os.environ["DB_PORT"]),
            DB_USER=_os.environ["DB_USER"],
            BUNGIE_TOKEN=_os.environ.get("BUNGIE_TOKEN", ""),
            BUNGIE_CLIENT_ID=int(_os.environ.get("BUNGIE_CLIENT_TOKEN", 0)),
            BUNGIE_CLIENT_SECRET=_os.environ.get("BUNGIE_CLIENT_SECRET", ""),
            REDIS_HOST=_os.environ.get("REDIS_HOST", cls.REDIS_HOST),
            REDIS_PORT=int(_os.environ.get("REDIS_PORT", cls.REDIS_PORT)),
            REDIS_PASSWORD=_os.environ.get("REDIS_PASSWORD"),
        )

    def verify_bungie_tokens(self) -> bool:
        return all(
            (self.BUNGIE_CLIENT_ID, self.BUNGIE_TOKEN, self.BUNGIE_CLIENT_SECRET)
        )

    @staticmethod
    def cache_settings() -> hikari_config.CacheComponents:
        return (
            hikari_config.CacheComponents.GUILD_CHANNELS
            | hikari_config.CacheComponents.GUILDS
            | hikari_config.CacheComponents.MEMBERS
            | hikari_config.CacheComponents.ROLES
        )
