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

import datetime

__all__: tuple[str, ...] = (
    "HTTPNet",
    "Wrapper",
    "Error",
    "NotFound"
)

import asyncio
import logging
import random as random_
import typing
from http import HTTPStatus as http

import uuid
import tempfile
import aiohttp
import attr
import hikari
import humanize
import multidict
from aiobungie.internal import time
from hikari import _about as about
from hikari.internal.time import (
    fast_iso8601_datetime_string_to_datetime as fast_datetime,
)
from tanjun import _backoff as backoff
from yarl import URL

from . import consts, interfaces, traits

if typing.TYPE_CHECKING:
    import types

    import tanjun.abc
    from hikari.internal import data_binding
    _GETTER_TYPE = typing.TypeVar("_GETTER_TYPE", covariant=True)

DATA_TYPE = dict[str, typing.Any | int | str | hikari.UndefinedType | multidict.CIMultiDictProxy[str]]
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
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str | URL,
        read: bool = False,
        getter: _GETTER_TYPE | None = None,
        **kwargs: typing.Any,
    ) -> data_binding.JSONObject | data_binding.JSONArray | bytes | _GETTER_TYPE | None:
        async with rely:
            return await self.__request(method, url, read, getter, **kwargs)

    @typing.final
    async def __request(
        self,
        method: typing.Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str | URL,
        read: bool = False,
        getter: _GETTER_TYPE | None = None,
        **kwargs: typing.Any,
    ) -> data_binding.JSONObject | data_binding.JSONArray | bytes | _GETTER_TYPE | None:

        data: data_binding.JSONObject | data_binding.JSONArray | bytes | _GETTER_TYPE | None = None
        backoff_ = backoff.Backoff(max_retries=6)

        user_agent: typing.Final[
            str
        ] = f"Fated DiscorsBot Hikari/{about.__version__}"

        kwargs["headers"] = headers = {}
        headers["User-Agent"] = user_agent

        while True:
            async for _ in backoff_:
                try:
                    async with self._session.request(  # type: ignore
                        method, URL(url) if type(url) is URL else url, **kwargs
                    ) as response:

                        if http.MULTIPLE_CHOICES > response.status >= http.OK:
                            _LOG.debug(
                                f"{method} Request Success from {str(response.real_url)}"
                            )

                            if read is True:
                                return await response.read()

                            data = await response.json(encoding="utf-8")
                            if data is None:
                                return None

                            if getter is not None:
                                try:
                                    return data[getter]  # type: ignore
                                except KeyError:
                                    raise LookupError(
                                        response.real_url, response.headers, data
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
        await self.acquire()
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

    def __init__(self, client: HTTPNet) -> None:
        self._net = client

    async def get_anime(
        self,
        _: tanjun.abc.SlashContext,
        name: str | None = None,
        *,
        random: bool | None = None,
        genre: str,
    ) -> hikari.Embed | None:
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
                            return None

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
                        start_date = humanize.precisedelta(
                            time.clean_date(raw_start_date),
                            minimum_unit='minutes'
                        )

                    if (raw_end_date := anime.get("end_date")) is not None:
                        end_date = humanize.precisedelta(
                            time.clean_date(raw_end_date),
                            minimum_unit='minutes'
                        )

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
        self, _: tanjun.abc.SlashContext, name: str, /
    ) -> hikari.Embed | None:
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
                        return None

                    embed.description = manga.get("synopsis", hikari.UNDEFINED)
                    embed.set_author(url=manga.get("url", str(hikari.UNDEFINED)), name=manga.get("title", hikari.UNDEFINED))

                    embed.set_image(manga.get("image_url", None))
                    start_date: hikari.UndefinedOr[str] = hikari.UNDEFINED
                    end_date: hikari.UndefinedOr[str] = hikari.UNDEFINED

                    if (raw_start_date := manga.get("start_date")) is not None:
                        start_date = humanize.precisedelta(time.clean_date(raw_start_date), minimum_unit='minutes')

                    if (raw_end_date := manga.get("end_date")) is not None:
                        end_date = humanize.precisedelta(time.clean_date(raw_end_date), minimum_unit='minutes')

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
    ) -> hikari.Embed | None:
        async with self._net as cli:

            resp = (
                await cli.request(
                    "GET", consts.API["urban"], params={"term": name.lower()}, getter="list"
                ) or []
            )

            if not resp:
                await ctx.respond(f"Couldn't find definition about `{name}`")
                return None

            defn = random_.choice(resp)  # type: ignore
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

    async def do_tts(self, model: str, *, text: str) -> typing.Any:
        async with self._net as cli:
            json = {
                "inference_text": text,
                "tts_model_token": consts.TTS[model],
                "uuid_idempotency_token": str(uuid.uuid4())
            }
            resp = await cli.request(
                "POST",
                "https://api.fakeyou.com/tts/inference",
                json=json
            )
            if (job_token := resp.get("inference_job_token")):
                wave = await cli.request(
                    "GET",
                    f"https://api.fakeyou.com/tts/job/{job_token}"
                )
                if isinstance(wave, dict):
                    if (audio_path := wave['state'].get("maybe_public_bucket_wav_audio_path")) is None:
                        await asyncio.sleep(2)
                    # We need to make 2 requests here while the audio is being uploaded.
                    wave = await cli.request(
                        "GET",
                        f"https://api.fakeyou.com/tts/job/{job_token}"
                    )
                    audio_path = wave['state'].get("maybe_public_bucket_wav_audio_path")
                    final_path = f'https://storage.googleapis.com/vocodes-public{audio_path}'
                    wave_bytes = await cli.request('GET', final_path, read=True)
                    if isinstance(wave_bytes, bytes):
                        tmp = tempfile.TemporaryFile('wb')
                        with tmp as t:
                            t.write(wave_bytes)
                            t.seek(0)
                        return t

    def _set_repo_owner_attrs(self, payload: dict[str, typing.Any]) -> interfaces.GithubUser:
        user: dict[str, typing.Any] = payload
        created_at: datetime.datetime | None = None
        if(raw_created := user.get('created_at')):
            created_at = fast_datetime(raw_created)  # type: ignore
        user_obj = interfaces.GithubUser(
            api=self,
            name=user.get("login", hikari.UNDEFINED),
            id=user["id"],
            url=user['html_url'],
            repos_url=user['repos_url'],
            public_repors=user.get("public_repos", hikari.UNDEFINED),
            avatar_url=user.get("avatar_url", None),
            email=user.get("email", None),
            type=user['type'],
            bio=user.get("bio", hikari.UNDEFINED),
            created_at=created_at,
            location=user.get("location", None),
            followers=user.get("followers", hikari.UNDEFINED),
            following=user.get("following", hikari.UNDEFINED)
        )
        return user_obj

    def _set_repo_attrs(
        self,
        payload: dict[str, list[dict[str, typing.Any]]]
    ) -> typing.Sequence[interfaces.GithubRepo]:
        repos: typing.Sequence[interfaces.GithubRepo] = []

        for repo in payload['items']:
            if(repo_license := repo.get("license")) is not None:
                license_name = repo_license['name']
            repo_obj = interfaces.GithubRepo(
                id=repo['id'],
                name=repo['full_name'],
                description=repo.get("description", None),
                url=repo['html_url'],
                is_forked=repo['fork'],
                created_at=time.clean_date(repo['created_at']).astimezone(),
                last_push=humanize.precisedelta(
                    time.clean_date(
                        repo['pushed_at']),
                    minimum_unit='minutes'
                ),
                page=repo.get("homepage", None),
                size=repo['size'],
                license=license_name,
                is_archived=repo['archived'],
                forks=repo['forks_count'],
                open_issues=repo['open_issues_count'],
                stars=repo['stargazers_count'],
                language=repo.get("language", hikari.UNDEFINED),
                owner=self._set_repo_owner_attrs(repo.get("owner", None))
            )
            repos.append(repo_obj)
        return repos

    async def get_git_user(self, name: str, /) -> interfaces.GithubUser | None:
        async with self._net as cli:
            if(raw_user := await cli.request("GET", URL(consts.API['git']['user']) / name)) is not None:
                return self._set_repo_owner_attrs(raw_user)  # type: ignore
            return None

    async def get_git_repo(self, name: str) -> typing.Sequence[interfaces.GithubRepo] | None:
        async with self._net as cli:
            if(raw_repo := await cli.request(
                "GET",
                consts.API['git']['repo'].format(name)
            )) is not None:
                return self._set_repo_attrs(raw_repo)  # type: ignore
            return None

@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class Error(RuntimeError):
    """Main error class."""
    data: DATA_TYPE = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class Unauthorized(Error):
    data: DATA_TYPE = attr.field()

@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class NotFound(Error):
    data: DATA_TYPE = attr.field()

@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class RateLimited(Error):
    data: DATA_TYPE = attr.field()
    retry_after: float = attr.field()
    message: str = attr.field()

@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class BadRequest(Error):
    data: DATA_TYPE = attr.field()


@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class Forbidden(Error):
    data: DATA_TYPE = attr.field()

@attr.define(weakref_slot=False, repr=False, auto_exc=True)
class InternalError(Error):
    data: DATA_TYPE = attr.field()

async def acquire_errors(response: aiohttp.ClientResponse, /) -> Error:
    json_data = await response.json()
    real_data = {
        "data": json_data,
        "status": response.status,
        "message": json_data.get("message", hikari.UNDEFINED),
        "error": json_data.get("error", hikari.UNDEFINED),
        "headers": response.headers,
        "url": str(response.real_url)
    }

    # Black doesn'n know what match is.

    # fmt: off
    match response.status:
        case http.NOT_FOUND:
            return NotFound(real_data)
        case http.BAD_REQUEST:
            return BadRequest(real_data)
        case http.FORBIDDEN:
            return Forbidden(real_data)
        case http.TOO_MANY_REQUESTS:
            retry_after = response.headers["Retry-After"]
            message = response.headers["message"]
            return RateLimited(real_data, message=message, retry_after=float(retry_after))
        case http.UNAUTHORIZED:
            return Unauthorized(real_data)
        case _:
            pass

    status = http(response.status)
    match status:
        case (500, 502, 504):  # noqa: E211
            return InternalError(real_data)
        case _:
            return Error(real_data)
    # fmt: on
