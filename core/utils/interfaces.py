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
"""Interfaces for our api wrappers."""

from __future__ import annotations

__all__: tuple[str, ...] = ("APIAware", "GithubRepo", "GithubUser", "HashView")

import abc
import typing

import attr

if typing.TYPE_CHECKING:
    import collections.abc as collections
    import datetime

    import hikari
    import tanjun

_T = typing.TypeVar("_T")


@attr.mutable(weakref_slot=False, hash=False, repr=True)
class HashView(typing.Generic[_T]):
    key: _T = attr.field()
    value: _T = attr.field()


class APIAware(abc.ABC):
    """An abctract interface for our wrapper class."""

    __slots__ = ()

    @abc.abstractmethod
    async def fetch_anime(
        self,
        name: str | None = None,
        *,
        random: bool | None = None,
        genre: str,
    ) -> hikari.Embed | collections.Generator[hikari.Embed, None, None] | None:
        ...

    @abc.abstractmethod
    async def fetch_manga(
        self, name: str, /
    ) -> collections.Generator[hikari.Embed, None, None] | None:
        ...

    @abc.abstractmethod
    async def fetch_definitions(
        self, ctx: tanjun.SlashContext, name: str
    ) -> collections.Generator[hikari.Embed, None, None] | None:
        ...

    @abc.abstractmethod
    async def fetch_git_user(self, name: str) -> GithubUser | None:
        ...

    @abc.abstractmethod
    async def fetch_git_repo(
        self, name: str
    ) -> collections.Sequence[GithubRepo] | None:
        ...

    @abc.abstractmethod
    async def git_release(
        self, user: str, repo_name: str, limit: int | None
    ) -> collections.Generator[hikari.Embed, None, None]:
        ...


@attr.define(hash=False, weakref_slot=False, kw_only=True)
class GithubRepo:

    owner: GithubUser | None = attr.field(repr=True)

    id: int = attr.field()

    name: str = attr.field()

    description: str | None = attr.field()

    is_forked: bool = attr.field()

    url: str = attr.field()

    is_archived: bool = attr.field()

    forks: int = attr.field()

    open_issues: int = attr.field()

    # We only need the License name
    license: str | None = attr.field()

    size: int = attr.field()

    created_at: datetime.datetime = attr.field()

    last_push: str = attr.field()

    page: str | None = attr.field()

    stars: int = attr.field()

    language: str | hikari.UndefinedType = attr.field()


@attr.define(hash=False, weakref_slot=False, kw_only=True, repr=False)
class GithubUser:

    name: hikari.UndefinedOr[str] = attr.field(repr=True)

    id: int = attr.field(repr=True, hash=True)

    avatar_url: typing.Optional[str] = attr.field()

    url: str = attr.field()

    type: str = attr.field()

    email: typing.Optional[str] = attr.field()

    location: typing.Optional[str] | None = attr.field()

    public_repors: int | hikari.UndefinedType = attr.field()

    bio: hikari.UndefinedOr[str] | None = attr.field()

    followers: int | hikari.UndefinedType = attr.field()

    following: int | hikari.UndefinedType = attr.field()

    created_at: datetime.datetime | None = attr.field()

    repos_url: str = attr.field()
