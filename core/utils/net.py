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
import types
import typing
from http import HTTPStatus as http

import aiohttp
import attr
import multidict
import yuyo
from hikari import _about as about
from yarl import URL

from . import traits
from .consts import JsonObject

_LOG: typing.Final[logging.Logger] = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class _Rely:

    __slots__: typing.Sequence[str] = ("_lock",)

    def __init__(self) -> None:

        self._lock = asyncio.Lock()

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        _: BaseException | None,
        __: BaseException | None,
        ___: types.TracebackType | None,
    ) -> None:
        self._lock.release()

    async def acquire(self) -> None:
        await self._lock.acquire()


rely = _Rely()


class HTTPNet(traits.NetRunner):
    """A client to make http requests with."""

    __slots__: typing.Sequence[str] = ("_session",)

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

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

    @typing.final
    async def request(
        self,
        method: str,
        url: str | URL,
        getter: typing.Any | None = None,
        **kwargs: typing.Any,
    ) -> JsonObject | None:
        async with rely:
            return await self._request(method, url, getter, **kwargs)

    @typing.final
    async def _request(
        self,
        method: str,
        url: str | URL,
        getter: typing.Any | None = None,
        **kwargs: typing.Any,
    ) -> JsonObject | None:

        data: JsonObject | None = None
        backoff = yuyo.Backoff(max_retries=6)

        user_agent: typing.Final[
            str
        ] = f"Tsujigiri DiscorsBot Hikari/{about.__version__}"

        kwargs["headers"] = headers = dict()
        headers["User-Agent"] = user_agent

        while 1:
            async for _ in backoff:
                try:
                    await self.acquire()
                    async with self._session.request(
                        method, URL(url) if type(url) is URL else url, **kwargs
                    ) as response:
                        response.raise_for_status()

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
                                        raise LookupError(
                                            response.real_url, response.headers, data
                                        )

                                raise TypeError(
                                    f"Data must be a dict not {type(data).__name__}"
                                )
                            return data

                        await self.error_handle(response)

                except RateLimited as exc:
                    _LOG.warn(
                        f"We're being ratelimited for {exc.retry_after:,}: {exc.message}"
                    )
                    backoff.set_next_backoff(exc.retry_after)

                except (aiohttp.ContentTypeError, aiohttp.ClientPayloadError):
                    raise

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        _: BaseException | None,
        __: BaseException | None,
        ___: types.TracebackType | None,
    ) -> None:
        await self.close()
        return None

    @staticmethod
    async def error_handle(response: aiohttp.ClientResponse, /) -> typing.NoReturn:
        raise await acquire_errors(response)

    # TODO: maybe implement all requests we need here instead of making them in components?


@attr.define(weakref_slot=False, repr=False)
class Error(RuntimeError):
    """Main error class."""

    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False)
class Unauthorized(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False)
class NotFound(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False)
class RateLimited(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: JsonObject = attr.field()
    retry_after: float = attr.field()
    message: str = attr.field()


@attr.define(weakref_slot=False, repr=False)
class BadRequest(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False)
class Forbidden(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: JsonObject = attr.field()

@attr.define(weakref_slot=False, repr=False)
class InternalError(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: JsonObject = attr.field()

async def acquire_errors(response: aiohttp.ClientResponse, /) -> Error:
        json_data = await response.json()
        real_data: list[typing.Any] = [
            str(response.real_url),
            response.headers,
            json_data,
        ]

        try:
            real_data.append(response.headers["error"])
            real_data.append(response.headers["type"])
        except KeyError:
            pass

        # too lazy to define them somewhere else.
        if response.status == http.NOT_FOUND:
            return NotFound(*real_data)
        if response.status == http.BAD_REQUEST:
            return BadRequest(*real_data)
        if response.status == http.FORBIDDEN:
            return Forbidden(*real_data)
        if response.status == http.TOO_MANY_REQUESTS:
            retry_after = response.headers["Retry-After"]
            message = response.headers["message"]
            return RateLimited(
                *real_data, message=message, retry_after=float(retry_after)
            )
        if response.status == http.UNAUTHORIZED:
            return Unauthorized(*real_data)

        status = http(response.status)
        if 500 <= status < 500:
            return InternalError(*real_data)
        else:
            return Error(*real_data)