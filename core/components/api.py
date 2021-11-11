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

import typing

import hikari
import tanjun

from core.utils import consts, format
from core.utils import net as net_

component = tanjun.Component(name="api")


@component.with_slash_command
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
    net: net_.HTTPNet = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = net_.Wrapper(net)
    anime = await jian.get_anime(ctx, name, random=random, genre=genre)
    if anime:
        await ctx.respond(embed=anime)
    return None


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The manga name")
@tanjun.as_slash_command("manga", "Returns basic information about a manga.")
async def get_manga(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = net_.Wrapper(net)
    manga = await jian.get_manga(ctx, name)
    if manga is not None:
        await ctx.respond(embed=manga)
    return None


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The name of the definition.")
@tanjun.as_slash_command("def", "Returns a definition given a name.")
async def define(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = net_.HTTPNet(),
) -> None:
    urban = net_.Wrapper(net)
    definition = await urban.get_definition(ctx, name)
    if definition:
        await ctx.respond(embed=definition)
    return None

# Fun stuff.

@component.with_message_command
@tanjun.as_message_command("dog", "doggo")
async def doggo(ctx: tanjun.MessageContext, net: net_.HTTPNet = net_.HTTPNet()) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animal/dog",
            )
            if resp is not None:
                assert isinstance(resp, dict)
                embed = hikari.Embed(description=resp['fact'])
                embed.set_image(resp['image'])
    except net_.Error as exc:
        await ctx.respond(format.with_block(**exc.data))
        return
    await ctx.respond(embed=embed)

@component.with_message_command
@tanjun.as_message_command("cat", "kitten", "kittie")
async def kittie(ctx: tanjun.MessageContext, net: net_.HTTPNet = net_.HTTPNet()) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animal/cat",
            )
            if resp is not None:
                assert isinstance(resp, dict)
                embed = hikari.Embed(description=resp['fact'])
                embed.set_image(resp['image'])
    except net_.Error as exc:
        await ctx.respond(format.with_block(**exc.data))
        return
    await ctx.respond(embed=embed)

@component.with_message_command
@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("wink")
async def wink(
    ctx: tanjun.MessageContext,
    member: hikari.Member | None,
    net: net_.HTTPNet = net_.HTTPNet()
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animu/wink",
                getter="link"
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

@component.with_message_command
@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("pat")
async def pat(
    ctx: tanjun.MessageContext,
    member: hikari.Member | None,
    net: net_.HTTPNet = net_.HTTPNet()
) -> None:
    try:
        async with net as client:
            resp = await client.request(
                "GET",
                "https://some-random-api.ml/animu/pat",
                getter='link'
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

@component.with_message_command
@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("jail")
async def jail(
    ctx: tanjun.MessageContext,
    member: hikari.Member | None,
    net: net_.HTTPNet = net_.HTTPNet()
) -> None:
    member = member or ctx.member
    try:
        async with net as client:
            assert member is not None
            resp = await client.request(
                "GET",
                f"https://some-random-api.ml/canvas/jail?avatar={member.avatar_url}",
                read_bytes=True
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

@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("url", converters=str)
@tanjun.with_option("method", "--method", "-m", default='GET')
@tanjun.with_option("getter", "--get", "-g", default=None)
@tanjun.with_parser
@tanjun.as_message_command("net")
async def run_net(
    ctx: tanjun.abc.MessageContext,
    url: str,
    getter: str | None,
    method: typing.Literal["GET", "POST"] = "GET",
    net: net_.HTTPNet = net_.HTTPNet(),
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

@tanjun.as_loader
def load_api(client: tanjun.Client) -> None:
    client.add_component(component.copy())


@tanjun.as_unloader
def unload_examples(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
