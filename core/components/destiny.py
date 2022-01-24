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

"""Commands references aiobungie and makes my life easier."""

from __future__ import annotations

__all__: tuple[str, ...] = ("destiny",)

import asyncio
import typing
import urllib.parse

import aiobungie
import hikari
import tanjun
import yuyo
from hikari.internal import aio

from core.psql import pool
from core.utils import cache, consts, traits

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

    if entity.type is aiobungie.ItemType.EMBLEM:
        if entity.secondary_icon is not aiobungie.Undefined:
            embed.set_image(str(entity.secondary_icon))

    else:
        if entity.screenshot is not aiobungie.Undefined:
            embed.set_image(str(entity.screenshot))

    return embed

@destiny_group.with_command
@tanjun.as_slash_command("sync", "Sync your Bungie account with this bot.", default_to_ephemeral=True)
async def sync_command(
    ctx: tanjun.abc.SlashContext,
    redis: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    bot: hikari.GatewayBot = tanjun.inject(type=hikari.GatewayBot),
    pool_: pool.PoolT = tanjun.inject(type=pool.PoolT),
) -> None:
    url = client.rest.build_oauth2_url()
    assert url

    await ctx.create_initial_response(
        embed=hikari.Embed(
            title="How to sync your account.",
            description=(
                f"1) Visit this link {url}\n"
                "2) Login with your Bungie account and accept to authorize.\n"
                "3) After accepting you'll get redirected to Bungie's website. "
                "Simply copy the website URL link and send it here."
            )
        )
    )

    try:
        code = await bot.wait_for(
            hikari.MessageCreateEvent,
            90,
            lambda m: m.channel_id == ctx.channel_id
            and m.author_id == ctx.author.id
            and m.content is not None and 'code=' in m.content
        )
    except asyncio.TimeoutError:
        raise tanjun.CommandError("Time is up! Try again.")

    else:
        if code.content:
            parse_code = urllib.parse.urlparse(code.content).query.removeprefix("code=")

            try:
                await code.message.delete()
            # In DMs most likely, pass.
            except hikari.ForbiddenError:
                pass

            try:
                response = await client.rest.fetch_oauth2_tokens(parse_code)
            except aiobungie.BadRequest:
                raise tanjun.CommandError("Invalid URL. Please run the command again and send the URL.")

            user = await client.fetch_current_user_memberships(response.access_token)

            try:
                membership = user.destiny[0]
            except IndexError:
                # They don't have a Destiny membership aperantly ¯\_(ツ)_/¯
                raise tanjun.CommandError("You don't have any Destiny 2 memberships!")

            if (primary_id_ := user.primary_membership_id) is not None:
                primary_id = primary_id_
            else:
                primary_id = membership.id

            await redis.set_bungie_tokens(
                ctx.author.id,
                response
            )

            try:
                await pool_.put_destiny_member(
                    ctx.author.id,
                    primary_id,
                    str(membership.name),
                    membership.code if membership.code else 0,
                    membership.type
                )
            except pool.ExistsError:
                # They already exists in the DB.
                pass

            await ctx.respond(
                embed=(hikari.Embed(
                    title=membership.unique_name,
                    description=f"Synced successfully.",
                    url=user.bungie.profile_url
                    ).set_thumbnail(str(user.bungie.picture))
                )
            )


@destiny_group.with_command
@tanjun.as_slash_command("desync", "Desync your destiny membership with this bot.")
async def desync(
    ctx: tanjun.abc.SlashContext,
    pool_: pool.PoolT = tanjun.inject(type=pool.PoolT),
    redis: traits.HashRunner = tanjun.inject(type=traits.HashRunner)
) -> None:

    # Redis will remove if the tokens exists and fallback if not
    await redis.remove_bungie_tokens(ctx.author.id)

    try:
        await pool_.remove_destiny_member(ctx.author.id)
    except pool.ExistsError:
        raise tanjun.CommandError(f"Member {ctx.author} is not synced.")

    await ctx.respond("Successfully desynced your membership.")

@destiny_group.with_command
@tanjun.as_slash_command("user", "Return authorized user information.")
async def user_command(
    ctx: tanjun.abc.SlashContext,
    redis: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
) -> None:

    try:
        tokens = await redis.get_bungie_tokens(ctx.author.id)
    except LookupError:
        raise tanjun.CommandError("Youre not authorized. Type `/destiny sync` to sync your account.")

    access_token = str(tokens['access'])
    try:
        user = await client.fetch_current_user_memberships(access_token)
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
        .set_footer(f'{consts.naive_datetime(user.bungie.created_at)}')
    )
    await ctx.respond(embed=embed)

@tanjun.with_cooldown("destiny")
@destiny_group.with_command
@tanjun.as_slash_command("friends", "View your Bungie friend list")
async def friend_list_command(
    ctx: tanjun.abc.SlashContext,
    redis: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
) -> None:

    try:
        tokens = await redis.get_bungie_tokens(ctx.author.id)
    except LookupError:
        raise tanjun.CommandError("Youre not authorized. Type `/destiny sync` to sync your account.")

    access = str(tokens['access'])
    try:
        friend_list = await client.fetch_friends(access)
    except aiobungie.HTTPError as e:
        raise tanjun.CommandError(e.message)

    check_status: collections.Callable[[aiobungie.Presence], str] = (
        lambda status: '<:online2:464520569975603200>'
        if status is aiobungie.Presence.ONLINE else '<:offline2:464520569929334784>'
    )
    build_friends: collections.Callable[[collections.Sequence[aiobungie.crate.Friend]], str] = (
        lambda friend_list_: 
            "\n".join(
                [
                    f"{check_status(friend.online_status)} `{friend.unique_name}`"
                    for friend in friend_list_[:15]
            ]
        )
    )
    filtered_length = list(filter(lambda f: f.online_status is aiobungie.Presence.ONLINE, friend_list))

    embed = hikari.Embed(title=f"({len(filtered_length)}/{len(friend_list)}) Online.")
    if friend_list:
        embed.add_field("Friends",build_friends(friend_list))

    requests = await client.fetch_friend_requests(access)
    if incoming := requests.incoming:
        embed.add_field(
            "Incoming requests",
            build_friends(incoming)
        )

    if outgoing := requests.outgoing:
        embed.add_field(
            "Sent requests",
            build_friends(outgoing)
        )
    await ctx.respond(embed=embed)

# I don't want to force authorizing so we also allow to search for players
# either with their name or id.
@tanjun.with_cooldown("destiny")
@destiny_group.with_command
@tanjun.with_member_slash_option(
    "member", "An optional discord member to get their characters.", default=None
)
@tanjun.with_str_slash_option(
    "query", "An optional player id or full name to search for.", default=None
)
@tanjun.as_slash_command(
    "character", "Information about a member's Destiny characters."
)
async def characters(
    ctx: tanjun.abc.SlashContext,
    member: hikari.InteractionMember | None,
    query: str | int | None,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    pool_: pool.PoolT = tanjun.inject(type=pool.PoolT),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient),
) -> None:

    member = member or ctx.member
    assert member, "This command should be ran in a Guild."

    if query:
        if isinstance(query, str) and '#' in query:
            # We fetch the player by their name and get their id.
            try:
                player = await _get_destiny_player(client, query)
            except LookupError as e:
                raise tanjun.CommandError(f'{e!s}')

            id = player.id 
            platform = str(player.type).title()

    else:
        try:
            membership = await pool_.fetch_destiny_member(member.id)
        except pool.ExistsError:
            raise tanjun.CommandError(
                f"Member `{member.user.username}` is not synced yet. If that was you type `/destiny sync` first."
            )
        id = membership.membership_id
        platform = membership.membership_type

    try:
        char_resp = await client.fetch_profile(
            id, _PLATFORMS[platform], aiobungie.ComponentType.CHARACTERS
        )

    except aiobungie.MembershipTypeError as exc:
        raise tanjun.CommandError(f'{exc!s}')

    if characters := char_resp.characters:
        pages = iter(
            (
                (
                    hikari.UNDEFINED,
                    hikari.Embed(
                        title=str(char.class_type),
                        colour=consts.COLOR["invis"]
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
                        f"Last played: {tanjun.conversion.from_datetime(consts.naive_datetime(char.last_played), style='R')}\n"
                        f"Title hash: {char.title_hash if char.title_hash else 'N/A'}\n"
                        f"Member ID: {char.member_id}\nMember Type: {char.member_type}\n",
                    )
                    .add_field(
                        "Stats",
                        "\n".join(
                            [
                                f"{key.name.replace('_', '').title()}: {val} {STAR if val >= 90 and key.name != 'LIGHT_POWER' else ''}"
                                for key, val in char.stats.items()
                            ]
                        ),
                    ),
                    # We dont need char_id since its in the object itself.
                )
                for char in (c for c in characters.values())
            )
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
@tanjun.as_slash_command("lfg", "Look for fireteams to play with.")
async def lfg_command(
    ctx: tanjun.abc.SlashContext,
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
            _ACTIVITIES[activity][1], platform=platform_, date_range=1
        )
    except aiobungie.HTTPError as exc:
        raise tanjun.CommandError(exc.message)

    if not fireteams:
        raise tanjun.CommandError("No results found.")

    pages = (
        (
            hikari.UNDEFINED,
            hikari.Embed(
                title=fireteam.title,
                url=fireteam.url,
                timestamp=consts.naive_datetime(fireteam.date_created),
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

# last_group = destiny_group.with_command(
#     tanjun.slash_command_group("last", "Commands that returns the last thing occurred.")
# )
# 
# @last_group.with_command
# @tanjun.as_slash_command("raid", "Returns information about the last raid you played.")
# async def last_raid(
#     ctx: tanjun.abc.SlashContext,
#     client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
#     pool: pool.PgxPool = tanjun.inject(type=pool.PoolT)
# ) -> None:
#     ...
# 

search_group = destiny_group.with_command(
    tanjun.slash_command_group("search", "Commands search for stuff in the API.")
)

# This one is currently bugged.
@search_group.with_command
@tanjun.with_str_slash_option("name", "The player names to search for.")
@tanjun.as_slash_command("player", "Search for Destiny 2 players.")
async def search_players(
    ctx: tanjun.abc.SlashContext,
    name: str,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient)
) -> None:
    ...
    # results = await client.search_users(name)

    # if not results:
    #     raise tanjun.CommandError("No players found.")
    
    # iters = (
    #     (
    #         hikari.UNDEFINED,
    #         hikari.Embed(title=player.unique_name, url=player.link)
    #         .add_field(
    #             "Information",
    #             f"Membershiptype: {player.type}\n"
    #             f"ID: {player.id}\n"
    #             f"Crossave-override: {str(player.crossave_override).title()}"
    #         )
    #         .set_thumbnail(str(player.icon))
    #     )
    #     for player in results
    # )
    # await consts.generate_component(ctx, iters, component_client)

@search_group.with_command
@tanjun.with_str_slash_option("name", "The entity name to search for.")
@tanjun.with_str_slash_option("definition", "The definition of the entity. Default to inventory item", default=None)
@tanjun.as_slash_command("entity", "Search for Destiny 2 entity given its definition.")
async def search_entities(
    ctx: tanjun.abc.SlashContext,
    name: str,
    definition: str | None,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient)
) -> None:

    try:
        results = await client.search_entities(name, definition or "DestinyInventoryItemDefinition")
    except aiobungie.NotFound as exc:
        raise tanjun.CommandError(exc.message)

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


@search_group.with_command
@tanjun.with_str_slash_option(
    "query", "The clan name or id.", converters=(str, int), default=4389205
)
@tanjun.as_slash_command("clan", "Searches for Destiny clans by their name.")
async def get_clan(
    ctx: tanjun.abc.SlashContext,
    query: str | int,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
) -> None:

    await ctx.defer()
    try:
        # Allow the command to search for both methods.
        if isinstance(query, int):
            clan = await client.fetch_clan_from_id(query)
        else:
            clan = await client.fetch_clan(query)
    except aiobungie.NotFound as e:
        raise tanjun.CommandError(f"{e.message}")

    embed = hikari.Embed(description=f"{clan.about}", colour=consts.COLOR["invis"], url=clan.url)
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
            f"Creation date: {tanjun.conversion.from_datetime(consts.naive_datetime(clan.created_at), style='R')}\n"
            f"Type: {clan.type.name.title()}",
            inline=False,
        )
        .set_footer(", ".join(clan.tags))
    )

    if clan.owner is not None:
        embed.add_field(
            f"Owner",
            f"Name: [{clan.owner.unique_name}]({clan.owner.link})\n"
            f"ID: `{clan.owner.id}`\n"
            f"Joined at: {tanjun.conversion.from_datetime(consts.naive_datetime(clan.owner.joined_at), style='R')}\n"
            f"Last seen: {tanjun.conversion.from_datetime(consts.naive_datetime(clan.owner.last_online), style='R')}\n"
            f"Membership: `{clan.owner.type.name.title()}`"
        )
    await ctx.respond(embed=embed)


@search_group.with_command
@tanjun.with_int_slash_option("item_hash", "The item hash to get.")
@tanjun.as_slash_command("item", "Fetch a Bungie inventory item by its hash.")
async def item_definition_command(
    ctx: tanjun.abc.SlashContext,
    item_hash: int,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    cache_: cache.Memory[int, hikari.Embed] = tanjun.inject(type=cache.Memory),
) -> None:
    if cached_item := cache_.get(item_hash):
        await ctx.respond(embed=cached_item)
        return

    try:
        entity = await client.fetch_inventory_item(item_hash)
    except aiobungie.HTTPError as exc:
        raise tanjun.CommandError(f'{exc!s}')

    embed = _build_inventory_item_embed(entity)
    cache_.put(item_hash, embed)
    await ctx.respond(embed=embed)

@tanjun.with_cooldown("destiny")
@search_group.with_command
@tanjun.with_int_slash_option("instance", "The instance id of the activity.")
@tanjun.as_slash_command("post_activity", "Get post activity information given the activity's instance id.")
async def post_activity_command(
    ctx: tanjun.abc.SlashContext,
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
        raise tanjun.CommandError(e.message)

    features: list[str] = []

    if post.is_solo_flawless:
        features.append(f"Solo Flawless: {STAR}")

    elif post.is_flawless:
        features.append(f"Flawless: {STAR}")

    elif post.is_solo:
        features.append(f"Solo: {STAR}")

    rr = f'https://raid.report/pgcr/{instance}'
    embed = (
        hikari.Embed(title=post.mode, url=rr)
        .add_field(
            "Information",
            f"Reference id: {post.refrence_id}\n"
            f"Membership: {post.membership_type}\n"
            f"Starting phase: {post.starting_phase}\n"
            f"Date: {tanjun.conversion.from_datetime(consts.naive_datetime(post.occurred_at), style='R')}\n"
        )
    )

    try:
        activity = await client.rest.fetch_entity("DestinyActivityDefinition", post.refrence_id)
    except aiobungie.HTTPError:
        pass
    else:
        if raw_image := activity['pgcrImage']:
            embed.set_thumbnail(aiobungie.url.BASE + str(raw_image))

        if raw_props := activity['displayProperties']:
            embed.description = raw_props['description']
            embed.title = raw_props['name']

    for player in post.players:
        embed.add_field(
            f"{player.destiny_user.last_seen_name}#{player.destiny_user.code}",
            f"`Class`: [{player.character_class}]({player.destiny_user.link})\n"
            f"Light level: {player.light_level}\n"
            f"`Time`: {player.values.played_time}\n"
            f"`Kills`: {player.values.kills}\n"
            f"`Deaths`: {player.values.deaths}\n",
            inline=True
        )

    if features:
        embed.add_field(
            "Features",
            '\n'.join(features)
        )

    cache.put(instance, embed)
    await ctx.respond(embed=embed)

@tanjun.with_cooldown("destiny")
@destiny_group.with_command
@tanjun.with_member_slash_option(
    "member",
    "An optional member or get their collectibles.",
    default=None
)
@tanjun.with_str_slash_option(
    "username",
    "An optional Bungie membership username to fetch.",
    default=None
)
@tanjun.as_slash_command("collectibles", "Take a look at your last acquired items in Destiny 2.")
async def acquired_items_command(
    ctx: tanjun.abc.SlashContext,
    member: hikari.InteractionMember | hikari.User | None,
    username: str | None,
    client: aiobungie.Client = tanjun.inject(type=aiobungie.Client),
    pool_: pool.PgxPool = tanjun.inject(type=pool.PoolT),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient)
) -> None:

        member = member or ctx.author
        # This is kinda repeatable :\.
        if username is not None and '#' in username:
            try:
                membership = await _get_destiny_player(client, username)
                id_ = membership.id
                platform = membership.type.name.title()
            except LookupError as err:
                raise tanjun.CommandError(f'{err}')
        else:
            try:
                membership = await pool_.fetch_destiny_member(member.id)
                id_ = membership.membership_id
                platform = membership.membership_type
            except pool.ExistsError as e:
                raise tanjun.CommandError(e.message)

        profile = await client.fetch_profile(id_, _PLATFORMS[platform], aiobungie.ComponentType.COLLECTIBLES)

        if collectibles := profile.profile_collectibles:
            if not (recent_items := collectibles.recent_collectibles):
                raise tanjun.CommandError(f"No items found for {membership.name}")

            items = await aio.all_of(*[client.rest.fetch_entity("DestinyCollectibleDefinition", item) for item in recent_items])
            pages = (
                (
                    hikari.UNDEFINED,
                    hikari.Embed(
                        title=entity['displayProperties']['name'],
                        description=(
                            entity['displayProperties']['description']
                            if entity['displayProperties']['description']
                            else hikari.UNDEFINED
                        )
                    )
                    .set_thumbnail(aiobungie.url.BASE + entity['displayProperties']['icon'])
                    .add_field("Source", entity.get('sourceString', "Unknown"))
                    .add_field("Hash", entity['itemHash'])
                )
                for entity in items
            )
            await consts.generate_component(ctx, pages, component_client)

destiny = tanjun.Component(name="Destiny/Bungie", strict=True).load_from_scope().make_loader()