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

__all__: tuple[str, ...] = ("PgxPool", "PartialPool")

import logging
import pathlib
import typing

import asyncpg
import asyncpg.exceptions
from hikari import iterators

from core import models
from core.std import config, traits

if typing.TYPE_CHECKING:
    import collections.abc as collections

    import aiobungie
    from hikari import snowflakes

_LOG: typing.Final[logging.Logger] = logging.getLogger("fated.pool")


class ExistsError(RuntimeError):
    """A runtime error raised when either the data exists or not found."""

    __slots__ = ("message",)

    def __init__(self, message: str = "", *args: typing.Any) -> None:
        super().__init__(*args)
        self.message = message

    def __repr__(self) -> str:
        return self.message

    def __str__(self) -> str:
        return self.message


class PartialPool(traits.PartialPool):
    """Partial pool implementation. A low-level wrapper around asyncpg.Pool."""

    __slots__ = ("_pool", "_config")

    def __init__(self, cfg: config.Config) -> None:
        self._pool: asyncpg.Pool | None = None
        self._config = cfg

    def __repr__(self) -> str:
        return hex(id(self._pool))

    @staticmethod
    def tables(path: pathlib.Path | None = None) -> str:
        p = path or pathlib.Path("core") / "psql" / "tables.sql"

        if not p.exists():
            raise FileNotFoundError(f"Tables file not found in {p!r}")

        with p.open("r") as schema:
            return schema.read()

    async def open(
        self, build: bool = False, schema_path: pathlib.Path | None = None
    ) -> None:
        """Creates a new connection pool and create the tables if build is True."""

        self._pool = pool = await asyncpg.create_pool(
            database=self._config.DB_NAME,
            user=self._config.DB_USER,
            password=self._config.DB_PASSWORD,
            host=self._config.DB_HOST,
            port=self._config.DB_PORT,
        )
        _LOG.debug("Created database pool.")

        if build:
            tables = self.tables(schema_path)

            async with pool.acquire() as conn:
                try:
                    await conn.execute(tables)
                    _LOG.info("Tables build success.")

                except Exception as exc:
                    raise RuntimeError("Failed to build the database tables.") from exc

                finally:
                    await pool.release(conn)

    async def close(self) -> None:
        if self._pool is None:
            raise RuntimeError("Can't close pool not created.")

        await self._pool.close()
        _LOG.debug("Database pool closed.")
        self._pool = None

    def _get_pool(self) -> asyncpg.Pool:
        if self._pool:
            return self._pool

        raise RuntimeError("Can't return pool not created.")

    async def execute(
        self, sql: str, /, *args: typing.Any, timeout: float | None = None
    ) -> None:
        async with self._get_pool().acquire() as conn:
            await conn.execute(
                sql, *args, timeout=typing.cast(float, timeout)
            )  # asyncpg has weird typings.

    async def fetch(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[typing.Any]:
        async with self._get_pool().acquire() as conn:
            return await conn.fetch(sql, *args, timeout=timeout)

    async def fetchrow(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[typing.Any] | collections.Mapping[str, typing.Any] | tuple[typing.Any]:
        async with self._get_pool().acquire() as conn:
            return await conn.fetchrow(sql, *args, timeout=timeout)

    async def fetchval(
        self,
        sql: str,
        /,
        *args: typing.Any,
        column: int | None = 0,
        timeout: float | None = None,
    ) -> typing.Any:
        async with self._get_pool().acquire() as conn:
            return await conn.fetchval(sql, *args, column=column, timeout=timeout)


@typing.final
class PgxPool(traits.PoolRunner):
    """Core database pool implementation."""

    __slots__: tuple[str, ...] = ("_pool",)

    def __init__(self, cfg: config.Config) -> None:
        self._pool = PartialPool(cfg)

    def __repr__(self) -> str:
        return f"<PgxPool(ref: {self._pool!r})>"

    @property
    def partial(self) -> traits.PartialPool:
        return self._pool

    async def fetch_destiny_member(
        self, user_id: snowflakes.Snowflake
    ) -> models.Membership:
        query = await self._pool.fetchrow(
            "SELECT * FROM Destiny WHERE ctx_id = $1;", user_id
        )
        if not query:
            raise ExistsError(f"User <@!{user_id}> not found.")

        return models.Membership.as_membership(dict(query))

    async def fetch_destiny_members(self) -> iterators.LazyIterator[models.Membership]:
        query = await self._pool.fetch("SELECT * FROM Destiny;")
        if not query:
            raise ExistsError("No users found in Destiny tables.")

        return iterators.FlatLazyIterator(
            models.Membership.as_membership(dict(member)) for member in query
        )

    async def put_destiny_member(
        self,
        user_id: snowflakes.Snowflake,
        membership_id: int,
        name: str,
        code: int,
        membership_type: aiobungie.MembershipType,
    ) -> None:
        try:
            await self._pool.execute(
                "INSERT INTO Destiny(ctx_id, membership_id, name, code, membership_type) "
                "VALUES($1, $2, $3, $4, $5)",
                int(user_id),
                membership_id,
                name,
                code,
                membership_type.name.title(),
            )
        except asyncpg.UniqueViolationError:
            raise ExistsError(f"User {user_id}:{name} exists.")

    async def remove_destiny_member(self, user_id: snowflakes.Snowflake) -> None:
        try:
            await self._pool.execute(
                "DELETE FROM Destiny WHERE ctx_id = $1", int(user_id)
            )
        except asyncpg.NoDataFoundError:
            raise ExistsError
