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

__all__: tuple[str, ...] = ("meta",)

import datetime
import logging
import sys
import typing

import hikari
import tanjun

from core.utils import consts, traits

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.fated.component")
prefix_group = tanjun.slash_command_group("prefix", "Handle the bot prefix configs.")


async def on_ready(_: hikari.ShardReadyEvent) -> None:
    _LOGGER.info("Bot ready.")


@prefix_group.with_command
@tanjun.with_guild_check
@tanjun.with_author_permission_check(
    hikari.Permissions.MANAGE_GUILD,
    error_message="You need to be a guild manager to execute this command",
)
@tanjun.with_str_slash_option("prefix", "The prefix to set.")
@tanjun.as_slash_command("set", "Change the bot prefix to a custom one.")
async def set_prefix(
    ctx: tanjun.abc.SlashContext,
    prefix: str,
    hash: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
) -> None:

    if len(prefix) > 5:
        raise tanjun.CommandError("Prefix length cannot be more than 5 letters.")

    await ctx.defer()
    try:
        guild_id = ctx.guild_id or (await ctx.fetch_guild()).id
        await hash.set_prefix(guild_id, prefix)

    except Exception as err:
        raise tanjun.CommandError(f"Couldn't change bot prefix: {err!s}")

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
    hash: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
) -> None:

    if ctx.cache:
        guild = ctx.get_guild()
    else:
        guild = await ctx.fetch_guild()

    await ctx.defer()

    try:
        await hash.remove_prefix(guild.id)
    except Exception as err:
        raise tanjun.CommandError(f"Couldn't clear the prefix: {err!s}")

    await ctx.edit_initial_response(
        f"Cleared prefix. You can still use the main prefix which's `.`"
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


@tanjun.as_slash_command("about", "Information about the bot itself.")
async def about_command(
    ctx: tanjun.abc.SlashContext,
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
    create = f"**Creation date**: {tanjun.conversion.from_datetime(consts.naive_datetime(bot.created_at), style='R')}"
    uptime_ = f"**Uptime**: {ctx.client.metadata['uptime'] - datetime.datetime.now()}"

    embed.set_author(name=str(bot.id))

    embed.add_field(
        "Cache",
        f"**Members**: {len(cache.get_members_view())}\n"
        f"**Users**: {len(cache.get_users_view())}\n"
        f"**Available guilds**: {len(cache.get_available_guilds_view())}\n"
        f"**Guild Channels**: {len(cache.get_guild_channels_view())}\n"
        f"**Roles**: {len(cache.get_roles_view())}\n"
        f"**Emojis**: {len(cache.get_emojis_view())}\n"
        f"**Messages**: {len(cache.get_messages_view())}\n"
        f"**Voice states**: {len(cache.get_voice_states_view())}\n"
        f"**Presences**: {len(cache.get_presences_view())}\n"
        f"**Invites**: {len(cache.get_invites_view())}",
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
    ctx: tanjun.abc.SlashContext, member: hikari.InteractionMember | None
) -> None:

    assert ctx.guild_id is not None

    member = ctx.member or typing.cast(
        hikari.InteractionMember, await ctx.rest.fetch_member(ctx.guild_id, member.id)
    )
    embed = hikari.Embed(title=member.id)

    if member.avatar_url:
        embed.set_thumbnail(member.avatar_url)

    if member.banner_url:
        embed.set_image(member.banner_url)

    colour = member.accent_colour or consts.COLOR["invis"]
    embed.colour = colour

    info = [
        f'Nickname: {member.nickname or "N/A"}',
        f"Joined Discord at: {tanjun.conversion.from_datetime(member.created_at, style='R')}",
        f"Joined Guild at: {tanjun.conversion.from_datetime(member.joined_at, style='R')}",
        f"Is bot: {member.is_bot}\nIs system: {member.is_system}",
    ]
    embed.add_field("Information", "\n".join(info))

    roles = [
        f"{role.mention}: {role.id}"
        for role in member.get_roles()
        if not "everyone" in role.name
    ]
    embed.add_field("Roles", "\n".join(roles))

    perms = [f"`{perm.name}`" for perm in member.permissions if perm.name]

    if "ADMINISTRATOR" in perms:
        perms = ["ADMINISTRATOR"]

    embed.add_field("Permissions", ", ".join(perms))

    await ctx.respond(embed=embed)


@tanjun.with_user_slash_option("user", "The discord member.", default=None)
@tanjun.as_slash_command("user", "Gets you information about a discord user.")
async def user_view(ctx: tanjun.abc.SlashContext, user: hikari.User) -> None:

    user = ctx.author or await ctx.rest.fetch_user(user.id)
    embed = hikari.Embed(title=user.id)

    if user.avatar_url:
        embed.set_thumbnail(user.avatar_url)

    if user.banner_url:
        embed.set_image(user.banner_url)

    colour = user.accent_colour or consts.COLOR["invis"]
    embed.colour = colour

    info = [
        f"Joined Discord at: {tanjun.conversion.from_datetime(user.created_at, style='R')}",
        f"Is bot: {user.is_bot}\nIs system: {user.is_system}",
    ]
    embed.add_field("Information", "\n".join(info))

    await ctx.respond(embed=embed)


@tanjun.with_member_slash_option("member", "The discord member", default=None)
@tanjun.as_slash_command("avatar", "Returns the avatar of a discord member or yours.")
async def avatar_view(ctx: tanjun.abc.SlashContext, /, member: hikari.Member) -> None:
    """View of your discord avatar or other member."""
    member = member or ctx.author
    avatar = member.avatar_url or member.default_avatar_url
    embed = hikari.Embed(title=member.username).set_image(avatar)
    await ctx.respond(embed=embed)


meta = (
    tanjun.Component(name="Meta", strict=True)
    .add_listener(hikari.ShardReadyEvent, on_ready)
    .load_from_scope()
    .make_loader()
)
