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
import random

import hikari
import tanjun
from aiobungie.internal import time
from hikari.internal.time import (
    fast_iso8601_datetime_string_to_datetime as fast_datetime,
)
from hikari.undefined import UNDEFINED
from tanjun import abc as tabc

from core.utils import consts, format
from core.utils import net as net_
from core.utils.config import Config

component = tanjun.Component(name='api')
config = Config()

API: dict[str, str] = {
    "anime": "https://api.jikan.moe/v3",
    "urban": "https://mashape-community-urban-dictionary.p.rapidapi.com/define",
}
"""A dict that holds api endpoints."""

# TODO: Make all two commands in one command.


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The anime name")
@tanjun.as_slash_command("anime", "Returns basic information about an anime.")
async def get_anime(
    ctx: tabc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.injected(type=net_.HTTPNet),
) -> None:

    await ctx.defer()
    async with net as cli:
        if (
            raw_anime := await cli.request(
                "GET",
                # TODO: change the anime query to be a custom option
                # * So we can return anime or manga.
                f'{API["anime"]}/search/anime?q={name}/Zero&page=1&limit=1',
            )
        ) is not None:
            if type(raw_anime) is dict:
                try:
                    anime = raw_anime["results"][0]
                except KeyError:
                    await ctx.respond("Anime was not found.")
                    return

                embed = hikari.Embed(
                    title=anime.get("title", UNDEFINED),
                    description=anime.get("synopsis", UNDEFINED),
                    url=anime.get("url", UNDEFINED),
                )

                embed.set_image(anime.get("image_url", None))
                meta_data = (
                    ("Episodes", anime.get("episodes", UNDEFINED)),
                    ("Score", anime.get("score", UNDEFINED)),
                    (
                        "Aired at",
                        time.human_timedelta(
                            time.clean_date(anime.get("start_date", UNDEFINED))
                        ),
                    ),
                    (
                        "Finished at",
                        time.human_timedelta(
                            time.clean_date(anime.get("end_date", UNDEFINED))
                        ),
                    ),
                    ("Community members", anime.get("members", UNDEFINED)),
                    ("Being aired", anime.get("airing", UNDEFINED)),
                )
                for k, v in meta_data:
                    embed.add_field(name=k, value=v, inline=True)
                await ctx.respond(embed=embed)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The manga name")
@tanjun.with_str_slash_option("genre", "The manga's genre", default=None)
@tanjun.as_slash_command("manga", "Returns basic information about a manga.")
async def get_manga(
    ctx: tabc.SlashContext,
    name: str,
    genre: str | None,
    net: net_.HTTPNet = tanjun.injected(type=net_.HTTPNet),
) -> None:

    await ctx.defer()
    async with net as cli:
        if (
            raw_manga := await cli.request(
                "GET",
                f'{API["anime"]}/search/manga?q={name}/Zero&page=1&limit=1&genre={genre}',
            )
        ) is not None:
            if type(raw_manga) is dict:
                try:
                    anime = raw_manga["results"][0]
                except KeyError:
                    await ctx.respond("Anime was not found.")
                    return

                embed = hikari.Embed(
                    title=anime.get("title", UNDEFINED),
                    description=anime.get("synopsis", UNDEFINED),
                    url=anime.get("url", UNDEFINED),
                )

                embed.set_image(anime.get("image_url", None))
                meta_data = (
                    ("Chapters", anime.get("chapters", UNDEFINED)),
                    ("Volumes", anime.get("volumes", UNDEFINED)),
                    ("Type", anime.get("type", UNDEFINED)),
                    ("Score", anime.get("score", UNDEFINED)),
                    (
                        "Published at",
                        time.human_timedelta(
                            time.clean_date(anime.get("start_date", UNDEFINED))
                        ),
                    ),
                    (
                        "Ended at",
                        time.human_timedelta(
                            time.clean_date(anime.get("end_date", UNDEFINED))
                        ),
                    ),
                    ("Community members", anime.get("members", UNDEFINED)),
                    ("Being published", anime.get("publishing", UNDEFINED)),
                )
                for k, v in meta_data:
                    embed.add_field(name=k, value=v, inline=True)
                await ctx.respond(embed=embed)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The name of the definition.")
@tanjun.as_slash_command("def", "Returns a definition given a name.")
async def define(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.injected(type=net_.HTTPNet),
) -> None:
    async with net as cli:
        await ctx.defer()

        headers: dict[str, str] = {
            "x-rapidapi-key": config.RAPID_TOKEN,
            "x-rapidapi-host": "mashape-community-urban-dictionary.p.rapidapi.com",
        }

        try:
            resp = await cli.request(
                "GET", API["urban"], headers=headers, params={"term": name.lower()}
            )
        except Exception as exc:
            raise RuntimeError("Couldn't make the definition request") from exc

        try:
            defn = random.choice(resp["list"])  # type: ignore

        except IndexError:
            await ctx.respond(f"Couldn't find definition about `{name}`")
            return

        except hikari.NotFoundError:
            pass

        else:
            example: str = defn["example"]
            definition: str = defn["definition"]
            up_voted: int = defn["thumbs_up"]
            down_votes: int = defn["thumbs_down"]
            date: str = defn["written_on"]
            url: str = defn["permalink"]
            author: str = defn["author"]

        embed = (
            hikari.Embed(
                title=f"Definition for {name}",
                description=(definition.replace("]", "").replace("[", "")),
                colour=consts.COLOR["invis"],
                timestamp=fast_datetime(date),  # type: ignore[None]
            )
            .set_author(name=author, url=url)
            .add_field("Example", example.replace("]", "").replace("[", ""))
            .set_footer(text=f"\U0001f44d {up_voted} - \U0001f44e {down_votes}")
        )
        await ctx.respond(embed=embed)


@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("url", converters=str)
@tanjun.with_parser
@tanjun.as_message_command("net")
async def run_net(
    ctx: tabc.Context, url: str, net: net_.HTTPNet = tanjun.injected(type=net_.HTTPNet)
) -> None:
    """Make a GET http request to an api or else.

    !!! note
        The api must be application/json type.

    ### TODO: make this command with options for POST and GET methods maybe?

    Parameters
    ----------
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
