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

__all__: typing.Sequence[str] = ("PgxPool",)

import asyncio
import copy
import logging
import pathlib
import typing

import asyncpg
import attr
from hikari.internal import aio

from core.utils import config

SelfT = typing.TypeVar("SelfT", bound="PgxPool")


@attr.define(weakref_slot=False, slots=True, init=True, kw_only=True)
class PgxPool:
    """An asyncpg pool."""

    _pool: asyncpg.pool.Pool = attr.field(default=asyncpg.Pool, repr=False)
    """The pool itself."""

    debug: bool = attr.field(repr=True, default=False)
    """Asyncio debug."""

    def __copy__(self: SelfT) -> SelfT:
        """Returns a shallow copy of the pool for attrs safe access."""
        return copy.copy(self)

    def __call__(self) -> typing.Generator[typing.Any, None, asyncpg.Pool]:
        loop = aio.get_or_make_loop()
        return loop.run_until_complete(self.create_pool())

    @property
    def clone(self: SelfT) -> SelfT:
        return self.__copy__()

    @classmethod
    async def create_pool(cls) -> asyncpg.pool.Pool:
        """Returns an asyncpg new pool and creates the tables."""
        cls._pool = await asyncpg.create_pool(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
        )

        async with cls._pool.acquire() as conn:
            try:
                tables = cls.tables()
                await conn.execute(tables)
            except Exception as e:
                raise e from None
        return cls._pool

    def serve(self) -> None:
        """Runs the pool."""
        loop = aio.get_or_make_loop()
        loop.set_debug(self.debug)
        loop.run_until_complete(self.create_pool())

    # Methods under are just typed asyncpg.Pool methods.
    # Also since the pool already aquires the connection for us
    # we don't need to re-aquire.

    async def execute(self, sql: str, /, *args, timeout: float | None = None) -> None:
        await self._pool.execute(sql, *args, timeout)

    async def fetch(
        self, sql: str, /, *args, timeout: float | None = None
    ) -> list[asyncpg.Record]:
        return await self._pool.fetch(sql, *args, timeout)

    async def fetchrow(
        self, sql: str, /, *args, timeout: float | None = None
    ) -> list[asyncpg.Record]:
        return await self._pool.fetchrow(sql, *args, timeout)

    async def fetchval(
        self,
        sql: str,
        /,
        *args,
        column: int | None = None,
        timeout: float | None = None,
    ) -> list[asyncpg.Record]:
        return await self._pool.fetchval(sql, *args, column, timeout)

    async def close(self, pool: asyncpg.pool.Pool) -> None:
        for tries in range(3):
            try:
                if pool._closing:
                    await asyncio.sleep(1 + tries * 2)
            except asyncpg.exceptions.InterfaceError as e:
                raise e
        await pool.close()

    @staticmethod
    def tables() -> str:
        p = pathlib.Path("core") / "psql" / "tables.sql"
        if not p.exists():
            raise LookupError(f"Tables file not found in {p!r}")
        with p.open() as table:
            return table.read()
