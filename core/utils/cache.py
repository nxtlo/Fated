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

import collections.abc as collections
import copy
import datetime
import logging
import typing
import inspect

import aioredis
from hikari.internal import collections as hikari_collections

from . import traits
from .interfaces import HashView

_LOG: typing.Final[logging.Logger] = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Memory types.
MKT = typing.TypeVar("MKT")
MVT = typing.TypeVar("MVT")

# Hash types.
HashT = traits.HashT
FieldT = traits.FieldT
ValueT = traits.ValueT

T = typing.TypeVar("T")


class Hash(
    traits.HashRunner, typing.Generic[traits.HashT, traits.FieldT, traits.ValueT]
):
    # For some reason its not showing the inherited class docs.

    """A Basic generic Implementation of redis hash protocol.

    Example
    -------
    ```py
    # `str` is the name of the hash, `hikari.Snowflake` is the key, `hikari.Member` is the value.
    cache: HashRunner[str, hikari.SnowFlake, hikari.Member] = cache.Hash()
    member = await rest.fetch_member(...)
    await cache.set("members", member.id, member)

    ```

    Note
    ----
    This is meant to be a Key-Value cache for light-weight stuff for fast access,
    Means you can't cache the whole member object in the hash.

    Use The Memory cache if you want to cache a an object or impl your own marshaller.
    You can also use Snab's sake cache instead.
    """

    __slots__: typing.Sequence[str] = ("_injector", "_password")
    from .config import Config as __Config

    def __init__(
        self,
        host: str = __Config().REDIS_HOST,
        port: int = __Config().REDIS_PORT,
        password: str | None = __Config().REDIS_PASSWORD,
        /,
        *,
        db: str | int = 0,
        ssl: bool = False,
        max_connections: int = 0,
        decode_responses: bool = True,
        **kwargs: typing.Any,
    ) -> None:
        self._injector = aioredis.Redis(
            host=host,
            port=port,
            password=password,  # type: ignore
            retry_on_timeout=True,
            ssl=ssl,
            db=db,
            decode_responses=decode_responses,
            max_connections=max_connections,
            **kwargs,
        )

    async def __call__(
        self, *_: typing.Any, **__: typing.Any
    ) -> Hash[HashT, FieldT, ValueT]:
        return self

    async def __execute_command(
        self,
        command: str,
        hash: HashT,
        /,
        *,
        field: FieldT | str = "",  # This is actually required.
        value: ValueT | str = "",
    ) -> typing.Any:
        fmt = "{} {} {} {}".format(command, hash, field, value)
        return await self._injector.execute_command(fmt)

    async def set(self, hash: HashT, field: FieldT, value: ValueT) -> None:
        return await self.__execute_command("HSET", hash, field=field, value=value)

    async def setx(self, hash: HashT, field: FieldT) -> typing.Any:
        await self.__execute_command("HSETNX", hash, field=field)

    async def remove(self, hash: HashT) -> bool | None:
        cmd: int = await self.__execute_command("DEL", hash)
        if cmd != 1:
            _LOG.warn(
                f"Result is {bool(cmd)}, Means hash {hash} doesn't exists. returning."
            )
            return None
        return bool(cmd)

    async def len(self, hash: HashT) -> int:
        return await self.__execute_command("HLEN", hash)

    async def all(
        self, hash: HashT
    ) -> collections.MutableSequence[HashView[ValueT]] | None:
        coro: dict[typing.Any, typing.Any] = await self.__execute_command("HVALS", hash)
        pending = []
        for v in coro:
            pending.append(HashView(key=hash, value=v))
        return pending or None

    async def delete(self, hash: HashT, field: FieldT) -> None:
        return await self.__execute_command("HDEL", hash, field=field)

    async def exists(self, hash: HashT, field: FieldT) -> bool:
        send: int = await self.__execute_command("HEXISTS", hash, field=field)
        return bool(send)

    async def get(self, hash: HashT, field: FieldT) -> ValueT:
        return await self.__execute_command("HGET", hash, field=field)

    def clone(self) -> Hash[HashT, FieldT, ValueT]:
        return copy.deepcopy(self)


class Memory(hikari_collections.ExtendedMutableMapping[MKT, MVT]):
    """A standard basic in memory cache that we may use it for APIs, embeds, etc."""

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

        self.expire_after = expire_after
        self.on_expire = on_expire

        if not expire_after:
            # By default we only need to cache stuff
            # for 12 hours.
            expire_after = datetime.timedelta(hours=12)

        self._map = hikari_collections.TimedCacheMap[MKT, MVT](
            expiry=expire_after, on_expire=on_expire
        )

    def clear(self) -> None:
        self._map.clear()
        self.expire_after = None
        self.on_expire = None

    def copy(self) -> hikari_collections.ExtendedMutableMapping[MKT, MVT]:
        return self._map.copy()

    # Need this to cache the memory pointers.
    def memory(self, key: MKT) -> str:
        return hex(id(self._map[key]))

    clone = copy
    """An alias to `Memory.copy()"""

    def freeze(self) -> collections.MutableMapping[MKT, MVT]:
        return self._map.freeze()

    def view(self) -> str:
        return self.__repr__()

    def values(self) -> collections.ValuesView[MVT]:
        return self._map.values()

    def keys(self) -> collections.KeysView[MKT]:
        return self._map.keys()

    def put(self, key: MKT, value: MVT) -> Memory[MKT, MVT]:
        self.__setitem__(key, value)
        return self

    def set_expiry(self, date: datetime.timedelta) -> Memory[MKT, MVT]:
        self.expire_after = date
        return self

    def set_on_expire(self, obj: collections.Callable[..., T]) -> T:
        self.on_expire = obj
        obj.__doc__ = f'{type(obj).__name__}({inspect.getargs(obj.__code__)}) -> {obj.__annotations__.get("return")}'
        return typing.cast(T, obj)

    def __repr__(self) -> str:
        docs = inspect.getdoc(self.on_expire)
        return "\n".join(
            f"MemoryCache({k}={v!r}, expires_at={self.expire_after}, on_expire={docs})"
            for k, v in self._map.items()
        )

    def __iter__(self) -> collections.Iterator[MKT]:
        return self._map.__iter__()

    def __getitem__(self, k: MKT) -> MVT:
        return self._map.__getitem__(k)

    def __setitem__(self, k: MKT, v: MVT) -> None:
        self._map.__setitem__(k, v)

    def __delitem__(self, v: MKT) -> None:
        self._map.__delitem__(v)

    def __len__(self) -> int:
        return self._map.__len__()
