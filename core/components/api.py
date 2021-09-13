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

"""Commands that makes api calls."""

from __future__ import annotations

__all__: list[str] = ["component"]

import json
import typing
from random import choice

import hikari
import tanjun

from aiobungie.internal import time
from hikari.internal.time import (
    fast_iso8601_datetime_string_to_datetime as fast_datetime,
)
from hikari.undefined import UNDEFINED, UndefinedOr
from tanjun import abc as tabc

from core.utils import consts, format
from core.utils import net as net_
from core.utils import traits
from core.utils.config import Config

component = tanjun.Component(name="api")
config = Config()

API: dict[str, str] = {
    "anime": "https://api.jikan.moe/v3",
    "urban": "https://api.urbandictionary.com/v0/define",
}
"""A dict that holds api endpoints."""


GENRES: dict[str, int] = {
    "Action": 1,
    "Advanture": 2,
    "Drama": 8,
    "Daemons": 6,
    "Ecchi": 9,  # :eyes:
    "Magic": 16,
    "Sci Fi": 24,
    "Shounen": 27,
    "Harem": 35,  # :eyes:
    "Seinen": 42,
}
"""Anime only genres."""

PATTERN: str = r"'(\[(.+?)\])'"


class Wrapper:
    """Wrapped around different apis."""

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
        """Returns an anime from jian api."""
        embed = hikari.Embed(colour=consts.COLOR["invis"])

        async with self._net as cli:

            if random is True and name is None:
                # This is True by default in case the name is None.
                path = f"{API['anime']}/genre/anime/{GENRES[genre]}/1"
            else:
                path = f'{API["anime"]}/search/anime?q={str(name).lower()}/Zero&page=1&limit=1'

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
                        anime = choice(raw_anime)
                        genres: list[str] = list(
                            map(lambda tag: tag["name"], anime["genres"])
                        )
                    else:
                        try:
                            anime = raw_anime[0]
                        except (KeyError, TypeError):
                            await ctx.mark_not_found()
                            return hikari.UNDEFINED

                    embed.title = anime.get("title", UNDEFINED)
                    embed.description = anime.get("synopsis", UNDEFINED)
                    embed.set_author(url=anime.get("url", str(UNDEFINED)))

                    try:
                        embed.set_footer(text=", ".join(genres))
                    except UnboundLocalError:
                        pass

                    embed.set_image(anime.get("image_url", None))

                    start_date: UndefinedOr[str] = UNDEFINED
                    end_date: UndefinedOr[str] = UNDEFINED
                    if (raw_start_date := anime.get(start)) is not None:
                        start_date = time.human_timedelta(
                            time.clean_date(raw_start_date)
                        )

                    if (raw_end_date := anime.get("end_date")) is not None:
                        end_date = time.human_timedelta(time.clean_date(raw_end_date))

                    meta_data = (
                        ("Episodes", anime.get("episodes", UNDEFINED)),
                        ("Score", anime.get("score", UNDEFINED)),
                        ("Aired at", start_date),
                        ("Finished at", end_date),
                        ("Community members", anime.get("members", UNDEFINED)),
                        ("Being aired", anime.get("airing", UNDEFINED)),
                    )
                    for k, v in meta_data:
                        embed.add_field(k, str(v), inline=True)
            return embed

    async def get_manga(
        self, ctx: tanjun.abc.SlashContext, name: str, /
    ) -> hikari.Embed | hikari.UndefinedType:
        """Returns a manga from jian api."""
        embed = hikari.Embed(colour=consts.COLOR["invis"])

        async with self._net as cli:
            if (
                raw_manga := await cli.request(
                    "GET",
                    f'{API["anime"]}/search/manga?q={name}/Zero&page=1&limit=1',
                    getter="results",
                )
            ) is not None:
                if isinstance(raw_manga, list):
                    try:
                        manga = raw_manga[0]
                    except KeyError:
                        await ctx.respond("Anime was not found.")
                        return hikari.UNDEFINED

                    embed.title = manga.get("title", UNDEFINED)
                    embed.description = manga.get("synopsis", UNDEFINED)
                    embed.set_author(url=manga.get("url", str(UNDEFINED)))

                    embed.set_image(manga.get("image_url", None))
                    start_date: UndefinedOr[str] = UNDEFINED
                    end_date: UndefinedOr[str] = UNDEFINED

                    if (raw_start_date := manga.get("start_date")) is not None:
                        start_date = time.human_timedelta(
                            time.clean_date(raw_start_date)
                        )

                    if (raw_end_date := manga.get("end_date")) is not None:
                        end_date = time.human_timedelta(time.clean_date(raw_end_date))

                    meta_data = (
                        ("Chapters", manga.get("chapters", UNDEFINED)),
                        ("Volumes", manga.get("volumes", UNDEFINED)),
                        ("Type", manga.get("type", UNDEFINED)),
                        ("Score", manga.get("score", UNDEFINED)),
                        ("Published at", start_date),
                        ("Ended at", end_date),
                        ("Community members", manga.get("members", UNDEFINED)),
                        ("Being published", manga.get("publishing", UNDEFINED)),
                    )
                    for k, v in meta_data:
                        embed.add_field(k, str(v), inline=True)
            return embed

    async def get_definition(
        self, ctx: tanjun.abc.SlashContext, name: str
    ) -> hikari.Embed | hikari.UndefinedType:
        """Gets a definition from urbandefition."""
        async with self._net as cli:

            resp = (
                await cli.request(
                    "GET", API["urban"], params={"term": name.lower()}, getter="list"
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


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The anime name", default=None)
@tanjun.with_bool_slash_option("random", "Returns a random anime", default=True)
@tanjun.with_str_slash_option(
    "genre",
    "The anime genre. If left None you will get a random one.",
    default=choice(list(GENRES.keys())),
    choices=(name for name in GENRES.keys()),
)
@tanjun.as_slash_command("anime", "Returns basic information about an anime.")
async def get_anime(
    ctx: tabc.SlashContext,
    name: str,
    random: bool | None,
    genre: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = Wrapper(net)
    anime = await jian.get_anime(ctx, name, random=random, genre=genre)
    await ctx.respond(embed=anime)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The manga name")
@tanjun.as_slash_command("manga", "Returns basic information about a manga.")
async def get_manga(
    ctx: tabc.SlashContext,
    name: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = Wrapper(net)
    manga = await jian.get_manga(ctx, name)
    await ctx.respond(embed=manga)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The name of the definition.")
@tanjun.as_slash_command("def", "Returns a definition given a name.")
async def define(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    urban = Wrapper(net)
    definition = await urban.get_definition(ctx, name)
    await ctx.respond(embed=definition)


@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("url", converters=str)
@tanjun.with_parser
@tanjun.as_message_command("net")
async def run_net(
    ctx: tabc.MessageContext,
    url: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    """Make a GET http request to an api or else.

    Note: The api must be application/json type.

    TODO: make this command with options for POST and GET methods maybe?

    Parameters:
        url : str
            The api url to call.
        net : HTTPNet
            The http client we're making the request with.
    """
    async with net as cli:
        try:
            result = await cli.request("GET", url)
            formatted = format.with_block(json.dumps(result), lang="json")

        except Exception as exc:
            await ctx.respond(f"```hs\n{exc}\n```")
        try:
            await ctx.respond(formatted)
        except hikari.BadRequestError as err:
            await ctx.respond(f"```hs\n{err}\n```")


@tanjun.as_loader
def load_api(client: tanjun.Client) -> None:
    client.add_component(component.copy())
