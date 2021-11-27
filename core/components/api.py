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

import yuyo

__all__: tuple[str, ...] = (
    "api",
    "api_loader",
)

import datetime
import typing

import hikari
import tanjun

from core.utils import cache, consts, format
from core.utils import net as net_


# TODO: Use a paginator here.
@tanjun.with_str_slash_option("name", "The anime's name.", default=None)
@tanjun.with_bool_slash_option("random", "Get a random anime.", default=True)
@tanjun.with_str_slash_option(
    "genre",
    "The anime genre. This can be used with the random option.",
    choices=consts.iter(consts.GENRES),
    default=consts.randomize(),
)
@tanjun.as_slash_command("anime", "Returns basic information about an anime.")
async def get_anime(
    ctx: tanjun.abc.SlashContext,
    name: str,
    random: bool | None,
    genre: str,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
    cache: cache.Memory[str, hikari.Embed] = tanjun.inject(type=cache.Memory),
) -> None:
    if name and (cached_anime := cache.get(name.lower())):
        await ctx.respond(embed=cached_anime)
        return

    await ctx.defer()
    jian = net_.Wrapper(net)
    anime = await jian.get_anime(ctx, name, random=random, genre=genre)
    if anime:
        # Cache the anime if a name is not none.
        if name:
            cache.put(name.lower(), anime).set_expiry(datetime.timedelta(hours=6))
        await ctx.respond(embed=anime)


# TODO: Use a paginator here.
@tanjun.with_str_slash_option("name", "The manga name")
@tanjun.as_slash_command("manga", "Returns basic information about a manga.")
async def get_manga(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
    cache: cache.Memory[str, hikari.Embed] = tanjun.inject(type=cache.Memory),
) -> None:
    if name and (cached_manga := cache.get(name.lower())):
        await ctx.respond(embed=cached_manga)
        return

    await ctx.defer()
    jian = net_.Wrapper(net)
    manga = await jian.get_manga(ctx, name)
    if manga:
        if name:
            # Cache the manga if a name is not none.
            cache.put(name, manga).set_expiry(datetime.timedelta(minutes=1))
        await ctx.respond(embed=manga)


@tanjun.with_str_slash_option("name", "The name of the definition.")
@tanjun.as_slash_command("def", "Returns a definition given a name.")
async def define(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient),
) -> None:
    urban = net_.Wrapper(net)
    definitions = await urban.get_definition(ctx, name)

    if definitions:
        pages = ((hikari.UNDEFINED, embed) for embed in definitions)

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
        )
        next_definition = await paginator.get_next_entry()
        assert next_definition
        content, embed = next_definition
        msg = await ctx.respond(
            content=content, embed=embed, component=paginator, ensure_result=True
        )
        component_client.set_executor(msg, paginator)


# Fun stuff.
@tanjun.as_message_command("dog")
async def doggo(
    ctx: tanjun.MessageContext,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animal/dog",
            )
            if resp is not None:
                assert isinstance(resp, dict)
                embed = hikari.Embed(description=resp["fact"])
                embed.set_image(resp["image"])
    except net_.Error as exc:
        await ctx.respond(format.with_block(**exc.data))
        return
    await ctx.respond(embed=embed)


@tanjun.as_message_command("cat")
async def kittie(
    ctx: tanjun.MessageContext,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animal/cat",
            )
            if resp is not None:
                assert isinstance(resp, dict)
                embed = hikari.Embed(description=resp["fact"])
                embed.set_image(resp["image"])
    except net_.Error as exc:
        await ctx.respond(format.with_block(**exc.data))
        return
    await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("wink")
async def wink(
    ctx: tanjun.MessageContext,
    member: hikari.Member | None,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET", "https://some-random-api.ml/animu/wink", getter="link"
            )
            if resp is not None:
                assert isinstance(resp, str)
                embed = hikari.Embed(
                    description=f"{ctx.author.username} winked at {member.username if member else 'their self'} UwU!"
                )
                embed.set_image(resp)
    except net_.Error as exc:
        await ctx.respond(format.with_block(**exc.data))
        return
    await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("pat")
async def pat(
    ctx: tanjun.MessageContext,
    member: hikari.Member | None,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET", "https://some-random-api.ml/animu/pat", getter="link"
            )
            if resp is not None:
                assert isinstance(resp, str)
                embed = hikari.Embed(
                    description=f"{ctx.author.username} pats {member.username if member else 'their self'} UwU!"
                )
                embed.set_image(resp)
    except net_.Error as exc:
        await ctx.respond(format.with_block(**exc.data))
        return
    await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("jail")
async def jail(
    ctx: tanjun.MessageContext,
    member: hikari.Member | None,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
) -> None:
    member = member or ctx.member
    try:
        async with net as client:
            assert member is not None
            resp = await client.request(
                "GET",
                f"https://some-random-api.ml/canvas/jail?avatar={member.avatar_url}",
                read_bytes=True,
            )
            if resp is not None:
                assert isinstance(resp, bytes)
                embed = hikari.Embed(
                    description=f"{ctx.author.username} jails {member.username if member else 'their self'}"
                )
                embed.set_image(resp)
    except net_.Error as exc:
        await ctx.respond(format.with_block(**exc.data))
        return
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
    method: typing.Literal["GET", "POST"] = "GET",
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
) -> None:
    async with net as cli:
        try:
            result = await cli.request(method, url, getter=getter)
        except net_.Error:
            await ctx.respond(format.error(str=True))
            return
        try:
            formatted = format.with_block(result, lang="json")
            await ctx.respond(formatted)
        except hikari.HikariError:
            await ctx.respond(format.error(str=True))
        except Exception:
            pass


api = tanjun.Component(name="APIs", strict=True).load_from_scope()
api.metadata["about"] = "Component that makes API calls to different APIs."
api_loader = api.make_loader()
