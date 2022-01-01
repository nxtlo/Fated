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

"""Commands references aiobungie."""

from __future__ import annotations

__all__: tuple[str, ...] = ("destiny",)

import asyncio
import datetime
import typing
import urllib.parse

import aiobungie
import asyncpg
import hikari
import humanize
import tanjun
import yuyo
from hikari.internal import aio

from core.psql import pool
from core.utils import cache, consts, format, traits

if typing.TYPE_CHECKING:
    import collections.abc as collections

destiny_group = tanjun.slash_command_group("destiny", "Commands related to Destiny 2.")

# Consts usually used as slash options key -> val.
_PLATFORMS: dict[str, aiobungie.MembershipType] = {
    "Steam": aiobungie.MembershipType.STEAM,
    "Psn": aiobungie.MembershipType.PSN,
    "Stadia": aiobungie.MembershipType.STADIA,
    "Xbox": aiobungie.MembershipType.XBOX,
}

# _CHARACTERS: dict[str, aiobungie.Class] = {
#     "Warlock": aiobungie.Class.WARLOCK,
#     "Hunter": aiobungie.Class.HUNTER,
#     "Titan": aiobungie.Class.TITAN,
# }

# Fireteam activities for quick LFGs
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
    "GoE": (
        "https://www.bungie.net/img/destiny_content/pgcr/30th-anniversary-grasp-of-avarice.jpg",
        aiobungie.FireteamActivity.DUNGEON_GOA
    ),
    "DoE": (
        "https://www.bungie.net/img/destiny_content/pgcr/30th-anniversary-dares-of-eternity.jpg",
        aiobungie.FireteamActivity.DOE
    )
}

D2_SETS: typing.Final[str] = "https://data.destinysets.com/i/InventoryItem:{hash}"
STAR: typing.Final[str] = '⭐'

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
    names = name.split("#")
    name_, code = names
    try:
        player = await client.fetch_player(name_, int(code), type)
        assert player
        # The sequence always holds one player.
        # If they're not found means there's no player with the given name.
        return player[0]
    except IndexError:
        raise LookupError(
            f"Player name `{name}` not found. "
            "Make sure you include the full name looks like this `Fate#123`"
        ) from None


def _build_inventory_item_embed(
    entity: aiobungie.crate.InventoryEntity,
) -> hikari.Embed:
    sets = D2_SETS.format(hash=entity.hash)

    embed = (
        hikari.Embed(
            title=entity.name,
            url=sets,
            colour=consts.COLOR["invis"],
            description=(
                entity.description
                if entity.description is not aiobungie.Undefined
                else entity.about
            ),
        )
        .add_field(
            "About",
            f"Hash: {entity.hash}\n"
            f"Index: {entity.index}\n"
            f"Lore hash: {entity.lore_hash}",
        )
        .add_field(
            "Metadata",
            f"Source: {entity.display_source}\n"
            f"Type: {entity.type_and_tier_name}\n"
            f"Class type: {entity.item_class or 'N/A'}"
        )
    )

    if entity.has_icon:
        embed.set_thumbnail(str(entity.icon))

    if entity.type is aiobungie.Item.EMBLEM:
        if entity.secondary_icon is not aiobungie.Undefined:
            embed.set_image(str(entity.secondary_icon))

    else:
        if entity.screenshot is not aiobungie.Undefined:
            embed.set_image(str(entity.screenshot))

    return embed

async def _sync_player(
    ctx: tanjun.abc.SlashContext,
    client: aiobungie.Client,
    pool: pool.PoolT,
    /,
    *,
    name: str,
) -> None:
    try:
        player = await _get_destiny_player(client, name)
    except LookupError as exc:
        await ctx.respond(exc)
        return

    try:
        await pool.execute(
            "INSERT INTO destiny(ctx_id, bungie_id, name, code, memtype) VALUES($1, $2, $3, $4, $5)",
            ctx.author.id,
            player.id,
            player.name,
            player.code,
            str(player.type).title(),
        )
    except asyncpg.exceptions.UniqueViolationError:
        await ctx.respond("You're already synced.")
        return

    await ctx.respond(
        f"Synced `{player.unique_name}` | `{player.id}`, `/destiny profile` to view your profile"
    )

@destiny_group.with_command
@tanjun.as_slash_command("authorize", "Authorize your bungie account with this bot.", default_to_ephemeral=True)
async def sync_command(
    ctx: tanjun.SlashContext,
    cache: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    bot: hikari.GatewayBot = tanjun.inject(type=hikari.GatewayBot)
) -> None:
    url = client.rest.build_oauth2_url()
    assert url

    await ctx.respond(
        embed=hikari.Embed(description=f"[Enter this link and send the URL after authorizing]({url})")
    )

    try:
        code = await bot.wait_for(
            hikari.GuildMessageCreateEvent,
            60,
            lambda m: m.channel_id == ctx.channel_id
            and m.author_id == ctx.author.id
            and m.content is not None
        )
    except asyncio.TimeoutError:
        pass

    else:
        if code.content:
            parse_code = urllib.parse.urlparse(code.content).query.removeprefix("code=")
            await code.message.delete()

            try:
                response = await client.rest.fetch_oauth2_tokens(parse_code)
            except aiobungie.BadRequest:
                await ctx.respond("Invalid URL. Please run the command again and send the URL.")
                return

            try:
                await cache.set_bungie_tokens(
                    ctx.author.id,
                    response
                )
            except Exception as exc:
                raise RuntimeError(f"Couldn't set tokens for user {ctx.author}") from exc
            await ctx.respond("\U0001f44d")

@destiny_group.with_command
@tanjun.as_slash_command("user", "Return authorized user information.")
async def user_command(
    ctx: tanjun.SlashContext,
    cache: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
) -> None:

    try:
        tokens = await cache.get_bungie_tokens(ctx.author.id)
    except LookupError:
        await ctx.respond("Youre not authorized. Type /destiny authorize to sync your account.")
        return

    access_token = str(tokens['access'])
    try:
        user = await client.fetch_own_bungie_user(access_token=access_token)
    except aiobungie.Unauthorized:
        raise

    bungie = user.bungie

    embed = hikari.Embed(
        title=f'{bungie.unique_name} - {bungie.id}', description=bungie.about
    )

    connections: list[str] = []
    if bungie.blizzard_name:
        connections.append(f"Blizzard name: {bungie.blizzard_name}")
    if bungie.steam_name:
        connections.append(f"Steam name: {bungie.steam_name}")
    if bungie.stadia_name:
        connections.append(f"Stadia name: {bungie.stadia_name}")
    if bungie.psn_name:
        connections.append(f"PSN name: {bungie.psn_name}")

    (
        embed
        .set_thumbnail(str(bungie.picture))
        .add_field(
            "Connections",
            "\n".join(connections)
        )
        .add_field(
            "Memberships",
            '\n'.join([f'[{m.type}: {m.unique_name}]({m.link})' for m in user.destiny])
        )
    )
    await ctx.respond(embed=embed)

@tanjun.as_message_command("d2_api")
async def check_api(
    ctx: tanjun.MessageContext,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client)
) -> None:
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
@tanjun.as_slash_command("sync", "Sync your destiny membership with this bot.")
async def sync(
    ctx: tanjun.abc.SlashContext,
    name: str,
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
) -> None:
    await _sync_player(ctx, client, pool, name=name)


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
    ):
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
    "id_or_name", "An optional player id or full name to search for.", default=None
)
@tanjun.as_slash_command(
    "character", "Information about a member's Destiny characters."
)
async def characters(
    ctx: tanjun.SlashContext,
    member: hikari.InteractionMember | None,
    id_or_name: str | int | None,
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
    pool: pool.PoolT = tanjun.injected(type=pool.PoolT),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient),
) -> None:

    member = member or ctx.member
    assert member, "This command should be ran in a Guild."

    if id_or_name:
        if isinstance(id_or_name, str) and '#' in id_or_name:
            # We fetch the player by their name and get their id.
            try:
                player = await _get_destiny_player(client, id_or_name)
            except LookupError as e:
                await ctx.respond(f'{e!s}')
                return
            id = player.id 
            platform = str(player.type).title()

    else:
        sql = typing.cast(dict[str, typing.Any] | None, await pool.fetchrow(
            "SELECT memtype, bungie_id FROM destiny WHERE ctx_id = $1", member.id
        )
    )
        if not sql:
            await ctx.respond(f"Member `{member.display_name}` is not found, Type /destiny sync to sync your account.")
            return

        id = sql['bungie_id']
        platform = sql['memtype']

    try:
        char_resp = await client.fetch_profile(
            int(id), _PLATFORMS[platform], aiobungie.ComponentType.CHARACTERS
        )

    except aiobungie.MembershipTypeError as exc:
        await ctx.respond(
            exc.message,
            embed=hikari.Embed(description=f'{exc!s}')
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
                                f"{key}: {val} {STAR if val >= 90 and key.name != 'LIGHT_POWER' else ''}"
                                for key, val in char.stats.items()
                            ]
                        ),
                    ),
                    # We dont need char_id since its in the object itself.
                )
                for char in iterator
            )
        )
        await consts.generate_component(ctx, pages, component_client)

@destiny_group.with_command
@tanjun.with_str_slash_option("name", "The player names to search for.")
@tanjun.as_slash_command("search_players", "Search for Destiny2 players.")
async def search_players(
    ctx: tanjun.SlashContext,
    name: str,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient)
) -> None:
    results = await client.search_users(name)
    if not results:
        await ctx.respond("No players found.")
        return
    
    iters = (
        (
            hikari.UNDEFINED,
            hikari.Embed(title=player.unique_name, url=player.link)
            .add_field(
                "Information",
                f"Membershiptype: {player.type}\n"
                f"ID: {player.id}\n"
                f"Crossave-override: {str(player.crossave_override).title()}"
            )
            .set_thumbnail(str(player.icon))
        )
        for player in results
    )
    await consts.generate_component(ctx, iters, component_client)

@destiny_group.with_command
@tanjun.with_str_slash_option("name", "The entity name to search for.")
@tanjun.with_str_slash_option("definition", "The definition of the entity. Default to inventory item", default=None)
@tanjun.as_slash_command("search_entity", "Search for Destiny 2 entity given its definition.")
async def search_entities(
    ctx: tanjun.SlashContext,
    name: str,
    definition: str | None,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient)
) -> None:
    results = await client.search_entities(name, definition or "DestinyInventoryItemDefinition")

    if not results:
        await ctx.respond("No items found.")
        return
    
    await ctx.defer()

    iters = (
        (
            hikari.UNDEFINED,
            hikari.Embed(title=entity.name, description=entity.description)
            .add_field(
                "Information",
                f"Hash: {entity.hash}\n"
                f"Type: {entity.entity_type}\n"
            )
            .set_thumbnail(str(entity.icon) if entity.has_icon else None)
            .set_footer(text=", ".join(entity.suggested_words))
        )
        for entity in results
    )
    await consts.generate_component(ctx, iters, component_client)

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
    ):
        stored_player = typing.cast(dict[str, typing.Any], raw_stored_player)

        if name:
            player_name = name
        else:
            player_name: str = f"{stored_player['name']}#{stored_player['code']}"

        try:
            player = await _get_destiny_player(
                client, player_name
            )
        except LookupError as exc:
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
        return

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
    cache_.put(item_hash, embed)
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
            await consts.generate_component(ctx, pages, component_client)

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
    except aiobungie.HTTPError as exc:
        await ctx.respond(exc.message)
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
    await consts.generate_component(ctx, pages, component_client)

@destiny_group.with_command
@tanjun.with_int_slash_option("instance", "The instance id of the activity.")
@tanjun.as_slash_command("post", "Returns a post activity information given the activity's instance id.")
async def post_activity_command(
    ctx: tanjun.SlashContext,
    instance: int,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    cache: cache.Memory[int, hikari.Embed] = tanjun.inject(type=cache.Memory)
) -> None:

    if cached_instance := cache.get(instance):
        await ctx.respond(embed=cached_instance)
        return

    try:
        post = await client.fetch_post_activity(instance)
    except aiobungie.HTTPError as e:
        await ctx.respond(e.message)
        return

    if post.is_private:
        return

    features: list[str] = []

    if post.is_solo_flawless:
        features.append(f"Solo Flawless: {STAR}")

    elif post.is_flawless:
        features.append(f"Flawless: {STAR}")

    elif post.is_solo:
        features.append(f"Solo: {STAR}")


    players = '\n'.join(
        # We will need the last seen name to unsure nothing in UNDEFINED.
        [f"{player.character_class}: [{player.destiny_user.last_seen_name}#{player.destiny_user.code}]"
        f"({player.destiny_user.link}): {player.values.played_time}" for player in post.players]
    )

    embed = (
        hikari.Embed(title=post.mode)
        .add_field(
            "Information",
            f"Reference id: {post.refrence_id}\n"
            f"Membership: {post.membership_type}\n"
            f"Starting phase: {post.starting_phase}\n"
            f"Date: {format.friendly_date(post.occurred_at)}"
        )
        .add_field("Players", players)
        )

    if features:
        embed.add_field(
            "Features",
            '\n'.join(features)
        )

    cache.put(instance, embed)
    await ctx.respond(embed=embed)

destiny = tanjun.Component(name="Destiny/Bungie", strict=True).load_from_scope().make_loader()