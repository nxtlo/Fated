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

from __future__ import annotations

import aiobungie
import hikari
import tanjun
from aiobungie import crate
from aiobungie.internal.helpers import UndefinedType

component = tanjun.Component(name="destiny")
destiny_group = component.with_slash_command(
    tanjun.SlashCommandGroup("destiny", "Commands related to Destiny 2.")
)

@destiny_group.with_command
@tanjun.with_str_slash_option("name", "The clan name", converters=(str,))
@tanjun.as_slash_command("clan", "Searches for Destiny clans by their name.")
async def get_clan(
    ctx: tanjun.abc.SlashContext,
    name: str,
    client: aiobungie.Client = tanjun.injected(type=aiobungie.Client),
) -> None:
    await ctx.defer()
    try:
        clan: crate.Clan = await client.fetch_clan(name)
    except aiobungie.ClanNotFound as e:
        await ctx.respond(e)
        return None
    embed = hikari.Embed(description=clan.motto)

    if isinstance(clan.owner.name, UndefinedType):
        owner_name = (
            f'{clan.owner.last_seen_name}#{clan.owner.code if clan.owner.code else ""}'
        )

    (
        embed.set_author(name=clan.name, url=clan.url, icon=str(clan.avatar))
        .set_thumbnail(str(clan.avatar))
        .set_image(str(clan.banner))
        .add_field(
            "About",
            f"ID: {clan.id}\n"
            f"Total members: {clan.member_count}\n"
            f"About: {clan.about}\n"
            f"Public: {clan.is_public}\n"
            f"Creation date: {clan.created_at}\n"
            f"Type: {clan.type}",
            inline=False,
        )
        .add_field(
            f"Owner",
            f"Name: [{owner_name}]({clan.owner.link})\n"
            f"ID: {clan.owner.id}\n"
            f"Type: {str(clan.owner.type)}\n"
            f"Last seen: {clan.owner.last_online}\n"
            f"Public profile: {clan.owner.is_public}\n"
            f"Membership types: {', '.join(str(t) for t in clan.owner.types)}",
        )
        .add_field(
            "Features",
            f"Join Leve: {clan.features.join_level}\n"
            f"Capabilities: {clan.features.capabilities}\n"
            f"Memberships: {', '.join(str(c) for c in clan.features.membership_types)}",
        )
        .set_footer(", ".join(clan.tags))
    )
    await ctx.respond(embed=embed)


@tanjun.as_loader
def load_destiny(client: tanjun.abc.Client):
    client.add_component(component.copy())
