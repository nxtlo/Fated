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

from __future__ import annotations

import math  # type: ignore[import]
import typing

import hikari

__all__: list[str] = ["component"]

import tanjun
from tanjun import abc as tabc

component = tanjun.Component()


class QuickMath:

    __slots__: typing.Sequence[str] = ("_left", "_op", "_right")

    ALLOWED: typing.Set[str] = {"+", "-", "*", "**", "/", ""}

    def __init__(self, left: int | float, op: str, right: int | float) -> None:
        self._left = left
        self._op = op
        self._right = right

    @property
    def left(self) -> int | float:
        return self._left

    @property
    def right(self) -> int | float:
        return self._right

    @property
    def op(self) -> str:
        """The operator."""
        return self._op

    def parse(self) -> int | float:
        # TODO: Implement this.
        ...


@component.with_command
@tanjun.as_message_command("ping")
async def ping(ctx: tabc.Context, /) -> None:
    """Pong."""
    await ctx.respond("Pong!.")


@component.with_command
@tanjun.as_message_command("about", "botinfo", "bot")
async def about_command(ctx: tabc.Context) -> None:
    """Info about the bot itself."""
    return None


@component.with_command(copy=True)
@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("avatar")
async def avatar_view(ctx: tabc.Context, /, member: hikari.Member) -> None:
    """View of your discord avatar or other member."""
    member = member or ctx.author
    avatar = member.avatar_url or member.default_avatar_url
    embed = hikari.Embed(title=member.username).set_image(avatar)
    await ctx.respond(embed=embed)


@component.with_command
@tanjun.with_greedy_argument("query", converters=(str,))
@tanjun.with_parser
@tanjun.as_message_command("say")
async def say_command(ctx: tabc.Context, query: str) -> None:
    await ctx.respond(query)


@tanjun.as_loader
def load_meta(client: tabc.Client) -> None:
    client.add_component(component.copy())
