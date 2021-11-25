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

__all__: tuple[str, ...] = ("meta", "meta_loader")

import datetime
import logging
import os
import pathlib
import shutil
import subprocess as sp
import sys
import typing

import hikari
import humanize as hz
import psutil
import tanjun
import yuyo
from aiobungie.internal import time as time_

from core.utils import format, traits

prefix_group = tanjun.slash_command_group("prefix", "Handle the bot prefix configs.")


async def on_ready(_: hikari.ShardReadyEvent) -> None:
    logging.info("Bot ready.")


def _clean_up(path: pathlib.Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    return None


def iter_commands(ctx: tanjun.MessageContext) -> list[dict[tanjun.abc.Component, str]]:
    commands: list[dict[tanjun.abc.Component, str]] = []
    for command in ctx.client.iter_message_commands():
        assert command.component is not None
        commands += {
            c: "|".join(command.names)
            for c in ctx.client.components
            if command.component.name == c.name
        }
    return commands

# TODO: Fix this.
@tanjun.with_greedy_argument("command_name", converters=str, default=None)
@tanjun.with_parser
@tanjun.as_message_command("help")
async def help(ctx: tanjun.MessageContext, command_name: str | None) -> None:
    embed = hikari.Embed()
    if command_name is None:
        for commands in iter_commands(ctx):
            for commands_ in [(k, v) for k, v in commands.items()]:
                component, command = commands_
            embed.add_field(
                component.name,
                f"{component.metadata['about']}\n" f"**Commands**: {command}\n",
                inline=True,
            )
        await ctx.respond(embed=embed)
        return

    else:
        for command in ctx.client.iter_commands():
            if isinstance(command, tanjun.MessageCommand):
                name = command.names
            else:
                name = typing.cast(tanjun.SlashCommand, command).name
            if name == command_name:
                embed.title = f"{command.component.name} | {name}"
                embed.description = command.metadata.get("about", hikari.UNDEFINED)
        try:
            await ctx.respond(embed=embed)
            return
        # Content is empty.
        except hikari.BadRequestError:
            await ctx.respond(f"Command name {command_name} not found.")
            return

@tanjun.with_owner_check
@tanjun.with_str_slash_option("url", "The song name or url.")
@tanjun.with_str_slash_option("output", "The audio output format", default="mp3", choices=("mp3, m4a", "wav"))
@tanjun.as_slash_command("spotify", "Downloads a song from spotify given a name or url.")
async def download_spotify_song(
    ctx: tanjun.abc.SlashContext, url: str, output: str
) -> None:
    """Downloads a song from spotify giving a link or name."""
    if query is not None:
        path = pathlib.Path("__cache__")

        if path.exists():
            _clean_up(path)
        else:
            os.mkdir("__cache__")

            ok = await ctx.respond("Downloading...")
            with sp.Popen(
                [
                    "spotdl",
                    query,
                    "--output",
                    "__cache__",
                    "--output-format",
                    output_format,
                ],
                shell=False,
                stderr=sp.PIPE,
                stdin=sp.PIPE,
            ) as sh:
                _, nil = sh.communicate()
                if nil:
                    await ctx.respond(
                        f"Couldn't download the requested song: {format.with_block(nil.decode('utf-8'), lang='sh')}"
                    )
                    return None

        backoff = yuyo.backoff.Backoff(max_retries=3)
        async for _ in backoff:
            try:
                for file in path.iterdir():
                    if (
                        file.is_file()
                        and file.name.endswith((".wav", ".m4a", ".mp3"))
                        and not file.name == ".spotdl-cache"
                    ):
                        try:
                            assert ok is not None
                            await ok.respond(attachment=file)
                            _clean_up(path)
                            sh.terminate()
                            return
                        except Exception:
                            await ctx.respond(format.with_block(sys.exc_info()[1]))
                            return
            except FileNotFoundError:
                await ctx.respond("Encountered an error, Trying again.")
                continue
            except Exception as exc:
                raise RuntimeError(
                    f"Error while downloading a song in {ctx.guild_id}"
                ) from exc


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
    hash: traits.HashRunner[str, hikari.Snowflake, str] = tanjun.inject(
        type=traits.HashRunner
    ),
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
    hash: traits.HashRunner[str, hikari.Snowflake, str] = tanjun.inject(
        type=traits.HashRunner
    ),
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


@tanjun.with_str_slash_option("color", "The color hex code.")
@tanjun.as_slash_command("colour", "Returns a view of a color by its hex.")
async def color_fn(ctx: tanjun.abc.MessageContext, color: int) -> None:
    embed = hikari.Embed()
    embed.set_author(name=ctx.author.username)
    image = f"https://some-random-api.ml/canvas/colorviewer?hex={color}"
    embed.set_image(image)
    embed.title = f"0x{color}"
    await ctx.respond(embed=embed)


@tanjun.as_message_command("uptime")
async def uptime(ctx: tanjun.abc.MessageContext) -> None:
    await ctx.respond(
        f"Been up for {hz.precisedelta(ctx.client.metadata['uptime'] - datetime.datetime.now(), minimum_unit='MINUTES')}"
    )


@tanjun.as_slash_command("about", "Information about the bot itself.")
async def about_command(
    ctx: tanjun.SlashContext,
) -> None:
    """Info about the bot itself."""

    from aiobungie import __version__ as aiobungie_version
    from hikari._about import __version__ as hikari_version
    from tanjun import __version__ as tanjun_version

    procs = psutil.Process()
    mem_usage = (procs.memory_full_info().uss / 1024) ** 2
    cpu_usage = procs.cpu_percent() / psutil.cpu_count()

    if ctx.cache:
        cache = ctx.cache
        bot = cache.get_me()

    embed = hikari.Embed(
        title=bot.username,
        description="Information about the bot",
        url="https://github.com/nxtlo/Fated",
    )
    create = f"**Creation date**: {hz.precisedelta(time_.clean_date(str(bot.created_at)[:-6]), minimum_unit='MINUTES')}"
    uptime_ = f"**Uptime**: {hz.precisedelta(ctx.client.metadata['uptime'] - datetime.datetime.now(), minimum_unit='MINUTES')}"

    embed.set_author(name=str(bot.id))

    embed.add_field(
        "Cache",
        f"**Members**: {len(cache.get_members_view())}\n"
        f"**Available guilds**: {len(cache.get_available_guilds_view())}\n"
        f"**Channels**: {len(cache.get_guild_channels_view())}\n"
        f"**Emojis**: {len(cache.get_emojis_view())}\n"
        f"**Roles**: {len(cache.get_roles_view())}\n"
        f"**Messages**: {len(cache.get_messages_view())}",
        inline=False,
    )
    embed.add_field(
        "Meta",
        f"{create}\n{uptime_}\n"
        f"**Memory usage**: {mem_usage:.2f}MIB\n"
        f"**CPU usage**: {cpu_usage:.2f}%",
        inline=False,
    )
    if bot.avatar_url:
        embed.set_thumbnail(bot.avatar_url)

    embed.add_field(
        "Versions",
        f"**Hikari**: {hikari_version}\n"
        f"**Tanjun**: {tanjun_version}\n"
        f"**Aiobungie**: {aiobungie_version}\n"
        f"**Python**: {sys.version}",
        inline=False,
    )
    await ctx.respond(embed=embed)


@tanjun.with_member_slash_option("member", "The discord member", default=None)
@tanjun.as_slash_command("avatar", "Returns the avatar of a discord member or yours.")
async def avatar_view(ctx: tanjun.SlashContext, /, member: hikari.Member) -> None:
    """View of your discord avatar or other member."""
    member = member or ctx.author
    avatar = member.avatar_url or member.default_avatar_url
    embed = hikari.Embed(title=member.username).set_image(avatar)
    await ctx.respond(embed=embed)


async def on_message_create(
    event: hikari.GuildMessageCreateEvent,
) -> None:
    if event.is_bot or not event.is_human or event.message.content is None:
        return


meta = (
    tanjun.Component(name="Meta", strict=True)
    .add_listener(hikari.GuildMessageCreateEvent, on_message_create)
    .add_listener(hikari.ShardReadyEvent, on_ready)
).load_from_scope()
meta.metadata["about"] = "Component for misc and random commands."
meta_loader = meta.make_loader()
