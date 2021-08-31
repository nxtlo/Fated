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

import logging
import typing

import aiobungie
import hikari
import tanjun
from hikari import traits

from core.psql import pool
from core.utils import config as config_
from core.utils import net


class Tsujigiri(hikari.GatewayBot):
    """The bot."""

    def __init__(self, token: str, **kws) -> None:
        super().__init__(token, **kws)

        # bot configs
        self.config = config_.Config()

        # aiobungie destiny client.
        self.bungie: typing.Final[aiobungie.Client] = aiobungie.Client(
            self.config.BUNGIE_TOKEN  # type: ignore
        )

        # asyncpg pool
        self.pool = pool.PgxPool(debug=True)()

        # aiohttp networking.
        self.net = net.HTTPNet(3)

    def sub(self) -> None:
        self.event_manager.subscribe(
            hikari.GuildMessageCreateEvent, self.on_message_create
        )
        self.event_manager.subscribe(hikari.StartedEvent, self.on_ready)
        self.event_manager.subscribe(hikari.StoppingEvent, self.on_stopping)

    async def on_message_create(self, msg: hikari.GuildMessageCreateEvent) -> None:
        if msg.is_bot or not msg.is_human:
            return

        # http tests.
        if "?api" in str(msg.content):
            api = await self.net.mock()
            logging.info(api)

        logging.info("Recived {} from {}".format(msg.content, msg.author_id))

    async def on_ready(self, event: hikari.StartedEvent) -> None:
        logging.info("Bot is ready.")

    async def on_stopping(self, event: hikari.StoppingEvent) -> None:
        await self.net.close()


def build_bot() -> traits.GatewayBotAware:
    config = config_.Config()
    intents = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS
    bot = Tsujigiri(config.BOT_TOKEN, intents=intents)
    bot.sub()
    build_client(bot)
    return bot


def build_client(bot: traits.GatewayBotAware) -> tanjun.Client:
    # TODO: Add config as a dependency
    client = (
        tanjun.Client.from_gateway_bot(
            bot, mention_prefix=True, set_global_commands=True
        )
        .load_modules("core.components.meta")
        .add_prefix("?")
    )
    return client
