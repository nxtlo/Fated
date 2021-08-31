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

import copy
import logging
import pathlib
import typing

import asyncpg
import attr
from hikari.internal import aio

from core.utils import config

SelfT = typing.TypeVar("SelfT", bound="PgxPool")

LOG: typing.Final[logging.Logger] = logging.getLogger(__name__)


@attr.define(weakref_slot=False, slots=True, init=True, kw_only=True)
class PgxPool:
    """An asyncpg pool."""

    _pool: asyncpg.Pool = attr.field(default=asyncpg.Pool, repr=False)
    """The pool itself."""

    debug: bool = attr.field(repr=True, default=False)
    """Asyncio debug."""

    def __copy__(self: SelfT) -> SelfT:
        """Returns a shallow copy of the pool for attrs safe access."""
        return copy.copy(self)

    def __call__(self) -> typing.Generator[typing.Any, None, asyncpg.pool.Pool]:
        loop = aio.get_or_make_loop()
        loop.set_debug(self.debug)
        return loop.run_until_complete(self.create_pool())  # type: ignore

    @property
    def pool(self) -> asyncpg.Pool:
        """Access to `self._pool`."""
        return self._pool

    @property
    def clone(self: SelfT) -> SelfT:
        """Returns a clone of the pool."""
        return self.__copy__()

    @classmethod
    async def create_pool(cls) -> asyncpg.pool.Pool | None:
        config_ = config.Config()
        """Returns an asyncpg new pool and creates the tables."""
        cls._pool = await asyncpg.create_pool(  # type: ignore
            user=config_.DB_USER,
            password=config_.DB_PASSWORD,
            host=config_.DB_HOST,
            port=config_.DB_PORT,
        )
        tables = cls.tables()
        await cls._pool_build__(cls._pool, tables)  # type: ignore
        return cls._pool

    @staticmethod
    async def _pool_build__(pool: asyncpg.Pool, schema: str, /) -> None:
        async with pool.acquire() as conn:
            try:
                await conn.execute(schema)
                LOG.info("Building tables success.", stacklevel=2)
            except asyncpg.exceptions.PostgresError as exc:
                raise RuntimeError("Failed to build tahe database tables.") from exc
            finally:
                await pool.release(conn)
                LOG.info("Released connections from pool.")

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

    async def close(self) -> None:
        try:
            await self._pool.close()
        except asyncpg.exceptions.InterfaceError as e:
            raise e

    @staticmethod
    def tables() -> str:
        p = pathlib.Path("core") / "psql" / "tables.sql"
        if not p.exists():
            raise LookupError(f"Tables file not found in {p!r}")
        with p.open() as table:
            return table.read()
