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

"""Commands related to destiny 2 and bungie's API"""

from __future__ import annotations

import typing

import aiobungie
import asyncpg
import hikari
import humanize
import tanjun

from core.psql import pool

component = tanjun.Component(name="destiny")

destiny_group: typing.Final[tanjun.abc.SlashCommandGroup] = component.with_slash_command(
    tanjun.SlashCommandGroup("destiny", "Commands related to Destiny 2.")
)

_PLATFORMS: tuple[str, ...] = (
    "Steam",
    "PSN",
    "Stadia",
    "XBox",
)

def _transform_type(
    type: str,
) -> aiobungie.MembershipType:

    convert: aiobungie.MembershipType
    match type:
        case "steam":
            convert = aiobungie.MembershipType.STEAM
        case "xbox":
            convert = aiobungie.MembershipType.XBOX
        case "psn":
            convert = aiobungie.MembershipType.PSN
        case "stadia":
            convert = aiobungie.MembershipType.STADIA
        case _:
            convert = aiobungie.MembershipType.ALL
    return convert

async def _get_destiny_player(
    client: aiobungie.Client,
    name: str,
    type: aiobungie.MembershipType = aiobungie.MembershipType.ALL
) -> aiobungie.crate.DestinyUser:
    try:
        player = await client.fetch_player(name, type)
        assert player is not None
        # The sequence always holds one player.
        # If they're not found means there's no player with the given name.
        return player[0]
    except IndexError:
        raise aiobungie.PlayerNotFound(
            f"Didn't find player named `{name}` with type `{type}`. "
            "Make sure you include the full name looks like this `Fate#123`"
        ) from None

async def sync_player(
    ctx: tanjun.abc.SlashContext, 
    client: aiobungie.Client,
    pool: pool.PoolT,
    /,
    *,
    name: str,
    type: str,
) -> None:
    try:
        player = await _get_destiny_player(client, name, _transform_type(type))
    except aiobungie.PlayerNotFound as exc:
        await ctx.respond(exc)
        return None

    try:
        await pool.execute(
            "INSERT INTO destiny(ctx_id, bungie_id, name, code, memtype) VALUES($1, $2, $3, $4, $5)",
            ctx.author.id, player.id, player.name, player.code, int(player.type)
        )
    except asyncpg.exceptions.UniqueViolationError:
        await ctx.respond("You're already synced.")
        return None

    await ctx.respond(f"Synced `{player.unique_name}` | `{player.id}`, `/destiny profile` to view your profile")

@destiny_group.with_command
@tanjun.as_slash_command("desync", "Desync your destiny membership with this bot.")
async def desync_command(
    ctx: tanjun.abc.SlashContext,
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
) -> None:
    if (member := await pool.fetchval("SELECT ctx_id FROM destiny WHERE ctx_id = $1", ctx.author.id)) is not None:
        print(member)
        try:
            await pool.execute("DELETE FROM destiny WHERE ctx_id = $1", member)
        except Exception as exc:
            raise RuntimeError(f"Couldn't desync member {repr(ctx.author)}") from exc
        await ctx.respond("Successfully desynced your membership.")
    else:
        await ctx.respond("You're not already synced.")
        return None

@destiny_group.with_command
@tanjun.with_member_slash_option("member", "An optional discord member to get their profile.", default=None)
@tanjun.with_str_slash_option("name", "An optional player name to search for.", default=None)
@tanjun.as_slash_command("profile", "Information about a member's destiny membership.")
async def profile_command(
    ctx: tanjun.abc.SlashContext,
    name: str | None,
    member: hikari.Member,
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT)
) -> None:

    member = member or ctx.author
    if (raw_stored_player := await pool.fetchrow("SELECT * FROM destiny WHERE ctx_id = $1", member.id)) is not None:
        stored_player: dict[str, typing.Any] = raw_stored_player # type: ignore

        if name is not None:
            player_name = name
        else:
            player_name: str = f"{stored_player['name']}#{stored_player['code']}"

        try:
            player = await _get_destiny_player(client, player_name, aiobungie.MembershipType.ALL)
        except aiobungie.PlayerNotFound as exc:
            await ctx.respond(f"{exc}")
            return None

        if ctx.cache is not None or ctx.guild_id is not None:
            member_colour = ctx.cache.get_member(ctx.get_guild().id, ctx.author).get_top_role().colour
        embed = hikari.Embed(colour=member_colour)
        (
            embed
            .set_author(name=player.last_seen_name, icon=str(player.icon), url=player.link)
            .set_thumbnail(str(player.icon))
            .add_field(
                "About",
                f"ID: {player.id}\n"
                f"Full name: {player.unique_name}\n"
                f"Last seen name: {player.last_seen_name}\n"
                f"Code: {player.code}\n"
                f"Public profile: {player.is_public}\n"
                f"Types: {', '.join(str(t) for t in player.types)}"
            )
        )
        await ctx.respond(embed=embed)

@destiny_group.with_command
@tanjun.with_str_slash_option("name", "The unique bungie name. Looks like this `Fate#123`")
@tanjun.with_str_slash_option("type", "The membership type.", choices=_PLATFORMS)
@tanjun.as_slash_command("sync", "Sync your destiny membership with this bot.")
async def sync_command(
    ctx: tanjun.abc.SlashContext,
    name: str,
    type: str,
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client)
) -> None:
    await sync_player(ctx, client, pool, name=name, type=type)

@destiny_group.with_command
@tanjun.with_str_slash_option(
    "query",
    "The clan name or id.",
    converters=(str, int),
    default=4389205
)
@tanjun.as_slash_command("clan", "Searches for Destiny clans by their name.")
async def get_clan_command(
    ctx: tanjun.abc.SlashContext,
    query: str | int,
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
) -> None:
    await ctx.defer()

    try:
        # Allow the command to search for both methods.
        if isinstance(query, int):
            clan = await client.fetch_clan_from_id(query)
        else:
            clan: aiobungie.crate.Clan = await client.fetch_clan(query)

    except aiobungie.ClanNotFound as e:
        await ctx.respond(f"{e}")
        return None

    embed = hikari.Embed(description=f'**{clan.about}**')
    (
        embed.set_author(name=clan.name, url=clan.url, icon=str(clan.avatar))
        .set_thumbnail(str(clan.avatar))
        .set_image(str(clan.banner))
        .add_field(
            "About",
            f"**ID**: `{clan.id}`\n"
            f"**Total members**: `{clan.member_count}`\n"
            f"**About**: {clan.motto}\n"
            f"**Public**: `{clan.is_public}`\n"
            f"**Creation date**: {humanize.precisedelta(clan.created_at, minimum_unit='hours')}\n"
            f"**Type**: {clan.type}",
            inline=False,
        )
        .add_field(
            "Features",
            f"**Join Leve**: `{clan.features.join_level}`\n"
            f"**Capabilities**: `{clan.features.capabilities}`\n"
            f"**Memberships**: {', '.join(str(c) for c in clan.features.membership_types)}",
        )
        .set_footer(", ".join(clan.tags))
    )

    if isinstance(clan.owner, aiobungie.crate.ClanMember):
        owner_name = (
            f'{clan.owner.last_seen_name}#{clan.owner.code if clan.owner.code else ""}'
        )
        embed.add_field(
            f"Owner",
            f"**Name**: [{owner_name}]({clan.owner.link})\n"
            f"**ID**: `{clan.owner.id}`\n"
            f"**Joined at**: {humanize.precisedelta(clan.owner.joined_at, minimum_unit='hours')}\n"
            f"**Type**: `{str(clan.owner.type)}`\n"
            f"**Last seen**: {humanize.precisedelta(clan.owner.last_online, minimum_unit='minutes')}\n"
            f"**Public profile**: `{clan.owner.is_public}`\n"
            f"**Membership types**: {', '.join(str(t) for t in clan.owner.types)}",
        )
    await ctx.respond(embed=embed)

@tanjun.as_loader
def load_destiny(client: tanjun.abc.Client):
    client.add_component(component.copy())

@tanjun.as_unloader
def unload_examples(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
