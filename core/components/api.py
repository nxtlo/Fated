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

"""Commands that makes api calls."""

from __future__ import annotations

__all__: list[str] = ["component"]

import json

import hikari
import tanjun
from tanjun import abc as tabc

from core.utils import consts, format
from core.utils import net as net_
from core.utils import traits

component = tanjun.Component(name="api")


@component.with_slash_command
#@tanjun.with_greedy_argument("name", converters=(str,), default=None)
#@tanjun.with_option("random", "--random", converters=(bool,), default=True)
#@tanjun.with_option(
#    "genre",
#    "--genre",
#    default=consts.randomize(),
#)
#@tanjun.with_parser
@tanjun.with_str_slash_option("name", "The anime's name.", default=None)
@tanjun.with_bool_slash_option("random", "Get a random anime.", default=True)
@tanjun.with_str_slash_option(
    "genre", 
    "The anime genre. This can be used with the random option.", 
    choices=consts.iter(),
    default=consts.randomize()
    )
@tanjun.as_slash_command("anime", "Returns basic information about an anime.")
async def get_anime(
    ctx: tabc.SlashContext,
    name: str,
    random: bool | None,
    genre: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = net_.Wrapper(net)
    anime = await jian.get_anime(ctx, name, random=random, genre=genre)
    await ctx.respond(embed=anime)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The manga name")
@tanjun.as_slash_command("manga", "Returns basic information about a manga.")
async def get_manga(
    ctx: tabc.SlashContext,
    name: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = net_.Wrapper(net)
    manga = await jian.get_manga(ctx, name)
    await ctx.respond(embed=manga)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The name of the definition.")
@tanjun.as_slash_command("def", "Returns a definition given a name.")
async def define(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    urban = net_.Wrapper(net)
    definition = await urban.get_definition(ctx, name)
    await ctx.respond(embed=definition)


@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("url", converters=str)
@tanjun.with_parser
@tanjun.as_message_command("net")
async def run_net(
    ctx: tabc.MessageContext,
    url: str,
    net: traits.NetRunner = net_.HTTPNet(),
) -> None:
    """Make a GET http request to an api or else.

    Note: The api must be application/json type.

    TODO: make this command with options for POST and GET methods maybe?

    Parameters:
        url : str
            The api url to call.
        net : HTTPNet
            The http client we're making the request with.
    """
    async with net as cli:
        try:
            result = await cli.request("GET", url)
            formatted = format.with_block(json.dumps(result), lang="json")

        except Exception as exc:
            await ctx.respond(f"```hs\n{exc}\n```")
        try:
            await ctx.respond(formatted)
        except hikari.BadRequestError as err:
            await ctx.respond(f"```hs\n{err}\n```")


@tanjun.as_loader
def load_api(client: tanjun.Client) -> None:
    client.add_component(component.copy())
