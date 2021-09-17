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

import click
import hikari
import tanjun
from hikari.internal import aio
from setuptools import setup

from .utils import traits
from core.psql import pool as pool_
from core.utils import config as config_
from core.utils import net

if typing.TYPE_CHECKING:
    from hikari import traits as hikari_traits



class Fated(hikari.GatewayBot):
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
    ctx: tanjun.abc.MessageContext = tanjun.injected(type=tanjun.abc.MessageContext),
    pool: pool_.PoolT = tanjun.injected(type=pool_.PoolT),
) -> str | typing.Sequence[str]:

    guild: hikari.Snowflake = ctx.guild_id or (await ctx.fetch_guild()).id
    sql: typing.Final[str] = "SELECT prefix FROM guilds WHERE id = $1"

    if (prefix := await pool.fetchval(sql, guild)) is not None:
        return str(prefix)
    return ("?",)


def build_bot() -> hikari_traits.GatewayBotAware:
    # This is only global to pass it between
    # The bot and the client
    global config
    config = config_.Config()

    intents = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS
    bot = Fated(config.BOT_TOKEN, intents=intents)
    bot.sub()
    build_client(bot)
    return bot


def build_client(bot: hikari_traits.GatewayBotAware) -> tanjun.Client:
    # TODO: Add config as a dependency and aiobungie client here.
    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True,
            set_global_commands=True,
        )
        # Dependencies.
        .set_type_dependency(pool_.PoolT, tanjun.cache_callback(pool_.PgxPool()))
        .set_type_dependency(net.HTTPNet, typing.cast(traits.NetRunner, net.HTTPNet))
        # Global injected call backs.
        .set_callback_override(net.HTTPNet, traits.NetRunner)
        # Components.
        .load_modules("core.components.meta")
        .load_modules("core.components.mod")
        .load_modules("core.components.api")
        # Prefix stuff.
        .set_prefix_getter(get_prefix)
        .add_prefix("?")
    )

    # Client metadata
    client.metadata["uptime"] = datetime.datetime.utcnow()

    return client


@click.group(name="main", invoke_without_command=True, options_metavar="[options]")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        build_bot().run()


# This is only for exp.
@main.command(name="build", short_help="Build the rust extension.")
def build_ext() -> None:
    try:
        import setuptools_rust as setrust

        hasit = True
    except ImportError:
        hasit = False
        logging.warn("Setuptools rust not installed.")
        os.system("pip install setuptools_rust")

    if hasit is True:
        setup(
            name="rst",
            rust_extensions=[
                setrust.RustExtension(
                    "core.binds", binding=setrust.Binding.PyO3, path="rst/Cargo.toml"
                )
            ],
            packages=["rst"],
            zip_safe=False,
        )
        if os.path.exists("build"):
            os.system(
                f"mv build/lib/core/*.* core/binds/{'rst.so' if os.name != 'nt' else 'rst.pyd'} && rm -rf build"
            )
    else:
        raise RuntimeError("Coundl't build the rust extension.")


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
