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

"""Database modeuls. These model are just the result of fetched data from the tables."""

from __future__ import annotations

__all__: tuple[str, ...] = (
    "Destiny",
    "Mutes",
    "Notes"
)

import typing
import dataclasses

import hikari

if typing.TYPE_CHECKING:
    import datetime
    import collections.abc as collections

@dataclasses.dataclass(slots=True)
class Destiny:
    ctx_id: hikari.Snowflake
    membership_id: int
    name: str
    code: int
    membership_type: str

    @classmethod
    def into(cls, response: collections.Mapping[str, typing.Any]) -> Destiny:
        return Destiny(
            ctx_id=hikari.Snowflake(response['ctx_id']),
            membership_id=response['membership_id'],
            name=response['name'],
            code=response['code'],
            membership_type=response['membership_type']
        )

@dataclasses.dataclass(slots=True)
class Mutes:
    member_id: hikari.Snowflake
    guild_id: hikari.Snowflake
    author_id: hikari.Snowflake
    muted_at: datetime.datetime
    why: str
    duration: int

    @classmethod
    def into(cls, response: collections.Mapping[str, typing.Any]) -> Mutes:
        return Mutes(
            member_id=hikari.Snowflake(response['member_id']),
            guild_id=hikari.Snowflake(response['guild_id']),
            author_id=hikari.Snowflake(response['author_id']),
            muted_at=response['muted_at'],
            why=response['why'],
            duration=response['duration']
        )

@dataclasses.dataclass(slots=True)
class Notes:
    id: int
    name: str
    content: str
    author_id: hikari.Snowflake
    guild_id: hikari.Snowflake
    created_at: datetime.datetime

    @classmethod
    def into(cls, response: collections.Mapping[str, typing.Any]) -> Notes:
        return Notes(
            id=response['id'],
            name=response['name'],
            content=response['content'],
            author_id=hikari.Snowflake(response['author_id']),
            guild_id=hikari.Snowflake(response['guild_id']),
            created_at=response['created_at']
        )
