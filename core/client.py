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

import datetime
import logging
import os
import traceback
import typing

import asyncpg
import click
import hikari
import tanjun
from aiobungie.internal import time
from hikari import traits as hikari_traits
from hikari.internal import aio

from core.psql import pool as pool_
from core.utils import config as config_
from core.utils import net


class Tsujigiri(hikari.GatewayBot):
    """The bot."""

    def __init__(self, token: str, **kws: typing.Any) -> None:
        super().__init__(token, **kws)

    def sub(self) -> None:
        self.event_manager.subscribe(
            hikari.GuildMessageCreateEvent, self.on_message_create
        )
        self.event_manager.subscribe(hikari.StartedEvent, self.on_ready)

    async def on_message_create(self, msg: hikari.GuildMessageCreateEvent) -> None:
        if msg.is_bot or not msg.is_human:
            return

    async def on_ready(self, _: hikari.StartedEvent) -> None:
        logging.info("Bot is ready.")


async def get_prefix(
    ctx: tanjun.abc.Context,
    pool: pool_.PgxPool = tanjun.injected(type=asyncpg.pool.Pool),
) -> str | typing.Sequence[str]:
    query: str = "SELECT prefix FROM guilds WHERE id = $1"
    if (prefix := await pool.fetchval(query, ctx.guild_id)) is not None:
        return str(prefix)
    return ()


def build_bot() -> hikari_traits.GatewayBotAware:
    # This is only global to pass it between
    # The bot and the client
    global config
    config = config_.Config()

    intents = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS
    bot = Tsujigiri(config.BOT_TOKEN, intents=intents)
    bot.sub()
    build_client(bot)
    return bot


def build_client(bot: hikari_traits.GatewayBotAware) -> tanjun.Client:
    # TODO: Add config as a dependency and aiobungie client here.
    client = (
        tanjun.Client.from_gateway_bot(
            bot, mention_prefix=True, set_global_commands=True
        )
        .add_type_dependency(asyncpg.pool.Pool, pool_.PgxPool())  # db pool
        .add_type_dependency(net.HTTPNet, net.HTTPNet)  # http client session.
        .load_modules("core.components.meta")
        .load_modules("core.components.mod")
        .load_modules("core.components.api")
        .set_prefix_getter(get_prefix)
        .add_prefix("?")
    )
    client.metadata["uptime"] = datetime.datetime.utcnow()
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
        loop.run_until_complete(pool_.PgxPool.create_pool(build=True))
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
