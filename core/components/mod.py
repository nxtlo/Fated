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

import sys
import typing
import asyncpg
import hikari
import tanjun
import datetime
import inspect
import textwrap
import io
import contextlib
import traceback
import yuyo

from tanjun import abc

from core.psql import pool as pool_
from core.utils import format

component = tanjun.Component(name="mod")
stdout: typing.Literal[789614938247266305] = 789614938247266305

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
    print(query)
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
    member: hikari.InteractionMember,
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


@component.with_message_command
@tanjun.with_owner_check
@tanjun.as_message_command("close", "shutdown")
async def close_bot(
    _: tanjun.MessageContext,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None:
    try:
        await bot.close()
    except Exception:
        raise


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
    member: hikari.InteractionMember,
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

# This command perform rest calls to get an uptodate
# data instead of the cache.
@component.with_message_command
@tanjun.with_owner_check
@tanjun.with_argument("id", default=None, converters=(int,))
@tanjun.with_parser
@tanjun.as_message_command("guild")
async def get_guild(ctx: tanjun.MessageContext, id: hikari.Snowflakeish | int | None) -> None:

    id = id or ctx.guild_id if ctx.guild_id else 411804307302776833
    backoff = yuyo.Backoff(2)
    async for _ in backoff:
        try:
            guild = await ctx.rest.fetch_guild(hikari.Snowflake(id))
            guild_owner = await guild.fetch_owner()

        except hikari.ForbiddenError as exc:
            # not in guild most likely or missin access.
            await ctx.respond(exc.message + '.')
            return

        # Ratelimited... somehow.
        except hikari.RateLimitedError as exc:
            backoff.set_next_backoff(exc.retry_after)

        # 5xx, continue.
        except hikari.InternalServerError:
            pass

        # Other errors. break.
        else:
            embed = hikari.Embed(title=guild.name, description=guild.id)
            if guild.icon_url:
                embed.set_thumbnail(guild.icon_url)
            (
                embed
                .add_field("Information",
                f"Members: {len(guild.get_members())}\n"
                f"Created at: {guild.created_at}\n"
                )
                .add_field(
                    "Owner",
                    f"Name: {guild_owner.username}\n"
                    f"ID: {guild_owner.id}"
                )
            )
            await ctx.respond(embed=embed)
            return

@component.with_message_command
@tanjun.with_owner_check
@tanjun.as_message_command("guilds")
async def get_guilds(ctx: tanjun.MessageContext) -> None:
    guilds = ctx.cache.get_available_guilds_view()
    embed = hikari.Embed(
        description=format.with_block("\n".join(
            f'{id}::{guild.name}::{len(guild.get_members())}' for id, guild in guilds.items()
            ),
        lang="css"
        )
    )
    await ctx.respond(embed=embed)

@component.with_listener(hikari.GuildJoinEvent)
async def when_join_guilds(event: hikari.GuildJoinEvent) -> None:
    guild = await event.fetch_guild()
    guild_owner = await guild.fetch_owner()
    embed = hikari.Embed(
        title=f'{guild.name} | {guild.id}',
        description="Joined a guild.",
        timestamp=datetime.datetime.utcnow().astimezone(datetime.timezone.utc)
    )
    if guild.icon_url:
        embed.set_thumbnail(guild.icon_url)
    (
        embed
        .add_field("Member count", str(len(guild.get_members())))
        .add_field("Created at", str(guild.created_at))
        .add_field(
            "Owner",
            f"Name: {guild_owner.username}\n"
            f"ID: {guild_owner.id}"
        )
    )
    channel = typing.cast(hikari.TextableChannel, await event.app.rest.fetch_channel(stdout))
    await channel.send(embed=embed)

@component.with_listener(hikari.GuildLeaveEvent)
async def when_leave_guilds(event: hikari.GuildLeaveEvent) -> None:
    guild = event.old_guild
    channel = typing.cast(hikari.TextableChannel, await event.app.rest.fetch_channel(stdout))
    if guild:
        embed = hikari.Embed(
            title=f'{guild.name} | {guild.id}',
            description="Left a guild.",
            timestamp=datetime.datetime.utcnow().astimezone(datetime.timezone.utc))
        embed.add_field("Created at", str(guild.created_at))
        await channel.send(embed=embed)
        return
    await channel.send(f"Left from `UNDEFINED` guild {event.guild_id}")

# Typed and adopted from RoboDanny <3
@component.with_message_command
@tanjun.with_owner_check
@tanjun.with_greedy_argument("body", converters=(str,))
@tanjun.with_parser
@tanjun.as_message_command("eval")
async def eval_command(ctx: tanjun.MessageContext, body: str, bot: hikari.GatewayBot = tanjun.inject(type=hikari.GatewayBot)) -> None:
    """Evaluates python code"""
    env = {
        "ctx": ctx,
        "bot": bot,
        "channel": ctx.get_channel(),
        "author": ctx.author,
        "guild": ctx.get_guild(),
        "message": ctx.message,
        "source": inspect.getsource,
    }

    def cleanup_code(content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        return content.strip("` \n")

    env.update(globals())

    body = cleanup_code(body)
    stdout = io.StringIO()
    err = out = None

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    def paginate(text: str) -> list[str]:
        """Simple generator that paginates text."""
        last = 0
        pages: set[str] = set()
        for curr in range(0, len(text)):
            if curr % 1980 == 0:
                pages.add(text[last:curr])
                last = curr
                appd_index = curr
        if appd_index != len(text) - 1:
            pages.add(text[last:curr])
            print(pages)
        return list(filter(lambda a: a != "", pages))

    try:
        exec(to_compile, env)
    except Exception as e:
        err = await ctx.respond(f"```py\n{e.__class__.__name__}: {e}\n```")
        return await ctx.message.add_reaction("\u2049")

    func = env["func"]
    try:
        with contextlib.redirect_stdout(stdout):
            ret = await func()  # type: ignore
    except Exception as e:
        value = stdout.getvalue()
        err = await ctx.respond(f"```py\n{value}{traceback.format_exc()}\n```")
    else:
        value = stdout.getvalue()
        if ret is None:
            if value:
                try:

                    out = await ctx.respond(f"```py\n{value}\n```")
                except:
                    paginated_text = paginate(value)
                    for page in paginated_text:
                        if page == paginated_text[-1]:
                            out = await ctx.respond(f"```py\n{page}\n```")
                            break
                        await ctx.respond(f"```py\n{page}\n```")
        else:
            try:
                out = await ctx.respond(f"```py\n{value}{ret}\n```")
            except:
                paginated_text = paginate(f"{value}{ret}")
                for page in paginated_text:
                    if page == paginated_text[-1]:
                        out = await ctx.respond(f"```py\n{page}\n```")
                        break
                    await ctx.respond(f"```py\n{page}\n```")

    if out:
        await ctx.message.add_reaction("\u2705")  # tick
    elif err:
        await ctx.message.add_reaction("\u2049")  # x
    else:
        await ctx.message.add_reaction("\u2705")

@tanjun.as_loader
def load_mod(client: tanjun.Client) -> None:
    client.add_component(component.copy())


@tanjun.as_unloader
def unload_examples(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
