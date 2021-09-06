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

"""Commands here are for the owner and mods not for actual moderation."""

from __future__ import annotations

__all__: list[str] = ["component"]


import sys

import asyncpg
import hikari
import tanjun
from tanjun import abc

from core.psql import pool as pool_
from core.utils import format

component = tanjun.Component(name="mod")


@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("query", converters=str)
@tanjun.with_parser
@tanjun.as_message_command("sql")
async def run_sql(
    ctx: abc.MessageContext,
    query: str,
    pool: pool_.PoolT = tanjun.injected(type=pool_.PoolT),
) -> None:
    """Run sql code to the database pool.

    Parameters:
        query : `str`
            The sql query. This also can be used with code blocks like this.
            ```sql
                SELECT * FROM public.tables
                    WHERE THIS LIKE THAT
                LIMIT 1
            ```
    """

    query = format.parse_code(code=query)
    result: None | list[asyncpg.Record] = None

    try:
        result = await pool.fetch(query)

        # SQL Code error
    except asyncpg.exceptions.PostgresSyntaxError:
        await ctx.respond(format.with_block(sys.exc_info()[1]))
        return

        # Tables doesn't exists.
    except asyncpg.exceptions.UndefinedTableError:
        await ctx.respond(format.with_block(sys.exc_info()[1]))
        return

    if result is None:
        await ctx.respond("Nothing found.")
        return

    await ctx.respond(format.with_block(result))


@component.with_command
@tanjun.with_guild_check
@tanjun.with_own_permission_check(
    hikari.Permissions.KICK_MEMBERS,
    error_message="Bot doesn't have permissions to kick members.",
)
@tanjun.with_greedy_argument("reason", converters=(str,), default=None)
@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("kick")
async def kick(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member,
    /,
    reason: hikari.UndefinedOr[str],
) -> None:
    """Kick someone out of the guild

    Parameters:
        member : `hikari.Member`
            The member you want to kick.
        reason : `hikari.UndefinedOr[str]`
            The reason to replace at the audit log.
            This can be left undefined.
    """
    if member is None:
        await ctx.respond("No member was provided.")
        return

    if ctx.cache:
        member = ctx.cache.get_member(ctx.guild_id, member.id)  # type:ignore
    else:
        try:
            member = await ctx.client.rest.fetch_member(
                ctx.guild_id, member.id  # type:ignore
            )
        except hikari.HTTPError:
            await ctx.respond("Couldn't find the member in cache nor rest.")
            return
    try:
        guild = ctx.get_guild() or await ctx.fetch_guild()
        await guild.kick(member.id, reason=reason)
    except hikari.ForbiddenError as exc:
        await ctx.respond(f"You lack the {exc.message} permissions to perform this.")
        return

    to_respond = [f"Member {member.username}#{member.discriminator} has been kicked"]
    if reason:
        to_respond.append(f" For {reason}.")
    await ctx.respond("".join(to_respond))


@component.with_command
@tanjun.with_guild_check
@tanjun.with_own_permission_check(
    hikari.Permissions.KICK_MEMBERS,
    error_message="Bot doesn't have permissions to ban members.",
)
@tanjun.with_greedy_argument("reason", converters=(str,), default=None)
@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("ban")
async def ban(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member,
    /,
    reason: hikari.UndefinedOr[str],
) -> None:
    """Ban someone out of the guild

    Parameters:
        member : `hikari.Member`
            The member you want to kick.
        reason : `hikari.UndefinedOr[str]`
            The reason to replace at the audit log.
            This can be left undefined.
    """
    if member is None:
        await ctx.respond("No member was provided.")
        return

    if ctx.cache:
        member = ctx.cache.get_member(ctx.guild_id, member.id)  # type:ignore
    else:
        try:
            member = await ctx.client.rest.fetch_member(
                ctx.guild_id, member.id  # type:ignore
            )
        except hikari.HTTPError:
            await ctx.respond("Couldn't find the member in cache nor rest.")
            return
    try:
        guild = ctx.get_guild() or await ctx.fetch_guild()
        await guild.ban(member.id, reason=reason)
    except hikari.ForbiddenError as exc:
        await ctx.respond(f"You lack the {exc.message} permissions to perform this.")
        return

    to_respond = [f"Member {member.username}#{member.discriminator} has been banned"]
    if reason:
        to_respond.append(f" For {reason}.")
    await ctx.respond("".join(to_respond))


@tanjun.as_loader
def load_mod(client: tanjun.Client) -> None:
    client.add_component(component.copy())
