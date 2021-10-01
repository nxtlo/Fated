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

import datetime
import time

import hikari
import humanize as hz
import tanjun
from tanjun import abc

from core.utils import cache, traits

component = tanjun.Component(name="meta")
prefix_group = component.with_slash_command(
    tanjun.SlashCommandGroup("prefix", "Handle the bot prefix configs.")
)


@component.with_message_command
@tanjun.as_message_command("ping")
async def ping(ctx: abc.MessageContext) -> None:
    """Pong."""
    start_time = time.perf_counter()
    await ctx.rest.fetch_my_user()
    time_taken = (time.perf_counter() - start_time) * 1_000
    heartbeat_latency = (
        ctx.shards.heartbeat_latency * 1_000 if ctx.shards else float("NAN")
    )
    await ctx.respond(
        f"PONG\n - REST: {time_taken:.0f}ms\n - Gateway: {heartbeat_latency:.0f}ms"
    )


@prefix_group.with_command
@tanjun.with_guild_check
@tanjun.with_author_permission_check(
    hikari.Permissions.MANAGE_GUILD,
    error_message="You need to be a guild manager to execute this command",
)
@tanjun.with_str_slash_option("prefix", "The prefix.", converters=(str,), default=None)
@tanjun.as_slash_command("set", "Change the bot prefix to a custom one.")
async def set_prefix(
    ctx: tanjun.abc.SlashContext,
    prefix: str | None,
    hash: traits.HashRunner[str, hikari.Snowflake, str] = cache.Hash(),
) -> None:

    if prefix is None:
        await ctx.respond("You must provide a prefix.")
        return None

    if len(prefix) > 5:
        await ctx.respond("Prefix length cannot be more than 5 letters.")
        return None

    await ctx.defer()
    try:
        guild_id = ctx.guild_id or (await ctx.fetch_guild()).id
        await hash.set("prefixes", guild_id, prefix)

    except Exception as err:
        await ctx.respond(f"Couldn't change bot prefix: {err}")
        return None

    await ctx.edit_initial_response(f"Prefix set to {prefix}")


@prefix_group.with_command
@tanjun.with_guild_check
@tanjun.with_author_permission_check(
    hikari.Permissions.MANAGE_GUILD,
    error_message="You need to be a guild manager to execute this command",
)
@tanjun.as_slash_command("clear", "Clear the bot prefix to a custom one.")
async def clear_prefix(
    ctx: tanjun.abc.SlashContext,
    hash: traits.HashRunner[str, hikari.Snowflake, str] = cache.Hash(),
) -> None:

    if ctx.cache:
        guild = ctx.get_guild()
    else:
        guild = await (ctx.fetch_guild())

    await ctx.defer()
    try:
        if (found_prefix := await hash.get("prefixes", guild.id)) is not None:
            await hash.delete("prefixes", guild.id)
        else:
            assert ctx.has_been_deferred
            return None

    except Exception as err:
        await ctx.respond(f"Couldn't clear the prefix: {err}")
        return

    await ctx.edit_initial_response(
        f"Cleared `{found_prefix}` prefix. You can still use the main prefix which's `?`"
    )


@component.with_message_command
@tanjun.as_message_command("invite")
async def invite(ctx: tanjun.abc.MessageContext) -> None:
    """Gets you an invite link for the bot."""
    me = ctx.cache.get_me() if ctx.cache else await ctx.rest.fetch_my_user()
    route = f"https://discord.com/api/oauth2/authorize?client_id={me.id}&permissions=0&scope=bot"
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
@tanjun.as_message_command("uptime")
async def uptime(ctx: tanjun.abc.MessageContext) -> None:
    await ctx.respond(
        f"Been up for {hz.naturaldelta(ctx.client.metadata['uptime'] - datetime.datetime.now())}"
    )


# idk if this even works.
@component.with_slash_command
@tanjun.as_slash_command("about", "Information about the bot itself.")
async def about_command(
    ctx: abc.SlashContext,
    hash: traits.HashRunner[str, hikari.Snowflake, str] = cache.Hash(),
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
        guild_prefix := await hash.get(
            "prefixes", ctx.guild_id or (await ctx.fetch_guild()).id
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
