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
import yarl
from hikari import _about as about
from hikari.internal import data_binding, net, ux
from yuyo import backoff

from . import traits

if typing.TYPE_CHECKING:
    import types


_LOG: typing.Final[logging.Logger] = logging.getLogger("core.net")
_strigify = hikari.impl.RESTClientImpl._stringify_http_message  # type: ignore


@typing.final
class HTTPNet(traits.NetRunner):
    """A client to make HTTP requests with."""

    __slots__: typing.Sequence[str] = ("_session", "_lock")

    def __init__(self, lock: asyncio.Lock | None = None) -> None:
        self._session: hikari.UndefinedOr[aiohttp.ClientSession] = hikari.UNDEFINED
        self._lock = lock

    async def acquire(self) -> aiohttp.ClientSession:
        if isinstance(self._session, hikari.UndefinedType):
            http_settings = hikari.impl.HTTPSettings()
            connector = net.create_tcp_connector(http_settings)
            self._session = net.create_client_session(
                connector,
                connector_owner=False,
                http_settings=http_settings,
                raise_for_status=False,
                trust_env=False,
            )
            return self._session
        raise RuntimeError("Session is already running...")

    async def close(self) -> None:
        if self._session is not hikari.UNDEFINED and not self._session.closed:
            try:
                await self._session.close()
            except aiohttp.ClientOSError as e:
                raise RuntimeError("Couldn't close session.") from e
        self._session = hikari.UNDEFINED

    @typing.final
    async def request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str | yarl.URL,
        getter: str | None = None,
        json: typing.Optional[data_binding.JSONObjectBuilder] = None,
        auth: typing.Optional[str] = None,
        unwrap_bytes: bool = False,
        **kwargs: typing.Any,
    ) -> data_binding.JSONObject | data_binding.JSONArray | hikari.Resourceish | None:
        if not self._lock:
            self._lock = asyncio.Lock()

        async with self._lock:
            return await self._request(
                method=method,
                url=url,
                getter=getter,
                unwrap_bytes=unwrap_bytes,
                json=json,
                auth=auth,
                **kwargs,
            )

    @typing.final
    async def _request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str | yarl.URL,
        getter: str | None = None,
        json: typing.Optional[data_binding.JSONObjectBuilder] = None,
        auth: typing.Optional[str] = None,
        unwrap_bytes: bool = False,
        **kwargs: typing.Any,
    ) -> data_binding.JSONObject | data_binding.JSONArray | hikari.Resourceish | None:

        data: data_binding.JSONObject | data_binding.JSONArray | hikari.Resourceish | None = (
            None
        )
        backoff_ = backoff.Backoff(max_retries=6)
        response: aiohttp.ClientResponse

        user_agent: typing.Final[
            str
        ] = f"Fated DiscordBot(https://github.com/nxtlo/Fated) Hikari/{about.__version__}"

        kwargs["headers"] = headers = data_binding.StringMapBuilder()
        headers.put("User-Agent", user_agent)

        if auth is not None:
            headers.put("Authorization", f"Bearer {auth}")

        stack = contextlib.AsyncExitStack()

        while True:
            async for _ in backoff_:
                assert self._session is not hikari.UNDEFINED
                try:
                    response = await stack.enter_async_context(
                        self._session.request(method, url, json=json, **kwargs)
                    )
                    if (
                        http.HTTPStatus.MULTIPLE_CHOICES
                        > response.status
                        >= http.HTTPStatus.OK
                    ):
                        if unwrap_bytes:
                            return await response.read()

                        data = await response.json(encoding="utf-8")
                        _LOG.debug(
                            "%s Success from %s\n%s",
                            method,
                            response.real_url.human_repr(),
                            _strigify(response.headers, data)  # type: ignore
                            if _LOG.isEnabledFor(ux.TRACE)
                            else "",
                        )

                        if data is None:
                            return None

                        if getter is not None:
                            try:
                                return data[getter]  # type: ignore
                            except KeyError:
                                raise LookupError(
                                    f"{response.real_url!s}",
                                    f"{response.headers!r}",
                                    data,
                                )

                        return data

                    # Handle the ratelimiting.
                    if response.status == http.HTTPStatus.TOO_MANY_REQUESTS:
                        _LOG.warning(
                            f"We're being ratelimited {response.headers}, {method}::{response.url.human_repr()}"
                        )
                        backoff_.set_next_backoff(float(random.random() / 2))

                    response.raise_for_status()

                except (aiohttp.ContentTypeError, aiohttp.ClientPayloadError):
                    raise

    async def __aenter__(self):
        await self.acquire()
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
