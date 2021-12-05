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
import tanjun
import yuyo
from aiobungie.internal import time as time_

from core.utils import consts, format, traits

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.fated.component")
prefix_group = tanjun.slash_command_group("prefix", "Handle the bot prefix configs.")


async def on_ready(_: hikari.ShardReadyEvent) -> None:
    _LOGGER.info("Bot ready.")

def _clean_up(path: pathlib.Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    return None

@tanjun.with_owner_check
@tanjun.with_str_slash_option("url", "The song name or url.")
@tanjun.with_str_slash_option(
    "output", "The audio output format", default="mp3", choices=("mp3", "m4a", "wav")
)
@tanjun.as_slash_command(
    "spotify", "Downloads a song from spotify given a name or url."
)
async def download_spotify_song(
    ctx: tanjun.abc.SlashContext, url: str, output: str
) -> None:
    """Downloads a song from spotify giving a link or name."""
    if url is not None:
        path = pathlib.Path("__cache__")

        if path.exists():
            _clean_up(path)
        else:
            os.mkdir("__cache__")

            _ = await ctx.create_initial_response("Downloading...")
            with sp.Popen(
                [
                    "spotdl",
                    url,
                    "--output",
                    "__cache__",
                    "--output-format",
                    output,
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
                            await ctx.edit_initial_response(attachment=file)
                            sh.terminate()
                            return
                        except Exception:
                            await ctx.respond(format.error(str=True))
                            return
                        finally:
                            _clean_up(path)
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
async def colors(ctx: tanjun.abc.MessageContext, color: int) -> None:
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
        f"**Users**: {len(cache.get_users_view())}\n"
        f"**Available guilds**: {len(cache.get_available_guilds_view())}\n"
        f"**Channels**: {len(cache.get_guild_channels_view())}\n"
        f"**Emojis**: {len(cache.get_emojis_view())}\n"
        f"**Roles**: {len(cache.get_roles_view())}\n"
        f"**Messages**: {len(cache.get_messages_view())}",
        inline=False,
    )
    embed.add_field(
        "Bot",
        f"{create}\n{uptime_}\n",
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


@tanjun.with_member_slash_option("member", "The discord member.", default=None)
@tanjun.as_slash_command("member", "Gets you information about a discord member.")
async def member_view(
    ctx: tanjun.SlashContext, member: hikari.InteractionMember
) -> None:

    assert ctx.guild_id is not None
    try:
        guild = await ctx.rest.fetch_guild(ctx.guild_id)
    except Exception:
        _LOGGER.exception(f"Couldn't fetch guild for {ctx.guild_id}")
        guild = ctx.get_guild()
    assert guild is not None

    member = member or ctx.member
    assert member is not None
    embed = hikari.Embed(title=member.id)

    if member.avatar_url:
        embed.set_thumbnail(member.avatar_url)

    if member.banner_url:
        embed.set_image(member.banner_url)

    colour = member.accent_colour or consts.COLOR["invis"]
    embed.colour = colour

    info = [
        f'Nickname: {member.nickname or "N/A"}',
        f"Joined discord at: {tanjun.from_datetime(member.created_at, style='R')}",
        f"Joined guild at: {tanjun.from_datetime(member.joined_at, style='R')}",
        f"Is bot: {member.is_bot}\nIs system: {member.is_system}",
    ]
    embed.add_field("Information", "\n".join(info))

    roles = [
        f"{role.mention}: {role.id}"
        for role in member.get_roles()
        if not "everyone" in role.name
    ]
    embed.add_field("Roles", "\n".join(roles))

    await ctx.respond(embed=embed)

@tanjun.with_member_slash_option("member", "The discord member", default=None)
@tanjun.as_slash_command("avatar", "Returns the avatar of a discord member or yours.")
async def avatar_view(ctx: tanjun.SlashContext, /, member: hikari.Member) -> None:
    """View of your discord avatar or other member."""
    member = member or ctx.author
    avatar = member.avatar_url or member.default_avatar_url
    embed = hikari.Embed(title=member.username).set_image(avatar)
    await ctx.respond(embed=embed)

meta = (
    tanjun.Component(name="Meta", strict=True)
    .add_listener(hikari.ShardReadyEvent, on_ready)
).load_from_scope()
meta.metadata["about"] = "Component for misc and random commands."
meta_loader = meta.make_loader()
