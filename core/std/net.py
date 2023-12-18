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

"""HTTP and Networking model."""

from __future__ import annotations

__all__: tuple[str] = ("HTTPNet",)

import asyncio
import contextlib
import datetime
import http
import logging
import random
import typing

import aiohttp
import hikari
from hikari import _about as about
from hikari.internal import data_binding, net
from yuyo import backoff

from . import traits

if typing.TYPE_CHECKING:
    import types


_LOG: typing.Final[logging.Logger] = logging.getLogger("core.net")


@typing.final
class HTTPNet(traits.NetRunner):
    """A client to make HTTP requests with."""

    __slots__: typing.Sequence[str] = ("_session", "_lock")

    def __init__(self, lock: asyncio.Lock | None = None) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._lock = lock

    async def close(self) -> None:
        if self._session is None:
            raise RuntimeError("Cannot close a session that's already running.")
        await self._session.close()
        self._session = None

    async def _create_session(self):
        if self._session is not None:
            raise RuntimeError("Session is already running...")

        http_settings = hikari.impl.HTTPSettings()
        connector = net.create_tcp_connector(http_settings)
        self._session = net.create_client_session(
            connector,
            connector_owner=False,
            http_settings=http_settings,
            raise_for_status=False,
            trust_env=False,
        )

    @typing.overload
    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        getter: str | None = None,
        json: data_binding.JSONObjectBuilder | None = None,
        *,
        unwrap_bytes: bool = True,
    ) -> bytes | None:
        ...

    @typing.overload
    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        getter: str | None = None,
        json: data_binding.JSONObjectBuilder | None = None,
    ) -> data_binding.JSONArray | data_binding.JSONObject | None:
        ...

    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        getter: str | None = None,
        json: data_binding.JSONObjectBuilder | None = None,
        *,
        unwrap_bytes: bool = False,
    ) -> data_binding.JSONObject | data_binding.JSONArray | bytes | None:
        if not self._lock:
            self._lock = asyncio.Lock()

        async with self._lock:
            return await self._request(
                method=method,
                url=url,
                getter=getter,
                unwrap_bytes=unwrap_bytes,
                json=json,
            )

    async def _request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        getter: str | None = None,
        json: data_binding.JSONObjectBuilder | None = None,
        *,
        unwrap_bytes: bool | None = False,
    ) -> data_binding.JSONObject | data_binding.JSONArray | bytes | None:
        assert self._session is not None
        data: data_binding.JSONObject | data_binding.JSONArray | bytes | None = None
        backoff_ = backoff.Backoff(max_retries=4)

        user_agent: typing.Final[
            str
        ] = f"Fated DiscordBot(https://github.com/nxtlo/Fated) Hikari/{about.__version__}"

        headers = {}
        headers["User-Agent"] = user_agent

        stack = contextlib.AsyncExitStack()

        while True:
            async for _ in backoff_:
                try:
                    response = await stack.enter_async_context(
                        self._session.request(method, url, json=json, headers=headers)
                    )

                    if (
                        http.HTTPStatus.MULTIPLE_CHOICES
                        > response.status
                        >= http.HTTPStatus.OK
                    ):
                        if not data:
                            return None

                        if unwrap_bytes:
                            return await response.read()

                        if response.content_type == "application/json":
                            data = data_binding.default_json_loads(
                                await response.read()
                            )
                            _LOG.debug(
                                "%s Success from %s\n%s",
                                method,
                                response.real_url.human_repr(),
                            )

                            if getter:
                                try:
                                    return data[getter]  # type: ignore
                                except KeyError:
                                    raise LookupError(
                                        f"Key {getter} not found in {data!r}"
                                        f"{response.real_url!s}",
                                    )

                            return data

                    # Handle the ratelimiting.
                    if response.status == http.HTTPStatus.TOO_MANY_REQUESTS:
                        _LOG.warning(
                            f"We're being ratelimited {response.headers}, {method}::{response.url.human_repr()}"
                        )
                        backoff_.set_next_backoff(random.random() / 2)

                    response.raise_for_status()

                except (aiohttp.ContentTypeError, aiohttp.ClientPayloadError):
                    raise

    async def __aenter__(self):
        await self._create_session()
        _LOG.debug("Acquired client session %s", datetime.datetime.now().astimezone())
        return self

    async def __aexit__(
        self,
        _: BaseException | None,
        __: BaseException | None,
        ___: types.TracebackType | None,
    ) -> None:
        await self.close()
        _LOG.debug("Closed client session %s", datetime.datetime.now().astimezone())

    def __repr__(self) -> str:
        return f"HTTPNet(session: {self._session!r})"
