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
"""Constants used globally."""

from __future__ import annotations

__all__: list[str] = [
    "COLOR",
    "API",
    "GENRES",
    "iter",
    "randomize",
    "generate_component",
    "naive_datetime",
    "spawn",
]

import datetime
import random
import typing

import hikari
import tanjun
import yuyo

if typing.TYPE_CHECKING:
    import collections.abc as collections

    _T = typing.TypeVar("_T")

COLOR: typing.Final[
    collections.Mapping[typing.Literal["invis", "random"], hikari.Colourish]
] = {
    "invis": hikari.Colour(0x36393F),
    "random": hikari.Colour(random.randint(0, 0xFFFFFF)),
}
"""Colors."""

API: collections.Mapping[typing.Literal["anime", "urban", "git"], typing.Any] = {
    "anime": "https://api.jikan.moe/v3",
    "urban": "https://api.urbandictionary.com/v0/define",
    "git": {
        "user": "https://api.github.com/users",
        "repo": "https://api.github.com/search/repositories?q={}&page=0&per_page=11&sort=stars&order=desc",
    },
}
"""A dict that holds api endpoints."""

GENRES: dict[str, int] = {
    "Action": 1,
    "Advanture": 2,
    "Drama": 8,
    "Daemons": 6,
    "Ecchi": 9,  # :eyes:
    "Sci-Fi": 24,
    "Shounen": 27,
    "Harem": 35,  # :eyes:
    "Seinen": 42,
    "Saumrai": 21,
    "Games": 11,
    "Psycho": 40,
    "Superpowers": 37,
    "Vampire": 32,
}
"""Anime only genres."""


def naive_datetime(datetime_: datetime.datetime) -> datetime.datetime:
    return datetime_.astimezone(datetime.timezone.utc)


async def generate_component(
    ctx: tanjun.abc.SlashContext | tanjun.abc.MessageContext,
    iterable: (
        collections.Generator[tuple[hikari.UndefinedType, hikari.Embed], None, None]
        | collections.Iterator[tuple[hikari.UndefinedType, hikari.Embed]]
    ),
    component_client: yuyo.ComponentClient,
    timeout: datetime.timedelta | None = None,
) -> None:
    pages = yuyo.ComponentPaginator(
        iterable,
        authors=(ctx.author,),
        triggers=(
            yuyo.pagination.LEFT_DOUBLE_TRIANGLE,
            yuyo.pagination.LEFT_TRIANGLE,
            yuyo.pagination.STOP_SQUARE,
            yuyo.pagination.RIGHT_TRIANGLE,
            yuyo.pagination.RIGHT_DOUBLE_TRIANGLE,
        ),
        timeout=timeout or datetime.timedelta(seconds=90),
    )
    if next_ := await pages.get_next_entry():
        content, embed = next_
        msg = await ctx.respond(
            content=content, embed=embed, component=pages, ensure_result=True
        )
        component_client.set_executor(msg, pages)


def iter(map: collections.Mapping[str, typing.Any]) -> collections.Sequence[typing.Any]:
    return [k for k in map.keys()]


def randomize(seq: collections.Sequence[str] | None = None) -> str:
    if not seq or seq is None:
        return random.choice(list(GENRES.keys()))
    return random.choice(list(seq))


# Since this file is mostly imported everywhere its worth
# having this here.
async def spawn(*coros: collections.Awaitable[_T]) -> collections.Sequence[_T]:
    from hikari.internal import aio

    return await aio.all_of(*coros)
