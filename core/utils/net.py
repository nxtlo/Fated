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

"""An aiohttp client and a wrapper to make api requests."""

from __future__ import annotations

__all__: tuple[str, ...] = (
    "HTTPNet",
    "Wrapper"
)

import asyncio
import logging
import random as random_
import types
import typing
from http import HTTPStatus as http

import aiohttp
import attr
import hikari
import multidict
import tanjun
from aiobungie.internal import time
from hikari import _about as about
from hikari.internal.time import (
    fast_iso8601_datetime_string_to_datetime as fast_datetime,
)
from tanjun import _backoff as backoff
from yarl import URL

from . import consts, interfaces, traits

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
        self._session: hikari.UndefinedOr[aiohttp.ClientSession] = hikari.UNDEFINED

    async def acquire(self) -> None:
        if self._session is hikari.UNDEFINED:
            self._session = aiohttp.ClientSession()

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
        method: str,
        url: str | URL,
        getter: typing.Any | None = None,
        **kwargs: typing.Any,
    ) -> consts.JsonObject | None:
        async with rely:
            return await self._request(method, url, getter, **kwargs)

    @typing.final
    async def _request(
        self,
        method: str,
        url: str | URL,
        getter: typing.Any | None = None,
        **kwargs: typing.Any,
    ) -> consts.JsonObject | None:

        data: consts.JsonObject | None = None
        backoff_ = backoff.Backoff(max_retries=6)

        user_agent: typing.Final[
            str
        ] = f"Tsujigiri DiscorsBot Hikari/{about.__version__}"

        kwargs["headers"] = headers = dict()
        headers["User-Agent"] = user_agent

        while 1:
            async for _ in backoff_:
                try:
                    await self.acquire()
                    async with self._session.request( # type: ignore
                        method, URL(url) if type(url) is URL else url, **kwargs
                    ) as response:

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
                    backoff_.set_next_backoff(exc.retry_after)

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

class Wrapper(interfaces.APIWrapper):
    """Wrapped around different apis.
    
    Attributes
    ----------
    client : `tairs.NetRunner`
        The aiohttp client runner.
        This always defaults to `net.HTTPNet` is should not be modified.
    """

    __slots__: typing.Sequence[str] = ("_net",)

    def __init__(self, client: traits.NetRunner) -> None:
        self._net = client

    async def get_anime(
        self,
        ctx: tanjun.abc.SlashContext,
        name: str | None = None,
        *,
        random: bool | None = None,
        genre: str,
    ) -> hikari.Embed | hikari.UndefinedType:
        embed = hikari.Embed(colour=consts.COLOR["invis"])

        async with self._net as cli:

            if random is True and name is None:
                # This is True by default in case the name is None.
                path = f"{consts.API['anime']}/genre/anime/{consts.GENRES[genre]}/1"
            else:
                path = f'{consts.API["anime"]}/search/anime?q={str(name).lower()}/Zero&page=1&limit=1'

            # This kinda brain fuck but it will raise KeyError
            # error if we don't check before we make the actual request.
            if genre is not None and random and name is None:
                getter = "anime"
                start = "airing_start"
            else:
                getter = "results"
                start = "start_date"

            if (
                raw_anime := await cli.request(
                    "GET",
                    path,
                    getter=getter,
                )
            ) is not None:
                if isinstance(raw_anime, list):
                    if name is None and random:
                        anime = random_.choice(raw_anime)
                        genres: list[str] = list(
                            map(lambda tag: tag["name"], anime["genres"])
                        )
                    else:
                        try:
                            anime = raw_anime[0]
                        except (KeyError, TypeError):
                            await ctx.mark_not_found()
                            return hikari.UNDEFINED

                    embed.title = anime.get("title", hikari.UNDEFINED)
                    embed.description = anime.get("synopsis", hikari.UNDEFINED)
                    embed.set_author(url=anime.get("url", str(hikari.UNDEFINED)))

                    try:
                        embed.set_footer(text=", ".join(genres))
                    except UnboundLocalError:
                        pass

                    embed.set_image(anime.get("image_url", None))

                    start_date: hikari.UndefinedOr[str] = hikari.UNDEFINED
                    end_date: hikari.UndefinedOr[str] = hikari.UNDEFINED
                    if (raw_start_date := anime.get(start)) is not None:
                        start_date = time.human_timedelta(
                            time.clean_date(raw_start_date)
                        )

                    if (raw_end_date := anime.get("end_date")) is not None:
                        end_date = time.human_timedelta(time.clean_date(raw_end_date))

                    meta_data = (
                        ("Episodes", anime.get("episodes", hikari.UNDEFINED)),
                        ("Score", anime.get("score", hikari.UNDEFINED)),
                        ("Aired at", start_date),
                        ("Finished at", end_date),
                        ("Community members", anime.get("members", hikari.UNDEFINED)),
                        ("Being aired", anime.get("airing", hikari.UNDEFINED)),
                    )
                    for k, v in meta_data:
                        embed.add_field(k, str(v), inline=True)
            return embed

    async def get_manga(
        self, ctx: tanjun.abc.SlashContext, name: str, /
    ) -> hikari.Embed | hikari.UndefinedType:
        embed = hikari.Embed(colour=consts.COLOR["invis"])

        async with self._net as cli:
            if (
                raw_manga := await cli.request(
                    "GET",
                    f'{consts.API["anime"]}/search/manga?q={name}/Zero&page=1&limit=1',
                    getter="results",
                )
            ) is not None:
                if isinstance(raw_manga, list):
                    try:
                        manga = raw_manga[0]
                    except KeyError:
                        await ctx.respond("Anime was not found.")
                        return hikari.UNDEFINED

                    embed.title = manga.get("title", hikari.UNDEFINED)
                    embed.description = manga.get("synopsis", hikari.UNDEFINED)
                    embed.set_author(url=manga.get("url", str(hikari.UNDEFINED)))

                    embed.set_image(manga.get("image_url", None))
                    start_date: hikari.UndefinedOr[str] = hikari.UNDEFINED
                    end_date: hikari.UndefinedOr[str] = hikari.UNDEFINED

                    if (raw_start_date := manga.get("start_date")) is not None:
                        start_date = time.human_timedelta(
                            time.clean_date(raw_start_date)
                        )

                    if (raw_end_date := manga.get("end_date")) is not None:
                        end_date = time.human_timedelta(time.clean_date(raw_end_date))

                    meta_data = (
                        ("Chapters", manga.get("chapters", hikari.UNDEFINED)),
                        ("Volumes", manga.get("volumes", hikari.UNDEFINED)),
                        ("Type", manga.get("type", hikari.UNDEFINED)),
                        ("Score", manga.get("score", hikari.UNDEFINED)),
                        ("Published at", start_date),
                        ("Ended at", end_date),
                        ("Community members", manga.get("members", hikari.UNDEFINED)),
                        ("Being published", manga.get("publishing", hikari.UNDEFINED)),
                    )
                    for k, v in meta_data:
                        embed.add_field(k, str(v), inline=True)
            return embed

    async def get_definition(
        self, ctx: tanjun.abc.SlashContext, name: str
    ) -> hikari.Embed | hikari.UndefinedType:
        async with self._net as cli:

            resp = (
                await cli.request(
                    "GET", consts.API["urban"], params={"term": name.lower()}, getter="list"
                )
                or []
            )

            if not resp:
                await ctx.respond(f"Couldn't find definition about `{name}`")
                return hikari.UNDEFINED

            defn = choice(resp)  # type: ignore
            embed = hikari.Embed(
                colour=consts.COLOR["invis"], title=f"Definition for {name}"
            )

            def replace(s: str) -> str:
                return s.replace("]", "").replace("[", "")

            try:
                example: str = defn["example"]
                embed.add_field("Example", replace(example))
            except (KeyError, ValueError):
                pass

            # This cannot be None.
            definition: str = defn["definition"]
            embed.description = replace(definition)

            try:
                up_voted: int = defn["thumbs_up"]
                down_votes: int = defn["thumbs_down"]
                embed.set_footer(
                    text=f"\U0001f44d {up_voted} - \U0001f44e {down_votes}"
                )
            except KeyError:
                pass

            try:
                date: str = defn["written_on"]
                embed.timestamp = fast_datetime(date)  # type: ignore
            except KeyError:
                pass

            url: str = defn["permalink"]
            author: str = defn["author"]
            embed.set_author(name=author, url=url)
        return embed

@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class Error(RuntimeError):
    """Main error class."""

    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: consts.JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class Unauthorized(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: consts.JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class NotFound(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: consts.JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class RateLimited(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: consts.JsonObject = attr.field()
    retry_after: float = attr.field()
    message: str = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class BadRequest(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: consts.JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class Forbidden(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: consts.JsonObject = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class InternalError(Error):
    url: str | URL = attr.field()
    headers: multidict.CIMultiDictProxy[str] = attr.field()
    data: consts.JsonObject = attr.field()


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

    # Black doesn'n know what match is.
    
    # fmt: off
    match response.status:
        case http.NOT_FOUND:
            return NotFound(*real_data)
        case http.BAD_REQUEST:
            return BadRequest(*real_data)
        case http.FORBIDDEN:
            return Forbidden(*real_data)
        case http.TOO_MANY_REQUESTS:
            retry_after = response.headers["Retry-After"]
            message = response.headers["message"]
            return RateLimited(*real_data, message=message, retry_after=float(retry_after))
        case http.UNAUTHORIZED:
            return Unauthorized(*real_data)
        case _:
            pass

    status = http(response.status)
    match status:
        case (500, 502, 504):
            return InternalError(*real_data)
        case _:
            return Error(*real_data)
    # fmt: on
