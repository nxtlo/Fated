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
    import aiobungie
    import aiohttp
    import asyncpg
    import yarl
    from hikari import files, snowflakes
    from hikari.internal import data_binding

    _GETTER_TYPE = typing.TypeVar("_GETTER_TYPE", covariant=True)


@typing.runtime_checkable
class HashRunner(fast.FastProtocolChecking, typing.Protocol):
    """Standard Redis hash trait. This hash is used to store fast key -> value objects for our needs."""

    __slots__ = ()

    async def set_prefix(self, guild_id: snowflakes.Snowflake, prefix: str) -> None:
        """Sets a guild prefix given a guild snowflake."""

    async def get_prefix(self, guild_id: snowflakes.Snowflake) -> str:
        """Returns the cached prefix for a guild snowflake."""
        raise NotImplementedError

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

    async def remove_prefix(self, guild_id: snowflakes.Snowflake) -> None:
        """Removes a prefix for a guild snowflake id."""

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
    ) -> dict[str, str | float]:
        """Gets loaded dict object of the user snowflake tokens.

        This dictionary contains 4 keys:
            * access: str -> The access token for the snowflake
            * refresh: str -> The refresh token for the snowflake
            * expires: float -> When's this token going to expire. This is handled internally
            * date: str date -> When was this snowflake cached, refreshed at.
        """
        raise NotImplementedError

    async def remove_bungie_tokens(self, user: snowflakes.Snowflake) -> None:
        """Removes the snowflake user's cached OAuth tokens."""
        raise NotImplementedError


@typing.runtime_checkable
class PoolRunner(fast.FastProtocolChecking, typing.Protocol):
    """A typed asyncpg pool protocol."""

    __slots__ = ()

    @property
    def pool(self) -> asyncpg.Pool | None:
        raise NotImplementedError

    @classmethod
    async def create_pool(cls, *, build: bool = False) -> PoolRunner:
        """Created a new pool.

        Parameters
        ----------
        build : `bool`
            if set to `True` the pool will build the tables.
            This is only called when you run `python run.py db init`

        Returns
        --------
        `Self`
            The pool.
        """
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
    ) -> list[typing.Any] | dict[str, typing.Any]:
        raise NotImplementedError

    async def fetchval(
        self,
        sql: str,
        /,
        *args: typing.Any,
        column: int | None = None,
        timeout: float | None = None,
    ) -> typing.Any:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    @staticmethod
    def tables() -> str:
        raise NotImplementedError


@typing.runtime_checkable
class NetRunner(fast.FastProtocolChecking, typing.Protocol):
    """An interface for our http client."""

    __slots__ = ()

    async def acquire(self) -> aiohttp.ClientSession:
        """Acquires the session if its closed or set to `hikari.UNDEFINED`"""
        raise NotImplementedError

    async def close(self) -> None:
        """Closes the http session."""

    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str | yarl.URL,
        getter: typing.Any | _GETTER_TYPE | None = None,
        read_bytes: bool = False,
        **kwargs: typing.Any,
    ) -> data_binding.JSONArray | data_binding.JSONObject | files.Resourceish | _GETTER_TYPE | None:
        """Perform an HTTP request.

        Parameters
        ----------
        method : `str`
            The http request method.
            This can be `GET`. `POST`. `PUT`. `DELETE`. etc.

        url : `str` | `yarl.URL`
            The api url. This also can be used as a `yarl.URL(...)` object.
        getter: `T`
            if your data is a dict[..., ...] You can use this
            parameter to get something specific value from the dict
            This is equl to `request['key']` -> `request(getter='key')`
        read_bytes : `bool`
            If set to true then the request will read the bytes
            and return them.
        **kwargs : `typing.Any`
            Other keyword arguments you can pass to the request.
        """

    @staticmethod
    async def error_handle(response: aiohttp.ClientResponse, /) -> typing.NoReturn:
        """Handling the request errors."""
        raise NotImplementedError
