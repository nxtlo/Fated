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
"""Consts and stuff that we don't modify."""

from __future__ import annotations

__all__: list[str] = ["COLOR", "API", "GENRES", "iter", "randomize", "generate_component"]

import random
import typing
import tanjun
import yuyo
import hikari


ChoiceT = typing.TypeVar("ChoiceT", covariant=True)

if typing.TYPE_CHECKING:
    import datetime
    import collections.abc as collections

    SequenceOf = str | typing.Sequence[ChoiceT] | None

COLOR: typing.Final[dict[str, hikari.Colourish]] = {
    "invis": hikari.Colour(0x36393F),
    "random": hikari.Colour(random.randint(0, 0xFFFFFF)),
}
"""Colors."""

API: dict[str, typing.Any] = {
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
    "Magic": 16,
    "Sci Fi": 24,
    "Shounen": 27,
    "Harem": 35,  # :eyes:
    "Seinen": 42,
}
"""Anime only genres."""

_K = typing.TypeVar("_K")

async def generate_component(
    ctx: tanjun.SlashContext,
    iterable: (
        collections.Generator[tuple[hikari.UndefinedType, hikari.Embed], None, None]
        | collections.Iterator[tuple[hikari.UndefinedType, hikari.Embed]]
    ),
    timeout: datetime.timedelta,
    component_client: yuyo.ComponentClient
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
            timeout=timeout,
        )
    if next_ := await pages.get_next_entry():
        content, embed = next_
        msg = await ctx.respond(content=content, embed=embed, component=pages, ensure_result=True)
        component_client.set_executor(msg, pages)

def iter(map: dict[_K, typing.Any]) -> typing.Sequence[str | _K | typing.Any]:
    return [k for k in map.keys()]


def randomize(seq: SequenceOf[typing.Any] | None = None) -> typing.Any:
    if seq is None:
        return random.choice(list(GENRES.keys()))
    return random.choice(list(seq))
