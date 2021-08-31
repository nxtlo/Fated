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

"""Commands here are for the owner and mods not for actual moderation."""

from __future__ import annotations

__all__: list[str] = ["component"]

import typing

import asyncpg
import tanjun
from tanjun import abc

from core.psql import pool as pool_
from core.utils import format

component = tanjun.Component(name="mod_component")


@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("query", converters=str)
@tanjun.with_parser
@tanjun.as_message_command("sql")
async def run_sql(
    ctx: abc.Context,
    query: str,
    pool: pool_.PgxPool = tanjun.injected(type=asyncpg.pool.Pool),
) -> None:
    """Run sql code to the database pool.

    Parameters
    ----------
    query : str
        The sql query. This also can be used with code blocks like this.
        ```sql
            SELECT * FROM public.tables
                WHERE THIS LIKE THAT
            LIMIT 1
        ```
    pool: asyncpg.Pool
        The pool we're acquiring.
    """

    query = format.parse_code(code=query)
    result: None | typing.Sequence[str] = None
    try:
        result = await pool.fetch(query)

        # SQL Code error
    except asyncpg.exceptions.PostgresSyntaxError:
        return await ctx.respond(f"```hs\n{sys.exc_info()[1]}\n```")  # type: ignore

        # Tables doesn't exists.
    except asyncpg.exceptions.UndefinedTableError:
        return await ctx.respond(f"```hs\n{sys.exc_info()[1]}\n```")  # type: ignore

    if result is None:
        await ctx.respond("Nothing found.")

    # We need an else here otherwise it will send both results.
    else:
        await ctx.respond(f"```hs\n{result}\n```")


@tanjun.as_loader
def load_mod(client: tanjun.Client) -> None:
    client.add_component(component.copy())
