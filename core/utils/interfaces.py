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

__all__: tuple[str, ...] = ("APIWrapper",)

import abc
import typing

import attr
import hikari
import tanjun


class APIWrapper(abc.ABC):
    """An abctract interface for our wrapper class."""

    __slots__: typing.Sequence[str] = ()

    @abc.abstractmethod
    async def get_anime(
        self,
        ctx: tanjun.abc.SlashContext,
        name: str | None = None,
        *,
        random: bool | None = None,
        genre: str,
    ) -> hikari.Embed | hikari.UndefinedType:
        """Fetch an anime from jikan api.

        Parameters
        ----------
        ctx : `tanjun.abc.SlashContext`
            The discord slash context.
        name : `str` | `None`
            The anime name. If kept to None, A random anime will be returned.
        genre : `str`
            The anime's genre. If kept to None. A random genre will be selected.

        Notes
        -----
        * If random was `True` and genre is `None`,
        A random anime with a random genre will be returned.

        * If random was `None` and the genre is selected.
        A random anime based on the selected genre will be returned.

        Returns
        -------
        hikari.Embed
            A hikari embed contains the anime data
            if the the request was succesfulanime was found.
        hikari.undefined.UndefinedType
            An undefined type if the anime was not found.
        """

    @abc.abstractmethod
    async def get_manga(
        self, ctx: tanjun.abc.SlashContext, name: str, /
    ) -> hikari.Embed | hikari.UndefinedType:
        """Fetch an manga from jikan api and returns the first one found.

        Parameters
        ----------
        ctx : `tanjun.abc.SlashContext`
            The discord's slash context.
        name : `str`
            The manga name.

        Returns
        -------
        hikari.Embed
            A hikari embed contains the manga data
            if the the request was successful manga was found.
        hikari.undefined.UndefinedType
            An undefined type if the manga was not found.
        """

    @abc.abstractmethod
    async def get_definition(
        self, ctx: tanjun.abc.SlashContext, name: str
    ) -> hikari.Embed | hikari.UndefinedType:
        """Get the definition by its name from urban dictionary.

        Parameters
        ----------
        ctx : `tanjun.abc.SlashContext`
            The discord's slash context.
        name : `str`
            The name of the definition.

        Returns
        -------
        hikari.Embed
            A hikari embed contains the definition data
            if the the request was successful definition was found.
        hikari.undefined.UndefinedType
            An undefined type if the definition was not found.
        """


# TODO: impl this for github component.


@attr.define(hash=False, weakref_slot=False, kw_only=True)
class GithubRepo:
    """Represents a repo on github."""

    owner: hikari.UndefinedOr[GithubUser] = attr.field(repr=True)
    """The repo's owner."""


@attr.define(hash=False, weakref_slot=False, kw_only=True)
class GithubUser:
    """Represents a user on github."""

    api: APIWrapper = attr.field(repr=False, eq=False)
    """Our api wrapper that will run and fetch the requests."""

    name: hikari.UndefinedOr[str] = attr.field(repr=True)
    """The github user's name."""

    id: int = attr.field(repr=True, hash=True)
    """The user's id."""

    avatar_url: hikari.UndefinedOr[str] = attr.field(repr=False)
    """The user's avatar url"""

    url: hikari.UndefinedOr[str] = attr.field(repr=False)
    """The user's github profile url."""

    type: str = attr.field(repr=True)
    """The user's type."""

    node_id: str = attr.field(repr=False)
    """The user's node id."""

    async def fetch_repos(self) -> typing.Sequence[GithubRepo]:
        # TODO: impl this.
        ...
