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

"""Commands that you can use for any meta stuff."""

from __future__ import annotations


__all__: list[str] = ["component"]

import math  # type: ignore[import]
import sys
import typing

import asyncpg
import hikari
import tanjun
from tanjun import abc

from core.psql.pool import PgxPool
from core.utils import net

component = tanjun.Component(name="meta_component")


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
async def ping(ctx: abc.Context, /) -> None:
    """Pong."""
    await ctx.respond("Pong!.")


@component.with_slash_command
@tanjun.with_guild_check
@tanjun.with_author_permission_check(
    hikari.Permissions.MANAGE_GUILD,
    error_message="You need to be a guild manager to execute this command",
)
@tanjun.with_str_slash_option(
    "prefix", "The prefix you want to set.", converters=str, default=None
)
@tanjun.as_slash_command("prefix", "Change the bot prefix to a custom one.")
async def set_prefix(
    ctx: tanjun.abc.Context,
    prefix: str | None,
    pool: PgxPool = tanjun.injected(type=asyncpg.Pool),
) -> None:

    if prefix is None:
        await ctx.respond("You must provide a prefix.")
        return

    if len(prefix) > 5:
        await ctx.respond("Prefix length cannot be more than 5")
        return

    try:
        await pool.execute(
            "INSERT INTO guilds(id, prefix) VALUES($1, $2)", ctx.guild_id, prefix
        )
        await ctx.respond(f"Prefix changed to {prefix}")
    except asyncpg.exceptions.PostgresError:
        await ctx.respond(f"Failed to set the prefix {sys.exc_info()[1]}")


@component.with_message_command
@tanjun.with_argument("color", greedy=True)
@tanjun.with_parser
@tanjun.as_message_command("colour", "Returns a view of a color by its hex.")
async def color_fn(
    ctx: tanjun.abc.Context,
    color: int,
) -> None:

    embed = hikari.Embed()
    embed.set_author(name=ctx.author.username)
    image = f"https://some-random-api.ml/canvas/colorviewer?hex={color}"
    embed.set_image(image)
    embed.title = f'0x{color}'
    await ctx.respond(embed=embed)


@component.with_command
@tanjun.as_message_command("about", "botinfo", "bot")
async def about_command(ctx: abc.Context) -> None:
    """Info about the bot itself."""
    return None


@component.with_command(copy=True)
@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("avatar")
async def avatar_view(ctx: abc.Context, /, member: hikari.Member) -> None:
    """View of your discord avatar or other member."""
    member = member or ctx.author
    avatar = member.avatar_url or member.default_avatar_url
    embed = hikari.Embed(title=member.username).set_image(avatar)
    await ctx.respond(embed=embed)


@component.with_command
@tanjun.with_greedy_argument("query", converters=(str,))
@tanjun.with_parser
@tanjun.as_message_command("say")
async def say_command(ctx: abc.Context, query: str) -> None:
    await ctx.respond(query)


@tanjun.as_loader
def load_meta(client: tanjun.Client) -> None:
    client.add_component(component.copy())
