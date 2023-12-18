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

"""Dataclass models which represents records fetched from database / APIs / etc."""

from __future__ import annotations

__all__ = ("Membership", "Tokens")

import typing

import attrs
import hikari

if typing.TYPE_CHECKING:
    import collections.abc as collections
    import datetime
    from typing import Self


class Tokens(typing.TypedDict):
    """A view of a bungie user tokens fetched from a redis hash."""

    access: str
    refresh: str
    expires: float
    date: datetime.datetime


@attrs.frozen(kw_only=True, weakref_slot=False)
class Membership:
    """A view of a fetched Destiny database record."""

    ctx_id: hikari.Snowflake
    membership_id: int
    name: str
    code: int
    membership_type: str

    @classmethod
    def as_membership(cls, response: collections.Mapping[str, typing.Any]) -> Self:
        return cls(
            ctx_id=hikari.Snowflake(response["ctx_id"]),
            membership_id=response["membership_id"],
            name=response["name"],
            code=response["code"],
            membership_type=response["membership_type"],
        )
