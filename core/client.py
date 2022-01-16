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
import subprocess
import traceback
import typing

import aiobungie
import click
import hikari
import tanjun
import yuyo
from hikari.internal import aio, ux

from core.psql import pool as pool_
from core.utils import cache
from core.utils import config as __config
from core.utils import net, traits

if typing.TYPE_CHECKING:
    from hikari import traits as hikari_traits


async def get_prefix(
    ctx: tanjun.abc.MessageContext,
    hash: traits.HashRunner = tanjun.inject(type=traits.HashRunner),
) -> str:
    if ctx.guild_id:
        try:
            return await hash.get_prefix(ctx.guild_id)
        except LookupError:
            pass
    # Probably will switch to all slash soon.
    return "."


def _build_bot() -> hikari.impl.GatewayBot:
    config = __config.Config()
    intents = hikari.Intents.ALL_GUILDS | hikari.Intents.ALL_MESSAGES
    bot = hikari.GatewayBot(
        banner=None,
        token=config.BOT_TOKEN,
        intents=intents,
        cache_settings=hikari.CacheSettings(components=config.CACHE),
    )
    _build_client(bot, config)
    return bot


def _build_client(
    bot: hikari_traits.GatewayBotAware, config: __config.Config
) -> tanjun.Client:
    pg_pool = pool_.PgxPool()
    client_session = net.HTTPNet()
    aiobungie_client = aiobungie.Client(
        config.BUNGIE_TOKEN,
        config.BUNGIE_CLIENT_SECRET,
        config.BUNGIE_CLIENT_ID,
        max_retries=4,
    )
    redis_hash = cache.Hash(aiobungie_client=aiobungie_client)
    mem_cache = cache.Memory[typing.Any, typing.Any]()
    yuyo_client = yuyo.ComponentClient.from_gateway_bot(bot, event_managed=False)

    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True,
            declare_global_commands=True,
        )
        # pg pool
        .set_type_dependency(pool_.PoolT, pg_pool)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, pg_pool.create_pool)
        # own aiohttp client session.
        .set_type_dependency(net.HTTPNet, typing.cast(traits.NetRunner, client_session))
        # Cache. This is kinda overkill but we need the memory cache for api requests
        # And the redis hash for stuff that are not worth storing in a database for the sake of speed.
        # i.e., OAuth2 tokens
        .set_type_dependency(traits.HashRunner, redis_hash)
        .set_type_dependency(cache.Memory, mem_cache)
        # aiobungie client
        .set_type_dependency(aiobungie.Client, aiobungie_client)
        .add_client_callback(
            tanjun.ClientCallbackNames.CLOSING, aiobungie_client.rest.close
        )
        # yuyo
        .set_type_dependency(yuyo.ComponentClient, yuyo_client)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, yuyo_client.open)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, yuyo_client.close)
        # Components.
        .load_modules("core.components")
        .set_human_only(True)
        # Prefix stuff.
        .set_prefix_getter(get_prefix)
        .add_prefix(".")
    )
    (
        tanjun.InMemoryCooldownManager()
        .set_bucket("destiny", tanjun.BucketResource.USER, 2, 4)
        .add_to_client(client)
    )
    client.metadata["uptime"] = datetime.datetime.now()
    return client


def _enable_logging(
    hikari: bool = False,
    tanjun: bool = False,
    net: bool = False,
    aiobungie: bool = False,
) -> None:
    logging.getLogger("hikari.gateway").setLevel(logging.CRITICAL)
    if hikari:
        logging.getLogger("hikari.rest").setLevel(ux.TRACE)
        logging.getLogger("hikari.cache").setLevel(logging.DEBUG)
    if net:
        logging.getLogger("core.net").setLevel(logging.DEBUG)
    if aiobungie:
        logging.getLogger("aiobungie.rest").setLevel(logging.DEBUG)
    if tanjun:
        logging.getLogger("hikari.tanjun").setLevel(logging.DEBUG)
        logging.getLogger("hikari.tanjun.context").setLevel(logging.DEBUG)
        logging.getLogger("hikari.tanjun.clients").setLevel(logging.DEBUG)
        logging.getLogger("hikari.tanjun.components").setLevel(logging.DEBUG)


@click.group(name="main", invoke_without_command=True, options_metavar="[options]")
@click.pass_context
def main(ctx: click.Context) -> None:
    _enable_logging(hikari=False, tanjun=True, net=True, aiobungie=True)
    if ctx.invoked_subcommand is None:
        _build_bot().run(status=hikari.Status.DO_NOT_DISTURB)

@main.group(short_help="Handles the db configs.", options_metavar="[options]")
def db() -> None:
    pass

@db.command(name="init", short_help="Build the database tables.")
def init() -> None:
    loop = aio.get_or_make_loop()
    try:
        loop.run_until_complete(pool_.PgxPool.create_pool(build=True))
    except Exception:
        click.echo("Couldn't build the daatabse tables.", err=True, color=True)
        traceback.print_exc()


@main.command(name="format", short_help="Format the bot code.")
def format_code() -> None:
    command = subprocess.run(
        "black core; isort core; codespell core -w -L crate;",
        capture_output=True,
        shell=True,
    )
    ok, err = command.stdout, command.stderr
    if ok:
        click.echo("Ok", color=True)
    else:
        click.echo(err, err=True, color=True)


@main.command(name="install", short_help="Install the requirements")
def install_requirements() -> None:
    with subprocess.Popen(
        [
            "python",
            "-m",
            "pip",
            "install",
            "-r",
            "requirements.txt",
            "--upgrade",
        ]
    ) as proc:
        ok, err = proc.communicate()
        if ok:
            click.echo("Installed requirements.")
        elif err:
            click.echo("Couldn't install requirements")
