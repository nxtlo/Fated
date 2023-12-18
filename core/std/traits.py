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

"""Types that're used as type dependency interface for tanjun."""

from __future__ import annotations

__all__: tuple[str, ...] = (
    "PartialPool",
    "PoolRunner",
    "NetRunner",
    "HashRunner",
)

import typing

from hikari.internal import fast_protocol as fast  # too long >:

if typing.TYPE_CHECKING:
    import collections.abc as collections
    import pathlib
    import types
    from typing import Self

    import aiobungie
    from hikari import iterators, snowflakes
    from hikari.internal import data_binding

    from core import models


@typing.runtime_checkable
class HashRunner(fast.FastProtocolChecking, typing.Protocol):
    """An interface for a fast key->value redis hash."""

    __slots__ = ()

    async def open(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def set_bungie_tokens(
        self, user: snowflakes.Snowflake, response: aiobungie.builders.OAuth2Response
    ) -> None:
        """Cache a hikari snowflake to the returned OAuth2 response object tokens."""

    async def get_bungie_tokens(self, user: snowflakes.Snowflake) -> models.Tokens:
        """Gets a linked Discord user's Bungie tokens."""
        raise NotImplementedError

    async def remove_bungie_tokens(self, user: snowflakes.Snowflake) -> None:
        """Removes the snowflake user's cached OAuth tokens."""
        raise NotImplementedError


@typing.runtime_checkable
class PartialPool(fast.FastProtocolChecking, typing.Protocol):
    """Partial pool trait. Types that can perform core connection requests."""

    __slots__ = ()

    async def open(self, build: bool = False) -> None:
        """Initialize and creates a new connection pool."""
        raise NotImplementedError

    async def close(self) -> None:
        """Closes all pool connections."""
        raise NotImplementedError

    @staticmethod
    def tables(path: pathlib.Path | None = None) -> str:
        """Returns the source of the tables that this pool will build."""
        raise NotImplementedError

    async def execute(
        self, sql: str, /, *args: typing.Any, timeout: float | None = None
    ) -> None:
        raise NotImplementedError

    async def fetch(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[typing.Any]:
        raise NotImplementedError

    async def fetchrow(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[typing.Any] | collections.Mapping[str, typing.Any] | tuple[typing.Any]:
        raise NotImplementedError

    async def fetchval(
        self,
        sql: str,
        /,
        *args: typing.Any,
        column: int | None = 0,
        timeout: float | None = None,
    ) -> typing.Any:
        raise NotImplementedError


@typing.runtime_checkable
class PoolRunner(fast.FastProtocolChecking, typing.Protocol):
    """Core pool trait that implements direct methods to tables."""

    __slots__ = ()

    @property
    def partial(self) -> PartialPool:
        raise NotImplementedError

    async def fetch_destiny_member(
        self, user_id: snowflakes.Snowflake
    ) -> models.Membership:
        raise NotImplementedError

    async def fetch_destiny_members(self) -> iterators.LazyIterator[models.Membership]:
        raise NotImplementedError

    async def put_destiny_member(
        self,
        user_id: snowflakes.Snowflake,
        membership_id: int,
        name: str,
        code: int,
        membership_type: aiobungie.MembershipType,
    ) -> None:
        raise NotImplementedError

    async def remove_destiny_member(self, user_id: snowflakes.Snowflake) -> None:
        raise NotImplementedError


@typing.runtime_checkable
class NetRunner(fast.FastProtocolChecking, typing.Protocol):
    """An interface for an HTTP client."""

    __slots__ = ()

    if typing.TYPE_CHECKING:

        async def __aenter__(self) -> Self:
            ...

        async def __aexit__(
            self,
            _: BaseException | None,
            __: BaseException | None,
            ___: types.TracebackType | None,
        ) -> None:
            ...

    async def close(self) -> None:
        """Closes the HTTP client session."""

    @typing.overload
    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        getter: str | None = None,
        json: data_binding.JSONObjectBuilder | None = None,
    ) -> data_binding.JSONArray | data_binding.JSONObject | None:
        ...

    @typing.overload
    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        getter: str | None = None,
        json: data_binding.JSONObjectBuilder | None = None,
        *,
        unwrap_bytes: bool,
    ) -> bytes | None:
        ...

    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        getter: str | None = None,
        json: data_binding.JSONObjectBuilder | None = None,
        unwrap_bytes: bool = False,
    ) -> data_binding.JSONArray | data_binding.JSONObject | bytes | None:
        """Perform an HTTP request."""
