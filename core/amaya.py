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

__all__: typing.List[str] = ["Amaya"]

import logging
import typing

import aiobungie
import hikari

from core.psql import pool
from core.utils import config as config

LOG: typing.Final[logging.Logger] = logging.getLogger("core.amaya")


class Amaya(hikari.GatewayBot):
    """Amaya the bot."""

    def __init__(self, token: str, /, **kws) -> None:
        super().__init__(token=token, **kws)

        # aiobungie destiny client.
        self.bungie: typing.Final[aiobungie.Client] = aiobungie.Client(
            config.BUNGIE_TOKEN
        )

        # asyncpg pool
        self.pool = pool.PgxPool(debug=True)()

        # self.session: typing.Final[aiohttp.ClientSession] = aiohttp.ClientSession()

    async def on_starting(self, _: hikari.StartingEvent) -> None:
        LOG.info("Bot is about to run.")

    async def on_ready(self, _: hikari.StartedEvent) -> None:
        LOG.info(f"Bot is ready.")

    async def on_closing(self, _: hikari.StoppingEvent) -> None:
        LOG.info("Stopping the blot now!")
