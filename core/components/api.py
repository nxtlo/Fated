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

"""Commands that makes different api calls."""

from __future__ import annotations

__all__: tuple[str, ...] = ("api",)

import typing

import hikari
import tanjun
import yuyo
import alluka

from core.utils import boxed
from core.utils import net as net_


@tanjun.with_str_slash_option("name", "The anime's name.", default=None)
@tanjun.with_bool_slash_option("random", "Get a random anime.", default=True)
@tanjun.with_str_slash_option(
    "genre",
    "The anime genre. This can be used with the random option.",
    choices=boxed.iter(boxed.GENRES),
    default=boxed.randomize_genres(),
)
@boxed.add_help(
    "Get a random information about the anime!",
    options={
        "name": "An anime name to lookup",
        "random": "Whether to get you a random anime or not.",
        "genre": "The genre of the anime to return information about.",
    }
)
@tanjun.as_slash_command("anime", "Returns basic information about an anime.")
async def get_anime(
    ctx: tanjun.abc.SlashContext,
    name: str,
    random: bool | None,
    genre: str,
    jian: alluka.Injected[net_.AnyWrapper],
    component_client: alluka.Injected[yuyo.ComponentClient],
) -> None:
    await ctx.defer()

    try:
        anime_embed = await jian.fetch_anime(name, random=random, genre=genre)
    except net_.Error as e:
        raise tanjun.CommandError(e.data["message"])

    assert anime_embed is not None
    if not isinstance(anime_embed, typing.Generator):
        await ctx.respond(embed=anime_embed)
        return

    await boxed.generate_component(
        ctx, ((hikari.UNDEFINED, embed) for embed in anime_embed), component_client
    )

@tanjun.as_slash_command("help", "Get help about the bot.")
async def help_(ctx: tanjun.abc.SlashContext) -> None:
    emb = hikari.Embed(title="Bot help menu.")
    for command in ctx.client.iter_slash_commands():
        summary: str = command.metadata.get("summary", "No Summary")
        options: str = command.metadata.get("options", "No Options")

        emb.add_field(command.name, '\n'.join([f"{summary}\n\n{options}"]))

    await ctx.respond(embed=emb)

@tanjun.with_str_slash_option("name", "The manga name")
@tanjun.as_slash_command("manga", "Returns basic information about a manga.")
async def get_manga(
    ctx: tanjun.abc.SlashContext,
    name: str,
    jian: alluka.Injected[net_.AnyWrapper],
    component_client: alluka.Injected[yuyo.ComponentClient],
) -> None:
    await ctx.defer()

    manga_embeds = await jian.fetch_manga(name)
    if manga_embeds:
        await boxed.generate_component(
            ctx, ((hikari.UNDEFINED, embed) for embed in manga_embeds), component_client
        )


@tanjun.with_str_slash_option("name", "The name of the definition.")
@tanjun.as_slash_command("def", "Returns a definition given a name.")
async def define(
    ctx: tanjun.abc.SlashContext,
    name: str,
    urban: alluka.Injected[net_.AnyWrapper],
    component_client: alluka.Injected[yuyo.ComponentClient],
) -> None:
    definitions = await urban.fetch_definitions(name)

    if definitions:
        pages = ((hikari.UNDEFINED, embed) for embed in definitions)

        await boxed.generate_component(ctx, pages, component_client)


# Fun stuff.
@tanjun.as_message_command("dog")
async def doggo(
    ctx: tanjun.abc.MessageContext,
    net: alluka.Injected[net_.HTTPNet],
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animal/dog",
            )
            assert isinstance(resp, dict)
            embed = hikari.Embed(description=resp["fact"])
            embed.set_image(resp["image"])
    except net_.Error:
        pass

    await ctx.respond(embed=embed)


@tanjun.as_message_command("cat")
async def kittie(
    ctx: tanjun.abc.MessageContext,
    net: alluka.Injected[net_.HTTPNet],
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animal/cat",
            )
            assert isinstance(resp, dict)
            embed = hikari.Embed(description=resp["fact"])
            embed.set_image(resp["image"])
    except net_.Error:
        pass
    await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("wink")
async def wink(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member | None,
    net: alluka.Injected[net_.HTTPNet],
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET", "https://some-random-api.ml/animu/wink", getter="link"
            )
            assert isinstance(resp, str)
            embed = hikari.Embed(
                description=f"{ctx.author.username} winked at {member.username if member else 'their self'} UwU!"
            )
            embed.set_image(resp)
    except net_.Error:
        pass
    await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("pat")
async def pat(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member | None,
    net: alluka.Injected[net_.HTTPNet],
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET", "https://some-random-api.ml/animu/pat", getter="link"
            )
            assert isinstance(resp, str)
            embed = hikari.Embed(
                description=f"{ctx.author.username} pats {member.username if member else 'their self'} UwU!"
            )
            embed.set_image(resp)
    except net_.Error:
        pass
    await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("jail")
async def jail(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member | None,
    net: alluka.Injected[net_.HTTPNet],
) -> None:
    member = member or ctx.member
    try:
        async with net as client:
            assert member is not None
            resp = await client.request(
                "GET",
                f"https://some-random-api.ml/canvas/jail?avatar={member.avatar_url}",
                unwrap_bytes=True,
            )
            assert isinstance(resp, bytes)
            embed = hikari.Embed(
                description=f"{ctx.author.username} jails {member.username if member else 'their self'}"
            )
            embed.set_image(resp)
    except net_.Error:
        pass
    await ctx.respond(embed=embed)


@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("url", converters=str)
@tanjun.with_option("method", "--method", "-m", default="GET")
@tanjun.with_option("getter", "--get", "-g", default=None)
@tanjun.with_parser
@tanjun.as_message_command("net")
async def run_net(
    ctx: tanjun.abc.MessageContext,
    url: str,
    getter: str | None,
    net: alluka.Injected[net_.HTTPNet],
    method: typing.Literal["GET", "POST"],
) -> None:
    async with net as cli:
        try:
            result = await cli.request(method, url, getter=getter)
        except net_.Error:
            await ctx.respond(boxed.error(str=True))
            return
        formatted = boxed.with_block(result, lang="json")
        await ctx.respond(formatted)


api = tanjun.Component(name="APIs", strict=True).load_from_scope().make_loader()
