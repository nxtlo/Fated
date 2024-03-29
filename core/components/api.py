# -*- config: utf-8 -*-
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

__all__: tuple[str] = ("api",)

import typing

import alluka
import hikari
import tanjun
import yuyo

from core.std import boxed, traits


# Fun stuff.
@tanjun.as_message_command("dog")
async def doggo(
    ctx: tanjun.abc.MessageContext,
    net: alluka.Injected[traits.NetRunner],
) -> None:
    async with net as client:
        resp = await client.request(
            "GET",
            "https://some-random-api.ml/animal/dog",
        )
        assert isinstance(resp, dict)
        embed = hikari.Embed(description=resp["fact"])
        embed.set_image(resp["image"])

        await ctx.respond(embed=embed)


@tanjun.as_message_command("cat")
async def cat(
    ctx: tanjun.abc.MessageContext,
    net: alluka.Injected[traits.NetRunner],
) -> None:
    async with net as client:
        resp = await client.request("GET", "https://some-random-api.ml/animal/cat")
        assert isinstance(resp, dict)
        embed = hikari.Embed(description=resp["fact"])
        embed.set_image(resp["image"])

        await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("wink")
async def wink(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member | None,
    net: alluka.Injected[traits.NetRunner],
) -> None:
    async with net as client:
        resp = await client.request(
            "GET", "https://some-random-api.ml/animu/wink", getter="link"
        )
        assert isinstance(resp, str)
        embed = hikari.Embed(
            description=f"{ctx.author.username} winked at {member.username if member else 'their self'} UwU!"
        )
        embed.set_image(resp)

        await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("pat")
async def pat(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member | None,
    net: alluka.Injected[traits.NetRunner],
) -> None:
    async with net as client:
        resp = await client.request(
            "GET", "https://some-random-api.ml/animu/pat", getter="link"
        )
        assert isinstance(resp, str)
        embed = hikari.Embed(
            description=f"{ctx.author.username} pats {member.username if member else 'their self'} UwU!"
        )
        embed.set_image(resp)

        await ctx.respond(embed=embed)


@tanjun.with_argument("member", converters=tanjun.to_member, default=None)
@tanjun.with_parser
@tanjun.as_message_command("jail")
async def jail(
    ctx: tanjun.abc.MessageContext,
    member: hikari.Member | None,
    net: alluka.Injected[traits.NetRunner],
) -> None:
    member = member or ctx.member

    async with net as client:
        assert member is not None
        resp = await client.request(
            "GET",
            f"https://some-random-api.ml/canvas/jail?avatar={member.avatar_url}",
            unwrap_bytes=True,
        )
        embed = hikari.Embed(
            description=f"{ctx.author.username} jails {member.username if member else 'their self'}"
        )
        assert resp is not None
        embed.set_image(resp)

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
    net: alluka.Injected[traits.NetRunner],
    method: typing.Literal["GET", "POST"],
) -> None:
    async with net as cli:
        try:
            result = await cli.request(method, url, getter=getter)
        except Exception:
            await ctx.respond(boxed.error(str=True))
            return

        formatted = boxed.with_block(result, lang="json")
        await ctx.respond(formatted)


api = tanjun.Component(name="APIs", strict=True).load_from_scope().make_loader()
