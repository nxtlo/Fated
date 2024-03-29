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

from __future__ import annotations

import logging
import subprocess
import traceback
import typing

import aiobungie
import click
import hikari
import tanjun
import yuyo
from hikari.internal import aio

from core.psql import pool
from core.std import cache
from core.std import config as __config
from core.std import net, traits

if typing.TYPE_CHECKING:
    from hikari import traits as hikari_traits

_LOGGER = logging.getLogger("fated.client")


def _setup_client(
    client: tanjun.Client,
    bot: hikari_traits.GatewayBotAware,
    config: __config.Config,
    /,
) -> None:
    # Database pool.
    pg_pool = pool.PgxPool(config)
    # Networking.
    client_session = net.HTTPNet()
    # Cache
    redis_hash = cache.Hash(config)
    mem_cache = cache.Memory[typing.Any, typing.Any]()
    # yuyo client
    yuyo_client = yuyo.ComponentClient.from_gateway_bot(bot, event_managed=False)

    (
        client
        # pg pool
        .set_type_dependency(traits.PoolRunner, pg_pool)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, pg_pool.partial.open)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, pg_pool.partial.close)
        # HTTP.
        .set_type_dependency(traits.NetRunner, client_session)
        # Cache. This is kinda overkill but we need the memory cache for api requests
        # And the redis hash for stuff that are not worth storing in a database for the sake of speed.
        # i.e., OAuth2 tokens
        .set_type_dependency(traits.HashRunner, redis_hash)
        .set_type_dependency(cache.Memory, mem_cache)
        # yuyo
        .set_type_dependency(yuyo.ComponentClient, yuyo_client)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, yuyo_client.open)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, yuyo_client.close)
        # Components.
        .load_modules("core.components")
        .set_human_only(True)
        # Prefix stuff.
        .add_prefix(".")
    )

    if config.verify_bungie_tokens():
        _LOGGER.debug("aiobungie tokens found.")
        aiobungie_client = aiobungie.Client(
            str(config.BUNGIE_TOKEN),
            client_secret=config.BUNGIE_CLIENT_SECRET,
            client_id=config.BUNGIE_CLIENT_ID,
            max_retries=1,
        )
        redis_hash.client(aiobungie_client)
        client.set_type_dependency(aiobungie.Client, aiobungie_client)
        client.add_client_callback(
            tanjun.ClientCallbackNames.CLOSING, aiobungie_client.rest.close
        ).add_client_callback(
            tanjun.ClientCallbackNames.STARTING, aiobungie_client.rest.open
        )
        (
            tanjun.InMemoryCooldownManager()
            .set_bucket("destiny", tanjun.BucketResource.USER, 2, 4)
            .add_to_client(client)
        )
        (
            tanjun.InMemoryConcurrencyLimiter()
            .set_bucket("destiny", tanjun.BucketResource.USER, 2)
            .add_to_client(client)
        )
        client.load_modules("core.components.destiny")


def _build_client(
    bot: hikari_traits.GatewayBotAware, config: __config.Config
) -> tanjun.Client:
    client = tanjun.Client.from_gateway_bot(
        bot, mention_prefix=True, declare_global_commands=True
    )
    _setup_client(client, bot, config)
    return client


def _build_bot() -> hikari.impl.GatewayBot:
    config = __config.Config.into_dotenv()
    intents = hikari.Intents.ALL_GUILDS | hikari.Intents.ALL_MESSAGES
    bot = hikari.GatewayBot(
        banner=None,
        token=config.BOT_TOKEN,
        intents=intents,
        cache_settings=hikari.impl.CacheSettings(components=config.cache_settings()),
    )
    _build_client(bot, config)
    return bot


def _enable_logging() -> None:
    logging.getLogger("hikari.cache").setLevel(logging.DEBUG)
    logging.getLogger("aiobungie.rest").setLevel(logging.DEBUG)

    for logger in (
        logging.getLogger("core.net"),
        logging.getLogger("fated.cache"),
        logging.getLogger("fated.pool"),
        logging.getLogger("fated.client"),
    ):
        logger.setLevel(logging.DEBUG)

    for logger in (
        logging.getLogger("hikari.tanjun"),
        logging.getLogger("hikari.tanjun.context"),
        logging.getLogger("hikari.tanjun.clients"),
        logging.getLogger("hikari.tanjun.components"),
    ):
        logger.setLevel(logging.DEBUG)


@click.group(name="main", invoke_without_command=True, options_metavar="[options]")
@click.pass_context
def main(ctx: click.Context) -> None:
    _enable_logging()
    if ctx.invoked_subcommand is None:
        _build_bot().run(status=hikari.Status.DO_NOT_DISTURB)


@main.group(short_help="Database related commands.", options_metavar="[options]")
def db() -> None:
    pass


@db.command(name="init", short_help="Build the database tables.")
def init() -> None:
    loop = aio.get_or_make_loop()
    pool_ = pool.PartialPool(__config.Config.into_dotenv())
    try:
        loop.run_until_complete(pool_.open(build=True))
    except Exception:
        click.echo(
            "Encountered an error while building the database tables.",
            err=True,
            color=True,
        )
        traceback.print_exc()
    finally:
        loop.run_until_complete(pool_.close())


@main.command(name="format", short_help="Format the bot code.")
def format_code() -> None:
    commands = ("ruff format", "isort core", "codespell core -w -L crates")
    for command in commands:
        subprocess.run(command, shell=True)


@main.command(name="install", short_help="Install the requirements")
def install_requirements() -> None:
    subprocess.run(
        [
            "py",
            "-m",
            "pip",
            "install",
            "-r",
            "requirements.txt",
            "--upgrade",
        ]
    )
