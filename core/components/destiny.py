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

"""Commands refrences aiobungie."""

from __future__ import annotations

__all__: tuple[str, ...] = ("destiny",)

import datetime
import typing

import aiobungie
import asyncpg
import hikari
import humanize
import tanjun
import yuyo
from hikari.internal import aio

from core.psql import pool
from core.utils import cache, consts, format

if typing.TYPE_CHECKING:
    import collections.abc as collections

destiny_group = tanjun.slash_command_group("destiny", "Commands related to Destiny 2.")

# Consts usually used as slash options key -> val.
_PLATFORMS: dict[str, aiobungie.MembershipType] = {
    "Steam": aiobungie.MembershipType.STEAM,
    "PSN": aiobungie.MembershipType.PSN,
    "Stadia": aiobungie.MembershipType.STADIA,
    "XBox": aiobungie.MembershipType.XBOX,
}

_CHARACTERS: dict[str, aiobungie.Class] = {
    "Warlock": aiobungie.Class.WARLOCK,
    "Hunter": aiobungie.Class.HUNTER,
    "Titan": aiobungie.Class.TITAN,
}

_ACTIVITIES: dict[str, tuple[str | None, aiobungie.FireteamActivity]] = {
    "Any": (None, aiobungie.FireteamActivity.ANY),
    "VoG": (
        "https://www.bungie.net/img/destiny_content/pgcr/vault_of_glass.jpg",
        aiobungie.FireteamActivity.RAID_VOG,
    ),
    "DSC": (
        "https://www.bungie.net/img/destiny_content/pgcr/europa-raid-deep-stone-crypt.jpg",
        aiobungie.FireteamActivity.RAID_DSC,
    ),
    "Nightfall": (
        "https://www.bungie.net/img/theme/destiny/bgs/stats/banner_strikes_1.jpg",
        aiobungie.FireteamActivity.NIGHTFALL,
    ),
    "Dungeon": (
        "https://www.bungie.net/common/destiny2_content/icons/082c3d5e7a44343114b5d056c3006e4b.png",
        aiobungie.FireteamActivity.DUNGEON,
    ),
    "Crucible": (None, aiobungie.FireteamActivity.CRUCIBLE),
    "Expunge": (
        "https://www.bungie.net/img/destiny_content/pgcr/season_14_expunge_tartarus.jpg",
        aiobungie.FireteamActivity.S14_EXPUNGE,
    ),
}

# Default timeout for paginators.
TIMEOUT: typing.Final[datetime.timedelta] = datetime.timedelta(seconds=90)

_slots: collections.Callable[[aiobungie.crate.Fireteam], str] = (
    lambda fireteam: "Full"
    if fireteam.available_player_slots == 0
    else f"{fireteam.available_player_slots}/{fireteam.player_slot_count}"
)


async def _get_destiny_player(
    client: aiobungie.Client,
    name: str,
    type: aiobungie.MembershipType = aiobungie.MembershipType.ALL,
) -> aiobungie.crate.DestinyUser:
    try:
        player = await client.fetch_player(name, type)
        assert player
        # The sequence always holds one player.
        # If they're not found means there's no player with the given name.
        return player[0]
    except IndexError:
        raise aiobungie.NotFound(
            f"Didn't find player named `{name}` with type `{type}`. "
            "Make sure you include the full name looks like this `Fate#123`"
        ) from None


def _build_inventory_item_embed(
    entity: aiobungie.crate.InventoryEntity,
) -> hikari.Embed:
    sets = f"https://data.destinysets.com/i/InventoryItem:{entity.hash}"

    item_tier = None
    try:
        item_tier = entity.tier
    except ValueError:
        pass

    embed = (
        hikari.Embed(
            title=entity.name,
            url=sets,
            colour=consts.COLOR["invis"],
            description=entity.description,
        )
        .add_field(
            "About",
            f"Hash: {entity.hash}\n"
            f"Index: {entity.index}\n"
            f"About: {entity.about}\n"
            f"Can equip: {entity.is_equippable}\n"
            f"Lore hash: {entity.lore_hash}",
        )
        .add_field(
            "Metadata",
            f"Type: {str(entity.type)} - Sub type: {str(entity.sub_type)}\n"
            f"Damage type: {entity.damage}\n"
            f"Ammo type: {entity.ammo_type or 'N/A'}\n"
            f"Class type: {entity.item_class or 'N/A'}\n"
            f"Tier: {item_tier} - Tier name: {entity.tier_name}",
        )
    )
    if entity.has_icon:
        embed.set_thumbnail(str(entity.icon))

    # This is a bug in aiobungie o:
    if entity.banner and entity.banner.url != "https://www.bungie.netImage <UNDEFINED>":
        embed.set_image(entity.banner.url)
    return embed


async def _sync_player(
    ctx: tanjun.abc.SlashContext,
    client: aiobungie.Client,
    pool: pool.PoolT,
    /,
    *,
    name: str,
    type: str,
) -> None:
    try:
        player = await _get_destiny_player(client, name, _PLATFORMS[type])
    except aiobungie.NotFound as exc:
        await ctx.respond(exc)
        return

    try:
        await pool.execute(
            "INSERT INTO destiny(ctx_id, bungie_id, name, code, memtype) VALUES($1, $2, $3, $4, $5)",
            ctx.author.id,
            player.id,
            player.name,
            player.code,
            int(player.type),
        )
    except asyncpg.exceptions.UniqueViolationError:
        await ctx.respond("You're already synced.")
        return

    await ctx.respond(
        f"Synced `{player.unique_name}` | `{player.id}`, `/destiny profile` to view your profile"
    )

@tanjun.as_message_command("d2_api")
async def check_api(ctx: tanjun.MessageContext, client: aiobungie.Client = tanjun.inject(type=aiobungie.Client)) -> None:
    try:
        resp = await client.rest.static_request("GET", "Settings")
    except Exception:
        raise
    if resp['systems']['Destiny2']['enabled']:
        status = "Destiny2 API is up."
    else:
        status = "Destiny2 API is down."
    await ctx.respond(status)

@destiny_group.with_command
@tanjun.with_str_slash_option(
    "name", "The unique bungie name. Looks like this `Fate#123`"
)
@tanjun.with_str_slash_option(
    "type", "The membership type.", choices=consts.iter(_PLATFORMS)
)
@tanjun.as_slash_command("sync", "Sync your destiny membership with this bot.")
async def sync(
    ctx: tanjun.abc.SlashContext,
    name: str,
    type: str,
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
) -> None:
    await _sync_player(ctx, client, pool, name=name, type=type)


@destiny_group.with_command
@tanjun.as_slash_command("desync", "Desync your destiny membership with this bot.")
async def desync(
    ctx: tanjun.abc.SlashContext,
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
) -> None:
    if (
        member := await pool.fetchval(
            "SELECT ctx_id FROM destiny WHERE ctx_id = $1", ctx.author.id
        )
    ) is not None:
        print(member)
        try:
            await pool.execute("DELETE FROM destiny WHERE ctx_id = $1", member)
        except Exception as exc:
            raise RuntimeError(f"Couldn't desync member {repr(ctx.author)}") from exc
        await ctx.respond("Successfully desynced your membership.")
    else:
        await ctx.respond("You're not already synced.")
        return


@tanjun.with_cooldown("destiny")
@destiny_group.with_command
@tanjun.with_member_slash_option(
    "member", "An optional discord member to get their characters.", default=None
)
@tanjun.with_str_slash_option(
    "platform", "The membership type to return", choices=consts.iter(_PLATFORMS)
)
@tanjun.with_str_slash_option(
    "id_or_name", "An optional player id or full name to search for.", default=None
)
@tanjun.as_slash_command(
    "character", "Information about a member's Destiny characters."
)
async def characters(
    ctx: tanjun.abc.SlashContext,
    platform: str,
    member: hikari.InteractionMember | None,
    id_or_name: str | int | None,
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient),
) -> None:
    author = member or ctx.author
    if member and id_or_name:
        await ctx.respond("Can't specify a member and an id at the same time.")
        return

    if isinstance(id_or_name, str) and '#' in id_or_name:
        # We fetch the player by their name and get their id.
        player = await _get_destiny_player(client, id_or_name)
        id_or_name = player.id 

    id = id_or_name or await pool.fetchval(
        "SELECT bungie_id FROM destiny WHERE ctx_id = $1", author.id
    )

    try:
        char_resp = await client.fetch_profile(
            int(id), _PLATFORMS[platform], aiobungie.ComponentType.CHARACTERS
        )

    # TODO: include error messages in aiobungie.
    except aiobungie.ResponseError as exc:
        info: dict[str, str] = exc.args[1]
        await ctx.respond(
            "Invalid platform selected. Check the player's actual platform they're on.",
            embed=hikari.Embed(description=f"{info['Message']} : {info['MessageData']}")
        )
        return

    if char_mapper := char_resp.characters:
        iterator = tuple(c for c in char_mapper.values())
        pages = iter(
            (
                (
                    hikari.UNDEFINED,
                    hikari.Embed(
                        title=str(char.class_type), colour=consts.COLOR["invis"]
                    )
                    .set_image(char.emblem.url)
                    .set_thumbnail(char.emblem_icon.url)
                    .set_author(name=str(char.id), url=char.url)
                    .add_field(
                        "Information",
                        f"Power: {char.light}\n"
                        f"Class: {char.class_type}\n"
                        f"Gender: {char.gender}\n"
                        f"Race: {char.race}\n"
                        f"Played Time: {char.total_played_time}\n"
                        f"Last played: {char.last_played}\n"
                        f"Title hash: {char.title_hash if char.title_hash else 'N/A'}\n"
                        f"Member ID: {char.member_id}\nMember Type: {char.member_type}\n",
                    )
                    .add_field(
                        "Stats",
                        "\n".join(
                            [
                                f"{key}: {val} {'⭐' if val >= 90 and key.name != 'LIGHT_POWER' else ''}"
                                for key, val in char.stats.items()
                            ]
                        ),
                    ),
                    # We dont need char_id since its in the object itself.
                )
                for char in iterator
            )
        )
        paginator = yuyo.ComponentPaginator(
            pages,
            authors=(author,),
            triggers=(
                yuyo.pagination.LEFT_DOUBLE_TRIANGLE,
                yuyo.pagination.LEFT_TRIANGLE,
                yuyo.pagination.STOP_SQUARE,
                yuyo.pagination.RIGHT_TRIANGLE,
                yuyo.pagination.RIGHT_DOUBLE_TRIANGLE,
            ),
            timeout=TIMEOUT,
        )
        next_char = await paginator.get_next_entry()
        assert next_char
        content, embed = next_char
        msg = await ctx.respond(
            content=content, embed=embed, component=paginator, ensure_result=True
        )
        component_client.set_executor(msg, paginator)


@destiny_group.with_command
@tanjun.with_member_slash_option(
    "member", "An optional discord member to get their profile.", default=None
)
@tanjun.with_str_slash_option(
    "name", "An optional player name to search for.", default=None
)
@tanjun.as_slash_command("profile", "Information about a member's destiny membership.")
async def profiles(
    ctx: tanjun.abc.SlashContext,
    name: str | None,
    member: hikari.InteractionMember,
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
) -> None:

    member = member or ctx.member
    if (
        raw_stored_player := await pool.fetchrow(
            "SELECT * FROM destiny WHERE ctx_id = $1", member.id
        )
    ) is not None:
        stored_player: dict[str, typing.Any] = raw_stored_player  # type: ignore

        if name is not None:
            player_name = name
        else:
            player_name: str = f"{stored_player['name']}#{stored_player['code']}"

        try:
            player = await _get_destiny_player(
                client, player_name, aiobungie.MembershipType.ALL
            )
        except aiobungie.NotFound as exc:
            await ctx.respond(f"{exc}")
            return

        colour = consts.COLOR["invis"]
        if ctx.member and (role_colour := ctx.member.get_top_role()):
            colour = role_colour.colour
        embed = hikari.Embed(colour=colour)
        (
            embed.set_author(
                name=player.last_seen_name, icon=str(player.icon), url=player.link
            )
            .set_thumbnail(str(player.icon))
            .add_field(
                "About",
                f"ID: {player.id}\n"
                f"Full name: {player.unique_name}\n"
                f"Last seen name: {player.last_seen_name}\n"
                f"Code: {player.code}\n"
                f"Public profile: {player.is_public}\n"
                f"Types: {', '.join(str(t) for t in player.types)}",
            )
        )
        await ctx.respond(embed=embed)


@destiny_group.with_command
@tanjun.with_str_slash_option(
    "query", "The clan name or id.", converters=(str, int), default=4389205
)
@tanjun.as_slash_command("clan", "Searches for Destiny clans by their name.")
async def get_clan(
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
            clan = await client.fetch_clan(query)
    except aiobungie.NotFound as e:
        await ctx.respond(f"{e}")
        return None

    embed = hikari.Embed(description=f"{clan.about}", colour=consts.COLOR["invis"])
    (
        embed.set_author(name=clan.name, url=clan.url, icon=str(clan.avatar))
        .set_thumbnail(str(clan.avatar))
        .set_image(str(clan.banner))
        .add_field(
            "About",
            f"ID: `{clan.id}`\n"
            f"Total members: `{clan.member_count}`\n"
            f"About: {clan.motto}\n"
            f"Public: `{clan.is_public}`\n"
            f"Creation date: {humanize.precisedelta(clan.created_at, minimum_unit='hours')}\n"
            f"Type: {clan.type}",
            inline=False,
        )
        .add_field(
            "Features",
            f"Join Leve: `{clan.features.join_level}`\n"
            f"Capabilities: `{clan.features.capabilities}`\n"
            f"Memberships: {', '.join(str(c) for c in clan.features.membership_types)}",
        )
        .set_footer(", ".join(clan.tags))
    )

    if clan.owner:
        embed.add_field(
            f"Owner",
            f"Name: [{clan.owner.unique_name}]({clan.owner.link})\n"
            f"ID: `{clan.owner.id}`\n"
            f"Joined at: {humanize.precisedelta(clan.owner.joined_at, minimum_unit='hours')}\n"
            f"Type: `{str(clan.owner.type)}`\n"
            f"Last seen: {humanize.precisedelta(clan.owner.last_online, minimum_unit='minutes')}\n"
            f"Public profile: `{clan.owner.is_public}`\n"
            f"Membership types: {', '.join(str(t) for t in clan.owner.types)}",
        )
    await ctx.respond(embed=embed)


@destiny_group.with_command
@tanjun.with_int_slash_option("item_hash", "The item hash to get.")
@tanjun.as_slash_command("item", "Fetch a Bungie inventory item by its hash.")
async def item_definition_command(
    ctx: tanjun.SlashContext,
    item_hash: int,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    cache_: cache.Memory[int, hikari.Embed] = tanjun.inject(type=cache.Memory),
) -> None:
    if cached_item := cache_.get(item_hash):
        await ctx.respond(embed=cached_item)
        return

    try:
        entity = await client.fetch_inventory_item(item_hash)
    except Exception:
        await ctx.respond(embed=hikari.Embed(description=format.error(str=True)))

    embed = _build_inventory_item_embed(entity)
    cache_.put(item_hash, embed).set_expiry(datetime.timedelta(hours=8))
    await ctx.respond(embed=embed)


@tanjun.with_cooldown("destiny")
@destiny_group.with_command
@tanjun.with_member_slash_option(
    "member", "An optional discord member to get their characters.", default=None
)
@tanjun.with_str_slash_option(
    "platform", "The membership type to return", choices=consts.iter(_PLATFORMS)
)
@tanjun.with_str_slash_option(
    "id", "An optional player id to search for.", default=None
)
@tanjun.as_slash_command("equipment", "A view of a player's current equipped items.")
async def char_equipments(
    ctx: tanjun.SlashContext,
    member: hikari.InteractionMember | None,
    id: int | None,
    platform: str,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    pool: pool.PgxPool = tanjun.inject(type=pool.PoolT),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient),
) -> None:

    author = member or ctx.author
    if member and id:
        await ctx.respond("Can't specify a member and an id at the same time.")
        return

    id = id or await pool.fetchval(
        "SELECT bungie_id FROM destiny WHERE ctx_id = $1", author.id
    )
    if id:
        try:
            equips_resp = await client.fetch_profile(
                int(id),
                _PLATFORMS[platform],
                aiobungie.ComponentType.CHARACTER_EQUIPMENT,
            )
        except Exception as e:
            await ctx.respond(embed=hikari.Embed(description=format.with_block(e)))
            return

        if equipment := equips_resp.character_equipments:
            for _, equipment in equipment.items():
                tasks = await aio.all_of(*(i.fetch_self() for i in equipment))

            assert tasks
            pages = (
                (hikari.UNDEFINED, _build_inventory_item_embed(item)) for item in tasks
            )

            paginator = yuyo.ComponentPaginator(
                pages,
                authors=(author,),
                triggers=(
                    yuyo.pagination.LEFT_DOUBLE_TRIANGLE,
                    yuyo.pagination.LEFT_TRIANGLE,
                    yuyo.pagination.STOP_SQUARE,
                    yuyo.pagination.RIGHT_TRIANGLE,
                    yuyo.pagination.RIGHT_DOUBLE_TRIANGLE,
                ),
                timeout=TIMEOUT,
            )
            next_ = await paginator.get_next_entry()
            assert next_
            content, embed = next_
            msg = await ctx.respond(
                content=content, embed=embed, component=paginator, ensure_result=True
            )
            component_client.set_executor(msg, paginator)

@destiny_group.with_command
@tanjun.with_str_slash_option(
    "activity", "The activity to look for.", choices=consts.iter(_ACTIVITIES)
)
@tanjun.with_str_slash_option(
    "platform",
    "Specify a platform to filter the results.",
    default=aiobungie.FireteamPlatform.ANY,
    choices=consts.iter(_PLATFORMS),
)
@tanjun.as_slash_command("lfg", "Look for fireteams to play with at bungie.net LFGs")
async def lfg_command(
    ctx: tanjun.SlashContext,
    activity: str,
    platform: str,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient),
) -> None:

    # Different platforms from the normal ones.
    match platform:
        case "Steam":
            platform_ = aiobungie.FireteamPlatform.STEAM
        case "XBox":
            platform_ = aiobungie.FireteamPlatform.XBOX_LIVE
        case "Psn":
            platform_ = aiobungie.FireteamPlatform.PSN_NETWORK
        case _:
            platform_ = aiobungie.FireteamPlatform.ANY

    try:
        fireteams = await client.fetch_fireteams(
            _ACTIVITIES[activity][1], platform=platform_
        )
    except aiobungie.InternalServerError as exc:
        await ctx.respond(exc.long_message)
        return

    if not fireteams:
        await ctx.respond("No results found.")
        return

    pages = (
        (
            hikari.UNDEFINED,
            hikari.Embed(
                title=fireteam.title,
                url=fireteam.url,
                timestamp=fireteam.date_created.astimezone(datetime.timezone.utc),
            )
            .set_thumbnail(_ACTIVITIES[activity][0])
            .add_field(
                "Information",
                f"ID: {fireteam.id}\n"
                f"Platform: {fireteam.platform}\n"
                f"Activity: {fireteam.activity_type}\n"
                f"Available slots: {_slots(fireteam)}",
            ),
        )
        for fireteam in fireteams
    )
    paginator = yuyo.ComponentPaginator(
        pages,
        authors=(ctx.author,),
        triggers=(
            yuyo.pagination.LEFT_DOUBLE_TRIANGLE,
            yuyo.pagination.LEFT_TRIANGLE,
            yuyo.pagination.STOP_SQUARE,
            yuyo.pagination.RIGHT_TRIANGLE,
            yuyo.pagination.RIGHT_DOUBLE_TRIANGLE,
        ),
        timeout=TIMEOUT,
    )
    next_ = await paginator.get_next_entry()
    assert next_
    content, embed = next_
    msg = await ctx.respond(
        content, embed=embed, ensure_result=True, component=paginator
    )
    component_client.set_executor(msg, paginator)

destiny = tanjun.Component(name="Destiny/Bungie", strict=True).load_from_scope().make_loader()