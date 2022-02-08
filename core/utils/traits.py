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

"""Protocols or traits or whatever used for our impls. and also used as dependency injectors."""

from __future__ import annotations

__all__: tuple[str, ...] = ("PoolRunner", "NetRunner", "HashRunner")

import typing

from hikari.internal import fast_protocol as fast  # too long >:

if typing.TYPE_CHECKING:
    import collections.abc as collections
    import pathlib

    import aiobungie
    import aiohttp
    import asyncpg
    import yarl
    from hikari import files, snowflakes
    from hikari.internal import data_binding

    _GETTER_TYPE = typing.TypeVar("_GETTER_TYPE", covariant=True)


@typing.runtime_checkable
class HashRunner(fast.FastProtocolChecking, typing.Protocol):
    """Core redis hash trait. This hash is used to store fast key -> value objects for our needs."""

    __slots__ = ()

    async def set_prefix(self, guild_id: snowflakes.Snowflake, prefix: str) -> None:
        """Sets a guild prefix given a guild snowflake."""

    async def get_prefix(self, guild_id: snowflakes.Snowflake) -> str:
        """Returns the cached prefix for a guild snowflake."""
        raise NotImplementedError

    async def remove_prefix(self, guild_id: snowflakes.Snowflake) -> None:
        """Removes a prefix for a guild snowflake id."""

    async def set_mute_roles(
        self, guild_id: snowflakes.Snowflake, role_id: snowflakes.Snowflake
    ) -> None:
        """Sets the mute role for a guild snowflake."""

    async def get_mute_role(
        self, guild_id: snowflakes.Snowflake
    ) -> snowflakes.Snowflake:
        """Return the cached mute role id. Raised LookupError if not found."""
        raise NotImplementedError

    async def remove_mute_role(self, guild_id: snowflakes.Snowflake) -> None:
        """Removes the cached mute role id for the given snowflake guild."""

    # BTW there's no background task that runs every x hours to refresh the Bungie OAuth2 tokens.
    # All this are handled internally, We check if the token is expired or not when the user
    # invokes a command that requires OAuth2. If the token is expired we refresh them immediantly.
    # else we just return the data. Since we're using redis this should always be a fast response.

    async def set_bungie_tokens(
        self, user: snowflakes.Snowflake, respons: aiobungie.OAuth2Response
    ) -> None:
        """Cache a hikari snowflake to the returned OAuth2 response object tokens."""

    async def get_bungie_tokens(
        self, user: snowflakes.Snowflake
    ) -> collections.Mapping[
        typing.Literal["access", "refresh", "date", "expires"], str | float
    ]:
        """Gets loaded dict object of the user snowflake tokens.

        This dictionary contains 4 keys:
            * access: str -> The access token for the snowflake
            * refresh: str -> The refresh token for the snowflake
            * expires: float -> When's this token going to expire. This is handled internally
            * date: ISO string datetime -> When was this snowflake cached/refreshed at.
        """
        raise NotImplementedError

    async def remove_bungie_tokens(self, user: snowflakes.Snowflake) -> None:
        """Removes the snowflake user's cached OAuth tokens."""
        raise NotImplementedError


@typing.runtime_checkable
class PoolRunner(fast.FastProtocolChecking, typing.Protocol):
    """Core asyncpg pool trait. Every impl should have these methods."""

    __slots__ = ()

    @property
    def pool(self) -> asyncpg.Pool:
        raise NotImplementedError

    @property
    def pools(self) -> int:
        """Return the count of all running pools."""
        raise NotImplementedError

    @classmethod
    async def create_pool(cls, *, build: bool = False) -> asyncpg.Pool:
        """Initialize and creates a new connection pool."""
        raise NotImplementedError

    async def close(self) -> None:
        """Closes all pool connections."""
        raise NotImplementedError

    @staticmethod
    def tables(path: pathlib.Path | None = None) -> str:
        """Returns the source of the tables that this pool will build."""
        raise NotImplementedError


@typing.runtime_checkable
class NetRunner(fast.FastProtocolChecking, typing.Protocol):
    """Core trait for the HTTP client impl."""

    __slots__ = ()

    async def acquire(self) -> aiohttp.ClientSession:
        """Acquires the session if its closed or set to `hikari.UNDEFINED`"""
        raise NotImplementedError

    async def close(self) -> None:
        """Closes the HTTP client session."""

    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str | yarl.URL,
        getter: typing.Any | _GETTER_TYPE | None = None,
        json: typing.Optional[data_binding.JSONObjectBuilder] = None,
        auth: typing.Optional[str] = None,
        unwrap_bytes: bool = False,
        **kwargs: typing.Any,
    ) -> data_binding.JSONArray | data_binding.JSONObject | files.Resourceish | _GETTER_TYPE | None:
        """Perform an HTTP request.

        Parameters
        ----------
        method : `str`
            The HTTP request method.
        url : `str` | `yarl.URL`
            The API endpoint URL.
        getter: `T?`
            if your data is a `dict['key' -> 'val']` You can use this
            parameter to get something the value from the dict
            This is equl to `request['key']` -> `request(getter='key')`
        json : `data_binding.JSONObjectBuilder?`
            Optional JSON data that can be passed to the request if needed.
        unwrap_bytes : `bool`
            If set to true then the request will return the bytes of the response.
        auth : `str?`
            If the request requires a Bearer access token for auth, This can be passed here.
        **kwargs : `Any`
            Other keyword arguments you can pass to the request.
        """

    @staticmethod
    async def error_handle(response: aiohttp.ClientResponse, /) -> typing.NoReturn:
        """Handling the request errors."""
        raise NotImplementedError
