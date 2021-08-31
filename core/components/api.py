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

from core.utils import format
from core.utils import net as net_

component = tanjun.Component()


@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("url", converters=str)
@tanjun.with_parser
@tanjun.as_message_command("net")
async def run_net(
    ctx: tabc.Context, url: str, net: net_.HTTPNet = tanjun.injected(type=net_.HTTPNet)
) -> None:
    """Make a GET http request to an api or else.

    !!! note
        The api must be application/json type.

    ### TODO: make this command with options for POST and GET methods maybe?

    Parameters
    ----------
    url : str
        The api url to call.
    net : HTTPNet
        The http client we're making the request with.
    """
    async with net as cli:
        try:
            result = await cli.request("GET", url)
            formatted = format.with_block(
                json.dumps(result, separators=(", ", ": ")), lang="py"
            )

        except Exception as exc:
            await ctx.respond(f"```hs\n{exc}\n```")
        try:
            await ctx.respond(formatted)
        except hikari.BadRequestError as err:
            await ctx.respond(f"```hs\n{err}\n```")


@tanjun.as_loader
def load_api(client: tanjun.Client) -> None:
    client.add_component(component.copy())
