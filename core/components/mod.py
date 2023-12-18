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

from __future__ import annotations

__all__ = ("mod",)

import datetime
import sys
import typing

import alluka
import hikari
import tanjun

from core.std import boxed, cache, traits

STDOUT: typing.Final[hikari.Snowflake] = hikari.Snowflake(789614938247266305)


@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("query", converters=str)
@tanjun.with_parser
@tanjun.as_message_command("sql")
async def run_sql(
    ctx: tanjun.abc.MessageContext,
    query: str,
    pool: alluka.Injected[traits.PoolRunner],
) -> None:
    """Run sql code to the database pool."""

    query = boxed.parse_code(code=query)

    try:
        result = await pool.partial.fetch(query)
        # SQL Code error
    except Exception:
        raise tanjun.CommandError(boxed.with_block(sys.exc_info()[1]))

    if not result:
        await ctx.respond("Nothing found.", delete_after=5)
        return

    await ctx.respond(boxed.with_block(result))


@tanjun.with_guild_check
@tanjun.with_own_permission_check(
    hikari.Permissions.KICK_MEMBERS,
    error_message="Bot doesn't have permissions to kick members.",
)
@tanjun.with_author_permission_check(hikari.Permissions.KICK_MEMBERS)
@tanjun.with_str_slash_option(
    "reason", "The reason to kick the member.", converters=(str,), default=None
)
@tanjun.with_member_slash_option("member", "The member to kick.")
@tanjun.as_slash_command("kick", "Kick someone out of the guild.")
async def kick(
    ctx: tanjun.abc.SlashContext,
    member: hikari.InteractionMember,
    reason: hikari.UndefinedOr[str],
) -> None:
    assert ctx.guild_id

    await ctx.defer()

    if ctx.cache is not None:
        guild = ctx.cache.get_guild(ctx.guild_id)

    else:
        guild = await ctx.rest.fetch_guild(ctx.guild_id)

    assert guild

    try:
        async with ctx.rest.trigger_typing(ctx.channel_id):
            await guild.kick(member.id, reason=reason)
    except hikari.InternalServerError:
        pass

    except hikari.HTTPError as exc:
        await ctx.create_followup(
            f"Couldn't kick member for {exc.message}, Trying again.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    to_respond = (
        f"Member {member.user.mention} has been kicked. {reason if reason else ''}"
    )
    await ctx.respond(to_respond)
    return


@tanjun.with_guild_check
@tanjun.with_own_permission_check(
    hikari.Permissions.BAN_MEMBERS,
    error_message="Bot doesn't have permissions to ban members.",
)
@tanjun.with_author_permission_check(hikari.Permissions.BAN_MEMBERS)
@tanjun.with_str_slash_option("reason", "An optional reason for the ban.")
@tanjun.with_member_slash_option("member", "The member to ban.")
@tanjun.as_slash_command("ban", "Ban someone from the guild.")
async def ban(
    ctx: tanjun.abc.SlashContext,
    member: hikari.InteractionMember,
    reason: hikari.UndefinedOr[str],
) -> None:
    assert ctx.guild_id

    await ctx.defer()
    if ctx.cache is not None:
        guild = ctx.cache.get_guild(ctx.guild_id)

    else:
        guild = await ctx.rest.fetch_guild(ctx.guild_id)

    assert guild is not None

    try:
        async with ctx.rest.trigger_typing(ctx.channel_id):
            await guild.ban(member.id, reason=reason)
    except hikari.HTTPError as exc:
        await ctx.create_followup(
            f"Couldn't banned member for {exc.message}, Try again.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    to_respond = (
        f"Member {member.user.mention} has been banned. {reason if reason else ''}"
    )
    await ctx.respond(to_respond)


@tanjun.with_owner_check
@tanjun.as_message_command("close", "shutdown")
async def close_bot(
    _: tanjun.abc.MessageContext,
    bot: alluka.Injected[hikari.GatewayBot],
) -> None:
    try:
        await bot.close()
    except Exception:
        raise


@tanjun.with_owner_check
@tanjun.as_message_command("guilds")
async def get_guilds(ctx: tanjun.abc.MessageContext) -> None:
    if ctx.cache is not None:
        guilds = ctx.cache.get_guilds_view()
    else:
        guilds = {
            guild.id: guild async for guild in ctx.rest.fetch_my_guilds().limit(70)
        }

    embed = hikari.Embed(
        description=boxed.with_block(
            "\n".join(f"{id}::{guild.name}" for id, guild in guilds.items()),
            lang="css",
        )
    )
    await ctx.respond(embed=embed)


# Originally, These commands are used to manage and test the cache
# not for actually caching stuff.
@tanjun.with_owner_check
@tanjun.as_message_command_group("cache")
async def cacher(
    ctx: tanjun.abc.MessageContext,
) -> None:
    # This will always not respond.
    assert not ctx.has_responded


@cacher.with_command
@tanjun.with_greedy_argument("value")
@tanjun.with_argument("key")
@tanjun.with_parser
@tanjun.as_message_command("put")
async def put(
    ctx: tanjun.abc.MessageContext,
    key: typing.Any,
    value: typing.Any,
    cache_: alluka.Injected[cache.Memory[typing.Any, typing.Any]],
) -> None:
    cache_.put(key, value)
    await ctx.respond(f"Cached {key} to {value}")


@cacher.with_command
@tanjun.with_greedy_argument("key")
@tanjun.with_parser
@tanjun.as_message_command("get")
async def get(
    ctx: tanjun.abc.MessageContext,
    key: typing.Any,
    cache_: alluka.Injected[cache.Memory[typing.Any, typing.Any]],
) -> None:
    await ctx.respond(cache_.get(key, "null"))


@cacher.with_command
@tanjun.with_greedy_argument("key")
@tanjun.with_parser
@tanjun.as_message_command("del")
async def remove(
    ctx: tanjun.abc.MessageContext,
    key: typing.Any,
    cache_: alluka.Injected[cache.Memory[typing.Any, typing.Any]],
) -> None:
    if key not in cache_:
        return

    del cache_[key]
    await ctx.respond("Ok")


@cacher.with_command
@tanjun.as_message_command("items")
async def cache_items(
    ctx: tanjun.abc.MessageContext,
    cache_: alluka.Injected[cache.Memory[typing.Any, typing.Any]],
) -> None:
    await ctx.respond(cache_.view())


@cacher.with_command
@tanjun.as_message_command("clear")
async def cache_clear(
    _: tanjun.abc.MessageContext,
    cache_: alluka.Injected[cache.Memory[typing.Any, typing.Any]],
) -> None:
    cache_.clear()


async def when_join_guilds(event: hikari.GuildJoinEvent) -> None:
    guild = await event.fetch_guild()
    guild_owner = await guild.fetch_owner()
    embed = hikari.Embed(
        title=f"{guild.name} | {guild.id}",
        description="Joined a guild.",
        timestamp=datetime.datetime.utcnow().astimezone(datetime.timezone.utc),
    )
    if guild.icon_url:
        embed.set_thumbnail(guild.icon_url)
    (
        embed.add_field("Member count", str(len(guild.get_members())))
        .add_field(
            "Created at", tanjun.conversion.from_datetime(guild.created_at, style="R")
        )
        .add_field("Owner", f"Name: {guild_owner.username}\n" f"ID: {guild_owner.id}")
    )
    await event.app.rest.create_message(STDOUT, embed=embed)


async def when_leave_guilds(event: hikari.GuildLeaveEvent) -> None:
    guild = event.old_guild
    if guild:
        embed = hikari.Embed(
            title=f"{guild.name} | {guild.id}",
            description="Left a guild.",
            timestamp=datetime.datetime.utcnow().astimezone(datetime.timezone.utc),
        ).add_field(
            "Created at", tanjun.conversion.from_datetime(guild.created_at, style="R")
        )
        await event.app.rest.create_message(STDOUT, embed=embed)
        return

    if event.guild_id == 796460453248368732:
        return

    await event.app.rest.create_message(
        STDOUT, f"Left from `UNDEFINED` guild {event.guild_id}"
    )


mod = (
    tanjun.Component(name="Moderation", strict=True)
    .add_listener(hikari.GuildJoinEvent, when_join_guilds)
    .add_listener(hikari.GuildLeaveEvent, when_leave_guilds)
    .load_from_scope()
    .make_loader()
)
