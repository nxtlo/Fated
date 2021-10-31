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

__all__: list[str] = ["COLOR", "API", "GENRES", "TTS", "iter", "randomize"]

import random
import typing

import hikari

ChoiceT = typing.TypeVar("ChoiceT", covariant=True)

if typing.TYPE_CHECKING:
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

TTS: dict[str, str] = {
    "Spongebob": 'TM:m2aw3j03asrt',
    "Mr.krabs": 'TM:p4m33qacqj5v',
    "Peter Griffin": 'TM:9wqc59heasx8',
    "The Weekend": 'TM:j9czhrg050ba',
    'Trump': 'TM:xy6gvtrrhz67',
    '50cent': 'TM:3cj7r4b4q9ks',
    "Shaggy": 'TM:vesbrtjvtvsa',
    'ScoopyDoo': 'TM:3fcxdr8nyvgm',
    "Dr.Phill": 'TM:p87rnz4t8kgg'
}

_K = typing.TypeVar("_K")

def iter(map: dict[_K, typing.Any]) -> typing.Sequence[str | _K | typing.Any]:
    return [k for k in map.keys()]


def randomize(seq: SequenceOf[typing.Any] | None = None) -> typing.Any:
    """Takes a sequence and randomize it.

    Parameters
    ----------
    seq : `SequenceOf[typing.Any]` | `None`
        A sequence of any elements.

    Returns
    -------
    `typing.Any`
        Any random element from the given sequence.
    """
    if seq is None:
        return random.choice(list(GENRES.keys()))
    return random.choice(list(seq))
