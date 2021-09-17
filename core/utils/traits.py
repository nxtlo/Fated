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
"""Runtime protocols."""

from __future__ import annotations

import aiohttp

__all__: list[str] = ["PoolRunner", "NetRunner"]

import typing

import asyncpg
import yarl
from hikari.internal.fast_protocol import FastProtocolChecking

if typing.TYPE_CHECKING:
    import types

    from . import consts


@typing.runtime_checkable
class PoolRunner(FastProtocolChecking, typing.Protocol):
    """A typed asyncpg pool protocol."""

    __slots__: typing.Sequence[str] = ()

    @property
    def pool(self) -> asyncpg.Pool | None:
        """Access to `self._pool`."""

    @classmethod
    async def create_pool(cls, *, build: bool = False) -> asyncpg.pool.Pool | None:
        """Created a new pool.

        Parameters
        ----------
        build : `bool`
            if set to `True` the pool will build the tables.
            This is only called when you run `python run.py db init`

        Returns
        --------
        `asyncpg.pool.Pool` | `None`
            An asyncpg connection pool or None.
        """

    async def execute(
        self, sql: str, /, *args: typing.Any, timeout: float | None = None
    ) -> None:
        """A typed asyncpg execute method.

        Parameters
        -----------
        sql : `str`
            The sql query.
        args : `typing.Any`
            A sequence of any arguments.
        timeout : `float` | `None`
            An execution timeout.

        Returns
        -------
        `builtins.NoneType`
            None
        """

    async def fetch(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[asyncpg.Record]:
        """A typed asyncpg fetch method.

        Parameters
        ----------
        sql : `str`
            The sql query
        args : `typing.Any`
            A sequence of any arguments.
        timeout : `float` | `None`
            An execution timeout.

        Returns
        -------
        `typing.List[asyncpg.Record]`
            A typing of an asyncpg Records.
        """

    async def fetchrow(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[asyncpg.Record]:
        """A typed asyncpg fetchrow method.

        Parameters
        ----------
        sql : `str`
            The sql query
        args : `typing.Any`
            A sequence of any arguments.
        timeout : `float` | `None`
            An execution timeout.

        Returns
        -------
        `typing.List[asyncpg.Record]`
            The first row found in an asyncpg Record.
        """

    async def fetchval(
        self,
        sql: str,
        /,
        *args: typing.Any,
        column: int | None = None,
        timeout: float | None = None,
    ) -> typing.Any:
        """A typed asyncpg fetchval method.

        Parameters
        ----------
        sql : `str`
            The sql query
        args : `typing.Any`
            A sequence of any arguments.
        timeout : `float` | `None`
            An execution timeout.

        Returns
        -------
        `typing.Any`
            First Any value found in the first record.
        """

    async def close(self) -> None:
        """Closes the database."""

    @staticmethod
    def tables() -> str:
        """The sql schema file"""


@typing.runtime_checkable
class NetRunner(FastProtocolChecking, typing.Protocol):
    """An interface for our http client."""

    __slots__: typing.Sequence[str] = ()

    # This is required here for injecting it
    # to the client.
    def __call__(self) -> typing.NoReturn:
        raise NotImplementedError

    async def acquire(self) -> None:
        """Acquires the session if its closed or set to None."""

    async def close(self) -> None:
        """Closes the http session."""

    async def request(
        self,
        method: str,
        url: str | yarl.URL,
        getter: typing.Any | None = None,
        **kwargs: typing.Any,
    ) -> consts.JsonObject:
        """Perform an http request

        Parameters
        ----------
        method : `str`
            The http request method.
            This can be `GET`. `POST`. `PUT`. `DELETE`. etc.

        Note
        ----
        if you're performing any request
        that requires Auth you'll need to pass headers
        to the kwargs like this `headers={'X-API-KEY': ...}`

        url : `str` | `yarl.URL`
            The api url. This also can be used as a `yarl.URL(...)` object.
        getter: `typing.Any`
            if your data is a dict[..., ...] You can use this
            parameter to get something specific value from the dict
            This is equl to `request['key']` -> `request(getter='key')`
        kwargs : `typing.Any`
            Other keyword arguments you can pass to the request.
        """

    async def __aenter__(self) -> NetRunner:
        """`async with` for context management."""

    async def __aexit__(
        self,
        _: BaseException | None,
        __: BaseException | None,
        ___: types.TracebackType | None,
    ) -> None:
        """Closes the session when making the requests with `async with`."""

    @staticmethod
    async def error_handle(response: aiohttp.ClientResponse, /) -> typing.NoReturn:
        """Handling the request errors."""
