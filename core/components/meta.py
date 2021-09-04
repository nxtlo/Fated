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
from functools import cache

__all__: list[str] = ["component"]

import sys

import asyncpg
import hikari
import tanjun

from aiobungie.internal import time
from tanjun import abc

from core.psql.pool import PgxPool
from core.utils import format

component = tanjun.Component(name="meta")


@component.with_command
@tanjun.as_message_command("ping")
async def ping(ctx: abc.MessageContext, /) -> None:
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
    ctx: tanjun.abc.SlashContext,
    prefix: str | None,
    pool: PgxPool = tanjun.injected(type=asyncpg.Pool),
) -> None:

    if prefix is None:
        await ctx.respond("You must provide a prefix.")
        return

    if len(prefix) > 5:
        await ctx.respond("Prefix length cannot be more than 5")
        return

    await ctx.defer()
    try:
        await pool.execute(
            "INSERT INTO guilds(id, prefix) VALUES($1, $2)", ctx.guild_id, prefix
        )
    except asyncpg.exceptions.UniqueViolationError:
        await pool.execute(
            "UPDATE guilds SET prefix = $1 WHERE id = $2", prefix, ctx.guild_id
        )
        await ctx.respond(f"Prefix updated to {prefix}")
        return
    except asyncpg.exceptions.PostgresError:
        await ctx.respond(
            f"Failed to set the prefix {format.with_block(sys.exc_info()[1])}"
        )

    await ctx.edit_initial_response(f"Prefix set to {prefix}")

@component.with_message_command
@tanjun.as_message_command("invite")
async def invite(ctx: tanjun.abc.MessageContext) -> None:
    """Gets you an invite link for the bot."""
    me = ctx.cache.get_me() if ctx.cache else await ctx.rest.fetch_my_user()
    route = f'https://discord.com/api/oauth2/authorize?client_id={me.id}&permissions=0&scope=bot'
    await ctx.respond(route)

@component.with_slash_command
@tanjun.with_str_slash_option("color", "The color hex code.")
@tanjun.as_slash_command("colour", "Returns a view of a color by its hex.")
async def color_fn(ctx: tanjun.abc.MessageContext, color: int) -> None:
    embed = hikari.Embed()
    embed.set_author(name=ctx.author.username)
    image = f"https://some-random-api.ml/canvas/colorviewer?hex={color}"
    embed.set_image(image)
    embed.title = f"0x{color}"
    await ctx.respond(embed=embed)


@component.with_message_command
@tanjun.as_message_command("uptime", "Shows how long the bot been up for.")
async def uptime(ctx: tanjun.abc.SlashContext) -> None:
    """Chack the uptime for the bot."""
    await ctx.respond(
        f"Benn up for: *{time.human_timedelta(ctx.client.metadata['uptime'], suffix=False)}*"
    )


@component.with_slash_command
@tanjun.as_slash_command("about", "Information about the bot itself.")
async def about_command(
    ctx: abc.SlashContext, pool: PgxPool = tanjun.injected(type=asyncpg.Pool)
) -> None:
    """Info about the bot itself."""

    if ctx.cache:
        bot = ctx.cache.get_me()
        cache = ctx.cache

    from hikari._about import __version__ as hikari_version
    from tanjun import __version__ as tanjun_version

    embed = hikari.Embed(
        title=bot.username,
        description="Information about the bot",
        url="https://github.com/nxtlo/Tsujigiri",
    )
    embed.set_footer(text=f"Hikari {hikari_version} - Tanjun {tanjun_version}")
    embed.set_author(name=str(bot.id))

    await ctx.defer()
    if (
        guild_prefix := await pool.fetchval(
            "SELECT prefix FROM guilds WHERE id = $1", ctx.guild_id
        ),
    ) is not None:
        embed.add_field("Guild prefix", guild_prefix)

    embed.add_field(
        "Cache",
        f"Members: {len(cache.get_members_view())}\n"
        f"Available guilds: {len(cache.get_available_guilds_view())}\n"
        f"Channels: {len(cache.get_guild_channels_view())}",
        inline=False,
    )

    if bot.avatar_url:
        embed.set_thumbnail(bot.avatar_url)

    await ctx.respond(embed=embed)


@component.with_slash_command(copy=True)
@tanjun.with_member_slash_option("member", "The discord member", default=None)
@tanjun.as_slash_command("avatar", "Returns the avatar of a discord member or yours.")
async def avatar_view(ctx: abc.SlashContext, /, member: hikari.Member) -> None:
    """View of your discord avatar or other member."""
    member = member or ctx.author
    avatar = member.avatar_url or member.default_avatar_url
    embed = hikari.Embed(title=member.username).set_image(avatar)
    await ctx.respond(embed=embed)


@component.with_command
@tanjun.with_greedy_argument("query", converters=(str,))
@tanjun.with_parser
@tanjun.as_message_command("say")
async def say_command(ctx: abc.MessageContext, query: str) -> None:
    await ctx.respond(query)


@tanjun.as_loader
def load_meta(client: tanjun.Client) -> None:
    client.add_component(component.copy())
