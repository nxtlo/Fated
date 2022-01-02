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

"""Interfaces/ABCs for multiple impls."""

from __future__ import annotations

__all__: tuple[str, ...] = ("APIAware", "GithubRepo", "GithubUser")

import abc
import typing
import dataclasses

if typing.TYPE_CHECKING:
    import collections.abc as collections
    import datetime

    import hikari
    import tanjun


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


@dataclasses.dataclass(kw_only=True, slots=True, repr=False)
class GithubRepo:
    owner: GithubUser | None = dataclasses.field(repr=True)
    id: int
    name: str
    description: str | None
    is_forked: bool
    url: str
    is_archived: bool
    forks: int
    open_issues: int
    # We only need the License name
    license: str | None
    size: int
    created_at: datetime.datetime
    last_push: str
    page: str | None
    stars: int
    language: str | hikari.UndefinedType

@dataclasses.dataclass(kw_only=True, repr=False, slots=True)
class GithubUser:
    name: hikari.UndefinedOr[str] = dataclasses.field(repr=True)
    id: int = dataclasses.field(repr=True, hash=True)
    avatar_url: typing.Optional[str]
    url: str
    type: str
    email: typing.Optional[str]
    location: typing.Optional[str] | None
    public_repors: int | hikari.UndefinedType
    bio: hikari.UndefinedOr[str] | None
    followers: int | hikari.UndefinedType
    following: int | hikari.UndefinedType
    created_at: datetime.datetime | None
    repos_url: str
