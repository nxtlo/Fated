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

from yuyo import backoff

__all__: tuple[str, ...] = ("mod",)

import datetime
import sys
import typing

import asyncpg
import hikari
import tanjun
import alluka
import yuyo

from core.utils import boxed, cache, traits

STDOUT: typing.Final[hikari.Snowflake] = hikari.Snowflake(789614938247266305)

@tanjun.with_owner_check
@tanjun.as_message_command("reload")
async def reload(ctx: tanjun.abc.MessageContext) -> None:
    await ctx.client.clear_application_commands()


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
    result: None | list[asyncpg.Record] = None

    try:
        result = await pool._fetch(query)  # type: ignore
        # SQL Code error
    except asyncpg.exceptions.PostgresSyntaxError:
        raise tanjun.CommandError(boxed.with_block(sys.exc_info()[1]))

        # Tables doesn't exists.
    except asyncpg.exceptions.UndefinedTableError:
        raise tanjun.CommandError(boxed.with_block(sys.exc_info()[1]))

    if result is None:
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
    guild = ctx.get_guild()

    # In case the guild wasn't cached for somereason.
    await ctx.defer()

    if guild is None:
        guild = await ctx.rest.fetch_guild(ctx.guild_id)

    backoff_ = backoff.Backoff(3)
    async for _ in backoff_:
        try:
            await guild.kick(member.id, reason=reason)
        except hikari.InternalServerError:
            pass

        except hikari.HTTPError as exc:
            await ctx.create_followup(
                f"Couldn't kick member for {exc.message}, Trying again.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            backoff_.set_next_backoff(2.0)

        else:
            to_respond = [f"Member {member.user.mention} has been kicked."]
            if reason:
                to_respond += f" For {reason}."
            await ctx.respond("".join(to_respond))
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
    guild = ctx.get_guild()

    # In case the guild wasn't cached for somereason.
    await ctx.defer()

    if guild is None:
        guild = await ctx.rest.fetch_guild(ctx.guild_id)

    backoff_ = backoff.Backoff(3)

    async for _ in backoff_:
        try:
            await guild.ban(member.id, reason=reason)
        except hikari.InternalServerError:
            pass

        except hikari.HTTPError as exc:
            await ctx.create_followup(
                f"Couldn't banned member for {exc.message}, Try again.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            backoff_.set_next_backoff(2.0)

        else:
            to_respond = [f"Member {member.user.mention} has been banned."]
            if reason:
                to_respond += f" For {reason}."
            await ctx.respond("".join(to_respond))
            return


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


# This command perform rest calls to get an up-to-date
# data instead of the cache.
@tanjun.with_owner_check
@tanjun.with_argument("id", default=None, converters=(hikari.Snowflake, int))
@tanjun.with_parser
@tanjun.as_message_command("guild")
async def fetch_guild(ctx: tanjun.abc.MessageContext, id: hikari.Snowflake) -> None:

    id = id or ctx.guild_id if ctx.guild_id else hikari.Snowflake(411804307302776833)
    backoff = yuyo.Backoff(2)
    async for _ in backoff:
        try:
            guild = await ctx.rest.fetch_guild(hikari.Snowflake(id))
            guild_owner = await guild.fetch_owner()

        except hikari.ForbiddenError as exc:
            # not in guild most likely or missin access.
            await ctx.respond(exc.message + ".")
            return

        # Ratelimited... somehow.
        except hikari.RateLimitedError as exc:
            backoff.set_next_backoff(exc.retry_after)

        # 5xx, continue.
        except hikari.InternalServerError:
            pass

        else:
            embed = hikari.Embed(title=guild.name, description=guild.id)
            if ctx.cache:
                guild_snowflakes = set(ctx.cache.get_available_guilds_view().keys())
                users_snowflakes = set(ctx.cache.get_users_view().keys())
            if guild.icon_url:
                embed.set_thumbnail(guild.icon_url)
            (
                embed.add_field(
                    "Information",
                    f"Members: {len(guild.get_members())}\n"
                    f"Created at: {tanjun.conversion.from_datetime(guild.created_at, style='R')}\n"
                    f"Cached: {guild.id in guild_snowflakes or False}",  # type: ignore
                ).add_field(
                    "Owner",
                    f"Name: {guild_owner.username}\n"
                    f"ID: {guild_owner.id}\n"
                    f"Cached: {ctx.author.id in users_snowflakes or False}",  # type: ignore
                )
            )
            await ctx.respond(embed=embed)
            return


@tanjun.with_owner_check
@tanjun.as_message_command("guilds")
async def get_guilds(ctx: tanjun.abc.MessageContext) -> None:
    guilds = ctx.cache.get_available_guilds_view()
    assert guilds is not None
    embed = hikari.Embed(
        description=boxed.with_block(
            "\n".join(
                f"{id}::{guild.name}::{len(guild.get_members())}"
                for id, guild in guilds.items()
            ),
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
    await ctx.respond(cache_.get(key, "NOT_FOUND"))


@cacher.with_command
@tanjun.with_greedy_argument("key")
@tanjun.with_parser
@tanjun.as_message_command("del")
async def remove(
    ctx: tanjun.abc.MessageContext,
    key: typing.Any,
    cache_: alluka.Injected[cache.Memory[typing.Any, typing.Any]],
) -> None:
    try:
        del cache_[key]
        await ctx.respond("Ok")
    except KeyError:
        raise tanjun.CommandError("Key not found in cache.")


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
