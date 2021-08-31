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
import os
import traceback
import typing

import aiobungie
import asyncpg
import click
import hikari
import tanjun
from hikari import traits
from hikari.internal import aio

from core.psql.pool import PgxPool
from core.utils import config as config_
from core.utils import net


class Tsujigiri(hikari.GatewayBot):
    """The bot."""

    def __init__(self, token: str, **kws) -> None:
        super().__init__(token, **kws)

        # bot configs
        self.config = config_.Config()

        # aiobungie destiny client.
        # TODO inject this as a dependency
        self.bungie: typing.Final[aiobungie.Client] = aiobungie.Client(
            self.config.BUNGIE_TOKEN  # type: ignore
        )

    def sub(self) -> None:
        self.event_manager.subscribe(
            hikari.GuildMessageCreateEvent, self.on_message_create
        )
        self.event_manager.subscribe(hikari.StartedEvent, self.on_ready)

    async def on_message_create(self, msg: hikari.GuildMessageCreateEvent) -> None:
        if msg.is_bot or not msg.is_human:
            return

    async def on_ready(self, event: hikari.StartedEvent) -> None:
        logging.info("Bot is ready.")


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
        .add_type_dependency(asyncpg.pool.Pool, PgxPool())  # db pool
        .add_type_dependency(net.HTTPNet, net.HTTPNet)  # http client session.
        .load_modules("core.components.meta")
        .load_modules("core.components.mod")
        .load_modules("core.components.api")
        .add_prefix("?")
    )
    return client


@click.group(name="main", invoke_without_command=True, options_metavar="[options]")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        build_bot().run()


@main.group(short_help="Handles the db configs.", options_metavar="[options]")
def db() -> None:
    pass


@db.command(name="init", short_help="Build the database tables.")
def init() -> None:
    loop = aio.get_or_make_loop()
    try:
        loop.run_until_complete(PgxPool.create_pool(build=True))
    except Exception:
        click.echo(f"Couldn't build the daatabse tables.", err=True)
        traceback.print_exc()


@main.command(name="format", short_help="Format the bot code.")
def format_code() -> None:
    try:
        os.system("black core")
        os.system("isort core")
        os.system("codespell core -w")
    except Exception:
        pass
