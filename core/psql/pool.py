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

__all__: typing.Sequence[str] = ("PgxPool", "PoolT")

import asyncio
import logging
import os
import pathlib
import typing

import asyncpg
import attr  # type: ignore[import]
import colorlog

from core.utils import config, traits

LOG: typing.Final[logging.Logger] = colorlog.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# For some reason decorating classes with attrs or dataclasses
# breaks the injection callbacks. Not sure why but removing it now.

# @attr.define(weakref_slot=False, slots=True, init=True, kw_only=True)
class PgxPool(traits.PoolRunner):
    """An asyncpg pool."""

    _pool: typing.ClassVar[asyncpg.Pool | None] = None
    """The pool itself."""

    def __call__(self) -> typing.Coroutine[None, None, asyncpg.pool.Pool | None]:
        asyncio.get_running_loop()
        return self.create_pool()

    @property
    def pool(self) -> asyncpg.Pool | None:
        """Access to `self._pool`."""
        return self._pool

    @classmethod
    async def create_pool(cls, *, build: bool = False) -> asyncpg.pool.Pool | None:
        config_ = config.Config()
        """Returns an asyncpg new pool and creates the tables."""
        cls._pool = await asyncpg.create_pool(
            database=config_.DB_NAME,
            user=config_.DB_USER,
            password=config_.DB_PASSWORD,
            host=config_.DB_HOST,
            port=config_.DB_PORT,
        )
        if build is True:
            tables = cls.tables()
            async with cls._pool.acquire() as conn:
                try:
                    LOG.info(tables)
                    await conn.execute(tables)
                    os.system("clear" if os.name != "nt" else "cls")
                    LOG.info("Tables build success.")
                except asyncpg.exceptions.PostgresError as exc:
                    raise RuntimeError("Failed to build the database tables.") from exc
                finally:
                    await cls._pool.release(conn)
        return cls._pool

    # Methods under are just typed asyncpg.Pool methods.
    # Also since the pool already acquires the connection for us
    # we don't need to re-aquire.

    async def execute(
        self, sql: str, /, *args: typing.Any, timeout: float | None = None
    ) -> None:
        await self._pool.execute(sql, *args, timeout)

    async def fetch(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[asyncpg.Record]:
        return await self._pool.fetch(sql, *args, timeout)

    async def fetchrow(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[asyncpg.Record]:
        return await self._pool.fetchrow(sql, *args, timeout)

    async def fetchval(
        self,
        sql: str,
        /,
        *args: typing.Any,
        column: int | None = None,
        timeout: float | None = None,
    ) -> typing.Any:
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


PoolT = typing.NewType("PoolT", PgxPool)
"""A new type hint for the Pool class it self.
This only used as a type hint for injecting and type dependencies.
"""
