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
import inspect
import logging
import math
import time
import typing

import aiobungie
import aioredis
import hikari

from hikari.internal import collections as hikari_collections

from . import traits

try:
    import ujson as json  # type: ignore
except ImportError:
    import json

if typing.TYPE_CHECKING:
    import collections.abc as collections


_LOG: typing.Final[logging.Logger] = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Memory types.
MKT = typing.TypeVar("MKT")
MVT = typing.TypeVar("MVT")

_T = typing.TypeVar("_T")


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

    async def set_prefix(self, guild_id: hikari.Snowflake, prefix: str) -> None:
        await self.__connection.hset("prefixes", str(guild_id), prefix)  # type: ignore

    async def get_prefix(self, guild_id: hikari.Snowflake) -> str:
        if prefix := await self.__connection.hget("prefixes", str(guild_id)):
            return typing.cast(str, prefix)

        raise LookupError

    async def remove_prefix(self, *guild_ids: hikari.Snowflake) -> None:
        await self.__connection.hdel("prefixes", *list(map(str, guild_ids)))

    async def set_mute_roles(
        self, guild_id: hikari.Snowflake, role_id: hikari.Snowflake
    ) -> None:
        await self.__connection.hset("mutes", str(guild_id), role_id)  # type: ignore

    async def get_mute_role(
        self, guild_id: hikari.Snowflake
    ) -> hikari.Snowflake:
        role_id: int
        if role_id := await self.__connection.hget("mutes", str(guild_id)):
            return hikari.Snowflake(role_id)

        raise LookupError

    async def remove_mute_role(self, guild_id: hikari.Snowflake) -> None:
        await self.__connection.hdel("mutes", str(guild_id))

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
    ) -> str:
        body = json.dumps(
            {
                "access": access_token,
                "refresh": refresh_token,
                "expires": expires_in,
                "date": f"{datetime.datetime.now()!s}",
            }
        )
        await self.__connection.hset(name="tokens", key=owner, value=body)  # type: ignore
        return body

    # Loads the authorized data from a string JSON object to a Python dict object.
    async def __loads_tokens(
        self, owner: hikari.Snowflake
    ) -> dict[str, str | float]:
        resp: hikari.Snowflake = await self.__connection.hget("tokens", owner)
        if resp:
            return json.loads(str(resp))

        raise LookupError

    async def __refresh_token(
        self, owner: hikari.Snowflake
    ) -> aiobungie.OAuth2Response:
        assert (
            self._aiobungie_client is not None
        ), "Aiobungie client should never be `None` to refresh the tokens."

        try:
            tokens = await self.__loads_tokens(owner)
        except LookupError:
            raise

        refresh = tokens["refresh"]
        assert isinstance(refresh, str)

        try:
            response = await self._aiobungie_client.rest.refresh_access_token(refresh)
            _LOG.info(
                "Refreshed tokens for %s Last refresh was %s", owner, tokens["date"]
            )
        except aiobungie.BadRequest as err:
            raise RuntimeError(f"Couldn't refresh tokens for {owner}.") from err
        return response

    async def set_bungie_tokens(
        self, user: hikari.Snowflake, respons: aiobungie.OAuth2Response
    ) -> None:
        await self.__dump_tokens(
            user, respons.access_token, respons.refresh_token, respons.expires_in
        )

    # This impl hikari's client creds strat.
    async def get_bungie_tokens(
        self, user: hikari.Snowflake
    ) -> dict[str, str | float]:
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
        tokens_ = await self.__dump_tokens(
            user, response.access_token, response.refresh_token, expiry
        )
        return json.loads(tokens_)

    async def remove_bungie_tokens(self, user: hikari.Snowflake) -> None:
        await self.__connection.hdel("tokens", str(user))


class Memory(hikari_collections.ExtendedMutableMapping[MKT, MVT]):
    """A standard in-memory cache that we use it for APIs responses, embeds, etc.

    This implements hikari's `TimedCacheMap` with more functionality.
    It will pop entries after 12 hours by default `"IF"` new entries are inserted into the cache.
    This can be modified by changing `expire_after`.
    """

    __slots__ = ("_map", "expire_after", "on_expire")
    _map: hikari_collections.ExtendedMutableMapping[MKT, MVT]

    def __init__(
        self,
        expire_after: datetime.timedelta | float | None = None,
        *,
        on_expire: collections.Callable[..., typing.Any] | None = None,
    ) -> None:

        if isinstance(expire_after, float):
            expire_after = datetime.timedelta(seconds=expire_after)

        if expire_after is None:
            # By default we only need to cache stuff
            # for 12 hours.
            expire_after = datetime.timedelta(hours=12)

        self.on_expire = on_expire
        self.expire_after = expire_after
        self._map = hikari_collections.TimedCacheMap[MKT, MVT](
            expiry=expire_after, on_expire=on_expire
        )

    def clear(self) -> None:
        self._map.clear()
        self.expire_after = None
        self.on_expire = None

    def copy(self) -> hikari_collections.ExtendedMutableMapping[MKT, MVT]:
        return self._map.copy()

    clone = copy
    """An alias to `Memory.copy()"""

    # Technically, We can use into_iter().for_each(...) but we want to iter through k, v.
    def for_each(
        self, devours: collections.Callable[[MKT, MVT], typing.Any]
    ) -> Memory[MKT, MVT]:
        """Performs an inline for loop for each key, value cached and devours/maps it to a callable."""
        for k, v in self._map.items():
            devours(k, v)
        return self

    def into_iter(self, predicate: collections.Callable[[MKT], typing.Any], /) -> hikari.LazyIterator[MVT]:
        """Returns a flat lazy iterator of this cache's values based on the predicate keys."""
        for k, _ in self._map.items():
            if predicate(k):
                return hikari.FlatLazyIterator(list(self._map.values()))
        return hikari.FlatLazyIterator([])

    def freeze(self) -> collections.MutableMapping[MKT, MVT]:
        return self._map.freeze()

    # Do we actually need all this...

    def view(self) -> str:
        return repr(self)

    def values(self) -> collections.ValuesView[MVT]:
        return self._map.values()

    def keys(self) -> collections.KeysView[MKT]:
        return self._map.keys()

    def get(self, key: MKT, default: _T | None = None, /) -> MVT | _T | None:
       return self._map.get(key, default) 

    def put(self, key: MKT, value: MVT) -> Memory[MKT, MVT]:
        self._map[key] = value
        return self

    def set_expiry(self, date: datetime.timedelta) -> Memory[MKT, MVT]:
        self.expire_after = date
        return self

    def set_on_expire(self, obj: collections.Callable[..., _T]) -> _T:
        self.on_expire = obj
        obj.__doc__ = f'{type(obj).__name__}({inspect.getargs(obj.__code__)}) -> {obj.__annotations__.get("return")}'
        return typing.cast(_T, obj)

    def __repr__(self) -> str:
        if not self._map:
            return "`EmptyCache`"

        docs = inspect.getdoc(self.on_expire)
        return "\n".join(
            f"MemoryCache({k}={v!r}, expires_at={self.expire_after}, on_expire={docs})"
            for k, v in self._map.items()
        )

    def __iter__(self) -> collections.Iterator[MKT]:
        return iter(self._map)

    def __getitem__(self, k: MKT) -> MVT:
        return self._map[k]

    def __setitem__(self, k: MKT, v: MVT) -> None:
        self._map[k] = v

    def __delitem__(self, k: MKT) -> None:
        del self._map[k]

    def __len__(self) -> int:
        return len(self._map)
