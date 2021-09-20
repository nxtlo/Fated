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

__all__: list[str] = ["COLOR", "API", "GENRES", "iter", "randomize"]

import random
import typing

ChoiceT = typing.TypeVar("ChoiceT", covariant=True)
SequenceOf = str | typing.Sequence[ChoiceT] | None

# TODO: Make this a hikari.Colour ?
COLOR: typing.Final[dict[str, int]] = {
    "invis": 0x36393F,
    "random": random.randint(0, 0xFFFFFF),
}
"""Colors."""

API: dict[str, typing.Any] = {
    "anime": "https://api.jikan.moe/v3",
    "urban": "https://api.urbandictionary.com/v0/define",
    "git": {
        "user": "https://api.github.com/users",
        "repr": "https://api.github.com/users/nxtlo",
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

def iter(map: typing.Iterable[typing.Any] | None = None) -> typing.Iterable[str]:
    if map is None:
        map = GENRES
        return (genre for genre in map.keys())
    else:
        return (thing for thing in map)  # type:ignore


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
