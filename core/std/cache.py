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

__all__: tuple[str, ...] = ("Memory", "Hash")

import asyncio
import datetime
import logging
import math
import time
import typing

import aiobungie
import hikari
import redis.asyncio as redis
from hikari.internal import collections as hikari_collections
from hikari.internal import data_binding

from core import models

from . import boxed, config, traits

if typing.TYPE_CHECKING:
    import collections.abc as collections


_LOG: typing.Final[logging.Logger] = logging.getLogger("fated.cache")

MKT = typing.TypeVar("MKT")
MVT = typing.TypeVar("MVT")


@typing.final
class Hash(traits.HashRunner):
    __slots__: typing.Sequence[str] = (
        "__connection",
        "_aiobungie_client",
        "_lock",
        "_config",
        "_expiring_map",
    )

    def __init__(
        self,
        config: config.Config,
        /,
        aiobungie_client: aiobungie.traits.ClientApp | None = None,
    ) -> None:
        self._config = config
        self._aiobungie_client = aiobungie_client
        self._lock = asyncio.Lock()
        self._expiring_map = Memory[hikari.Snowflake, float]()
        self.__connection: redis.Redis | None = None

    def __repr__(self) -> str:
        return "<Hash>"

    async def open(self) -> None:
        if self.__connection is not None:
            raise RuntimeError("Redis cache already open.") from None

        pool_conn = redis.ConnectionPool(
            host=self._config.REDIS_HOST,
            port=self._config.REDIS_PORT,
            password=self._config.REDIS_PASSWORD,
            retry_on_timeout=True,
        )
        self.__connection = redis.Redis(connection_pool=pool_conn)

    async def close(self) -> None:
        if self.__connection is not None:
            await self.__connection.close()

    def client(self, client: aiobungie.traits.ClientApp) -> None:
        self._aiobungie_client = client

    async def set_bungie_tokens(
        self, user: hikari.Snowflake, response: aiobungie.builders.OAuth2Response
    ) -> None:
        await self.__dump_tokens(
            user, response.access_token, response.refresh_token, response.expires_in
        )

    async def remove_bungie_tokens(self, user: hikari.Snowflake) -> None:
        assert self.__connection is not None
        await self.__connection.hdel("tokens", str(user))  # type: ignore

    async def get_bungie_tokens(self, user: hikari.Snowflake) -> models.Tokens:
        is_expired = await self._is_expired(user)

        if (tokens := await self.__loads_tokens(user)) and not is_expired:
            return tokens

        async with self._lock:
            if (tokens := await self.__loads_tokens(user)) and not is_expired:
                return tokens

        response = await self.__refresh_token(user)

        expiry = time.monotonic() + math.floor(response.expires_in * 0.99)
        self._expiring_map[user] = expiry
        return await self.__dump_tokens(
            user, response.access_token, response.refresh_token, expiry
        )

    # Check whether the Bungie OAuth tokens are expired or not.
    # If expired we refresh them.
    async def _is_expired(self, user: hikari.Snowflake) -> bool:
        # We could just use an lur cache decorator here.
        if user in self._expiring_map:
            return time.monotonic() >= self._expiring_map[user]

        token = await self.__loads_tokens(user)
        self._expiring_map[user] = token["expires"]
        return time.monotonic() >= token["expires"]

    # Dump the authorized data as a string JSON object.
    async def __dump_tokens(
        self,
        owner: hikari.Snowflake,
        access_token: str,
        refresh_token: str,
        expires_in: float,
    ) -> models.Tokens:
        assert self.__connection is not None
        now = datetime.datetime.now(datetime.UTC)
        payload = data_binding.default_json_dumps(
            {
                "access": access_token,
                "refresh": refresh_token,
                "expires": expires_in,
                "date": str(now),
            }
        )
        await self.__connection.hset(
            name="tokens", key=str(owner), value=payload.decode()
        )  # type: ignore
        return models.Tokens(
            access=access_token, refresh=refresh_token, expires=expires_in, date=now
        )

    # Loads the authorized data from a string JSON object to a Python dict object.
    async def __loads_tokens(self, owner: hikari.Snowflake) -> models.Tokens:
        assert self.__connection is not None
        resp: str = await self.__connection.hget("tokens", str(owner))  # type: ignore
        if resp:
            data = data_binding.default_json_loads(str(resp))
            assert isinstance(data, dict)
            return models.Tokens(**data)

        raise LookupError(f"Tokens not found for {owner}") from None

    async def __refresh_token(
        self, owner: hikari.Snowflake
    ) -> aiobungie.builders.OAuth2Response:
        assert self._aiobungie_client is not None

        tokens = await self.__loads_tokens(owner)
        refresh = tokens.get("refresh")

        try:
            response = await self._aiobungie_client.rest.refresh_access_token(refresh)
            _LOG.info(
                "Refreshed tokens for %s Last refresh was %s", owner, tokens["date"]
            )
        except aiobungie.BadRequest as err:
            raise RuntimeError(
                f"Couldn't refresh tokens for {owner} due to `{err.message}`"
            ) from err
        return response


@typing.final
class Memory(hikari_collections.FreezableDict[MKT, MVT]):
    """In-Memory cache."""

    if typing.TYPE_CHECKING:
        _data: collections.MutableMapping[MKT, MVT]

    def __init__(self) -> None:
        super().__init__()

    def view(self) -> str:
        return self.__repr__()

    def put(self, key: MKT, value: MVT) -> Memory[MKT, MVT]:
        self[key] = value
        return self

    def __repr__(self) -> str:
        if not self._data:
            return "`EmptyCache`"

        return "\n".join(
            boxed.with_block(f"MemoryCache({k}={v!r})") for k, v in self._data.items()
        )
