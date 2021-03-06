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

from __future__ import annotations

__all__: tuple[str, ...] = ("Memory", "Hash")

import asyncio
import datetime
import logging
import math
import time
import typing

import aiobungie
import aioredis
import hikari
from hikari.internal import collections as hikari_collections, cache as hikari_cache

from core import models

from . import boxed, traits

try:
    import ujson as json  # type: ignore
except ImportError:
    import json  # type: ignore


_LOG: typing.Final[logging.Logger] = logging.getLogger("fated.cache")

MKT = typing.TypeVar("MKT")
MVT = typing.TypeVar("MVT")


class Hash(traits.HashRunner):
    """A Redis hash. This is used to store fast key -> value objects for our needs."""

    __slots__: typing.Sequence[str] = ("__connection", "_aiobungie_client", "_lock")
    from .config import Config as __Config

    def __init__(
        self,
        host: str = __Config().REDIS_HOST,
        port: int = __Config().REDIS_PORT,
        password: str | None = __Config().REDIS_PASSWORD,
        /,
        aiobungie_client: aiobungie.Client | None = None,
        *,
        db: str | int = 0,
        ssl: bool = False,
        max_connections: int = 60,
        decode_responses: bool = True,
        **kwargs: typing.Any,
    ) -> None:
        pool_conn = aioredis.ConnectionPool(
            host=host,
            port=port,
            password=password,
            retry_on_timeout=True,
            db=db,
            decode_responses=decode_responses,
            max_connections=max_connections,
            **kwargs,
        )
        self.__connection = aioredis.Redis(connection_pool=pool_conn, ssl=ssl)
        self._aiobungie_client = aiobungie_client
        self._lock = asyncio.Lock()

    def __repr__(self) -> str:
        return f"Hash(client: {self.__connection!r})"

    def set_aiobungie_client(self, client: aiobungie.Client) -> None:
        self._aiobungie_client = client

    async def set_bungie_tokens(
        self, user: hikari.Snowflake, respons: aiobungie.builders.OAuth2Response
    ) -> None:
        await self.__dump_tokens(
            user, respons.access_token, respons.refresh_token, respons.expires_in
        )

    async def remove_bungie_tokens(self, user: hikari.Snowflake) -> None:
        await self.__connection.hdel("tokens", str(user))

    # This impl hikari's client creds strat.
    async def get_bungie_tokens(self, user: hikari.Snowflake) -> models.Tokens:
        is_expired = await self._is_expired(user)

        if (tokens := await self.__loads_tokens(user)) and not is_expired:
            return tokens

        async with self._lock:
            if (tokens := await self.__loads_tokens(user)) and not is_expired:
                return tokens

        try:
            response = await self.__refresh_token(user)
        except (aiobungie.Unauthorized, LookupError):
            raise

        expiry = time.monotonic() + math.floor(response.expires_in * 0.99)
        return await self.__dump_tokens(
            user, response.access_token, response.refresh_token, expiry
        )

    # Check whether the Bungie OAuth tokens are expired or not.
    # If expired we refresh them.
    async def _is_expired(self, user: hikari.Snowflake) -> bool:
        expirey = await self.__loads_tokens(user)
        return time.monotonic() >= float(expirey["expires"])

    # Dump the authorized data as a string JSON object.
    async def __dump_tokens(
        self,
        owner: hikari.Snowflake,
        access_token: str,
        refresh_token: str,
        expires_in: float,
    ) -> models.Tokens:
        now = str(datetime.datetime.now())
        payload = {
            "access": access_token,
            "refresh": refresh_token,
            "date": now,
            "expires": expires_in,
        }
        await self.__connection.hset(name="tokens", key=owner, value=json.loads(payload))  # type: ignore
        return models.Tokens(access=access_token, refresh=refresh_token, expires=expires_in, date=now)

    # Loads the authorized data from a string JSON object to a Python dict object.
    async def __loads_tokens(
        self, owner: hikari.Snowflake
    ) -> models.Tokens:
        resp: hikari.Snowflake = await self.__connection.hget("tokens", owner)
        if resp:
            return models.Tokens(**json.loads(str(resp)))

        raise LookupError

    async def __refresh_token(
        self, owner: hikari.Snowflake
    ) -> aiobungie.builders.OAuth2Response:
        assert (
            self._aiobungie_client is not None
        ), "Aiobungie client should never be `None` to refresh the tokens."

        try:
            tokens = await self.__loads_tokens(owner)
        except LookupError:
            raise

        refresh = tokens.get("refresh")

        try:
            response = await self._aiobungie_client.rest.refresh_access_token(refresh)
            _LOG.info(
                "Refreshed tokens for %s Last refresh was %s", owner, tokens["date"]
            )
        except aiobungie.BadRequest as err:
            raise RuntimeError(f"Couldn't refresh tokens for {owner}.") from err
        return response

    # Not used anymore.

    if typing.TYPE_CHECKING:
        async def set_prefix(self, guild_id: hikari.Snowflake, prefix: str) -> None:
            raise NotImplementedError

        async def get_prefix(self, guild_id: hikari.Snowflake) -> str:
            raise NotImplementedError

        async def remove_prefix(self, *guild_ids: hikari.Snowflake) -> None:
            raise NotImplementedError

        async def set_mute_roles(
            self, guild_id: hikari.Snowflake, role_id: hikari.Snowflake
        ) -> None:
            raise NotImplementedError

        async def get_mute_role(self, guild_id: hikari.Snowflake) -> hikari.Snowflake:
            raise NotImplementedError

        async def remove_mute_role(self, guild_id: hikari.Snowflake) -> None:
            # await self.__connection.hdel("mutes", str(guild_id))
            raise NotImplementedError

class Memory(hikari_collections.FreezableDict[MKT, hikari_cache.Cell[MVT]]):
    """In-Memory cache."""

    if typing.TYPE_CHECKING:
        _data: dict[MKT, hikari_cache.Cell[MVT]]

    def __init__(self) -> None:
        super().__init__()

    def view(self) -> str:
        return repr(self)

    def put(self, key: MKT, value: MVT) -> Memory[MKT, MVT]:
        self[key] = hikari_cache.Cell(value)
        return self

    def __repr__(self) -> str:
        if not self._data:
            return "`EmptyCache`"

        return "\n".join(
            boxed.with_block(f"MemoryCache({k}={v!r})") for k, v in self._data.items()
        )
