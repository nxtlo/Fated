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

"""A very simple aiohttp session to make api requests."""

from __future__ import annotations

import asyncio
import logging
import typing
from http import HTTPStatus as http

import aiohttp
import attr
import multidict
from yarl import URL

_LOG: typing.Final[logging.Logger] = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class _Rely:

    __slots__: typing.Sequence[str] = ("_lock",)

    def __init__(self) -> None:

        self._lock = asyncio.Lock()

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, _, __, ___) -> None:
        self._lock.release()

    async def acquire(self) -> None:
        await self._lock.acquire()


rely = _Rely()

JsonObject = dict[str, typing.Any] | list[dict[str, typing.Any]] | None


class HTTPNet:
    """A client to make http requests with."""

    __slots__: typing.Sequence[str] = ("_session", "_lock")

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            try:
                await self._session.close()
            except aiohttp.ClientOSError as e:
                raise RuntimeError("Couldn't close session.") from e
        self._session = None

    async def request(
        self, method: str, url: str | URL, getter: typing.Any | None = None, **kwargs
    ) -> JsonObject | None:
        data: JsonObject | None = None
        while True:
            async with rely:
                await self.acquire()
                async with self._session.request(method, url, **kwargs) as response:
                    if http.MULTIPLE_CHOICES > response.status >= http.OK:
                        _LOG.debug(
                            f"{method} Request Success from {str(response.real_url)}"
                        )

                        data = await response.json(encoding="utf-8")
                        if data is None:
                            return None

                        if getter:
                            if isinstance(data, dict):
                                try:
                                    return data[getter]
                                except KeyError:
                                    _LOG.error(
                                        "{} key was not found. returning real data.".format(
                                            getter
                                        )
                                    )
                                    return data
                            raise TypeError(
                                f"Data must be a dict not {type(data).__name__}"
                            )
                        return data
                    await self.error_handle(response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, _, __, ___) -> None:
        await self.close()
        return None

    @staticmethod
    async def error_handle(response: aiohttp.ClientResponse, /) -> None:
        json_data = await response.json()
        real_data: list[typing.Any] = [
            str(response.real_url),
            response.headers,
            json_data,
        ]

        # too lazy to define them somewhere else.
        @attr.define(weakref_slot=False, repr=False)
        class NotFound(RuntimeError):
            url: str | URL = attr.field()
            headers: multidict.CIMultiDictProxy[str] = attr.field()
            data: JsonObject = attr.field()

        @attr.define(weakref_slot=False, repr=False)
        class BadRequest(RuntimeError):
            url: str | URL = attr.field()
            headers: multidict.CIMultiDictProxy[str] = attr.field()
            data: JsonObject = attr.field()

        @attr.define(weakref_slot=False, repr=False)
        class Forbidden(RuntimeError):
            url: str | URL = attr.field()
            headers: multidict.CIMultiDictProxy[str] = attr.field()
            data: JsonObject = attr.field()

        @attr.define(weakref_slot=False, repr=False)
        class InternalError(RuntimeError):
            url: str | URL = attr.field()
            headers: multidict.CIMultiDictProxy[str] = attr.field()
            data: JsonObject = attr.field()

        if response.status == http.NOT_FOUND:
            raise NotFound(*real_data)
        if response.status == http.BAD_REQUEST:
            raise BadRequest(*real_data)
        if response.status == http.FORBIDDEN:
            raise Forbidden(*real_data)

        status = http(response.status)
        if 500 <= status < 500:
            raise InternalError(*real_data)

    # TODO implement all requests we need here.
