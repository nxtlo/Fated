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
import time
import aiobungie

import hikari
import tanjun
import alluka

from core.utils import boxed, traits

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("fated.meta")
prefix_group = (
    tanjun.slash_command_group("prefix", "Handle the bot prefix configs.")
    .add_check(tanjun.checks.GuildCheck())
    .add_check(
        tanjun.checks.AuthorPermissionCheck(
            hikari.Permissions.MANAGE_GUILD,
            error_message="Only guild managers can run this.",
        )
    )
)


async def on_ready(
    _: hikari.ShardReadyEvent, client: alluka.Injected[tanjun.Client]
) -> None:
    client.metadata["uptime"] = datetime.datetime.now()
    _LOGGER.info("Bot ready.")


@prefix_group.with_command
@tanjun.with_str_slash_option("prefix", "The prefix to set.")
@tanjun.as_slash_command("set", "Change the bot prefix to a custom one.")
async def set_prefix(
    ctx: tanjun.abc.SlashContext,
    prefix: str,
    hash: alluka.Injected[traits.HashRunner],
) -> None:

    assert ctx.guild_id
    if len(prefix) > 5:
        raise tanjun.CommandError("Prefix length cannot be more than 5 letters.")

    await ctx.defer()
    try:
        await hash.set_prefix(ctx.guild_id, prefix)

    except Exception as err:
        raise tanjun.CommandError(f"Couldn't change bot prefix: {err!s}")

    await ctx.edit_initial_response(f"Prefix set to {prefix}")


@prefix_group.with_command
@tanjun.as_slash_command("clear", "Clear the bot prefix to a custom one.")
async def clear_prefix(
    ctx: tanjun.abc.SlashContext,
    hash: alluka.Injected[traits.HashRunner],
) -> None:

    guild = ctx.get_guild() or await ctx.fetch_guild()
    await ctx.defer()

    try:
        await hash.remove_prefix(guild.id)
    except Exception as err:
        raise tanjun.CommandError(f"Couldn't clear the prefix: {err!s}")

    await ctx.edit_initial_response(
        f"Cleared prefix. You can still use the main prefix which's `.`"
    )


@tanjun.as_slash_command("about", "Information about the bot itself.")
async def about_command(
    ctx: tanjun.abc.SlashContext,
    bot_: alluka.Injected[hikari.GatewayBot],
) -> None:
    """Info about the bot itself."""

    from aiobungie import __version__ as aiobungie_version
    from hikari._about import __version__ as hikari_version
    from tanjun import __version__ as tanjun_version

    if ctx.cache:
        cache = ctx.cache

    bot = bot_.get_me() or await bot_.rest.fetch_my_user()

    embed = hikari.Embed(
        title=bot.username,
        description="Information about the bot",
        url="https://github.com/nxtlo/Fated",
    )

    create_date = tanjun.conversion.from_datetime(
        boxed.naive_datetime(bot.created_at), style="R"
    )
    metadata_uptime: datetime.datetime = ctx.client.metadata["uptime"]
    uptime = str(metadata_uptime - datetime.datetime.now())

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
        f"**Creation Date**: {create_date}\n" f"**Uptime**: {uptime[1:]}",
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

    colour = member.accent_colour or boxed.COLOR["invis"]
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


@tanjun.with_user_slash_option("user", "The discord user.", default=None)
@tanjun.as_slash_command("user", "Gets you information about a discord user.")
async def user_view(ctx: tanjun.abc.SlashContext, user: hikari.User | None) -> None:

    id_ = user.id if user is not None else ctx.author.id
    user = await ctx.rest.fetch_user(id_)
    embed = hikari.Embed(title=user.id)

    if user.avatar_url:
        embed.set_thumbnail(user.avatar_url)

    if user.banner_url:
        embed.set_image(user.banner_url)

    colour = user.accent_colour or boxed.COLOR["invis"]
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


@tanjun.as_message_command("ping")
async def ping_command(
    ctx: tanjun.abc.MessageContext,
    client: alluka.Injected[aiobungie.Client],
) -> None:

    aiobungie_start = time.perf_counter()
    _ = await client.rest.fetch_common_settings()
    aiobungie_stop = (time.perf_counter() - aiobungie_start) * 1_000

    rest_start = time.perf_counter()
    _ = await ctx.rest.fetch_my_user()
    rest_stop = (time.perf_counter() - rest_start) * 1_000

    gateway_time = ctx.shards.heartbeat_latency * 1_000 if ctx.shards else float("NAN")

    await ctx.respond(
        embed=(
            hikari.Embed(
                description=(
                    f"Bungie: {aiobungie_stop:.0f}ms\n"
                    f"Discord REST: {rest_stop:.0f}ms\n"
                    f"Discord Gateway: {gateway_time:.0f}ms"
                ).replace("_", "")
            )
        )
    )


meta = (
    tanjun.Component(name="Meta", strict=True)
    .add_listener(hikari.ShardReadyEvent, on_ready)
    .load_from_scope()
    .make_loader()
)
