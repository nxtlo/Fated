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

__all__: tuple[str, ...] = ("PgxPool", "PoolT")

import datetime
import logging
import pathlib
import typing

import asyncpg
import asyncpg.exceptions
from hikari import iterators

from core.utils import traits

from . import models

if typing.TYPE_CHECKING:
    import collections.abc as collections

    import aiobungie
    from hikari import snowflakes


_LOG: typing.Final[logging.Logger] = logging.getLogger("fated.pool")
_LOG.setLevel(logging.INFO)


class ExistsError(RuntimeError):
    """A runtime error raised when either the data exists or not found."""

    def __init__(self, message: str = "") -> None:
        self.message = message

    def __repr__(self) -> str:
        return self.message

    def __str__(self) -> str:
        return self.message


class PgxPool(traits.PoolRunner):
    """An asyncpg pool impl."""

    __slots__: tuple[str, ...] = ("_pool",)

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def __call__(self) -> asyncpg.Pool:
        return await self.create_pool()

    def __await__(self) -> collections.Generator[typing.Any, None, asyncpg.Pool]:
        return self.create_pool().__await__()

    @classmethod
    async def create_pool(
        cls, *, build: bool = False, schema_path: pathlib.Path | None = None
    ) -> asyncpg.Pool:
        """Creates a new connection pool and created the tables if build is True."""

        from core.utils import config

        config_ = config.Config()

        cls._pool = pool = await asyncpg.create_pool(
            database=config_.DB_NAME,
            user=config_.DB_USER,
            password=config_.DB_PASSWORD,
            host=config_.DB_HOST,
            port=config_.DB_PORT,
        )
        assert pool is not None

        if build:
            tables = cls.tables(schema_path)
            conn: asyncpg.Connection

            async with pool.acquire() as conn:
                try:
                    await conn.execute(tables)
                    _LOG.info("Tables build success.")

                except Exception as exc:
                    raise RuntimeError("Failed to build the database tables.") from exc

                finally:
                    await pool.release(conn)
        return pool

    async def _execute(
        self, sql: str, /, *args: typing.Any, timeout: float | None = None
    ) -> None:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                sql, *args, timeout=typing.cast(float, timeout)
            )  # asyncpg has weird typings.

    async def _fetch(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[typing.Any]:

        assert self._pool is not None
        async with self._pool.acquire() as conn:
            return await conn.fetch(sql, *args, timeout=timeout)

    async def _fetchrow(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[typing.Any] | collections.Mapping[str, typing.Any] | tuple[typing.Any]:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(sql, *args, timeout=timeout)

    async def _fetchval(
        self,
        sql: str,
        /,
        *args: typing.Any,
        column: int | None = 0,
        timeout: float | None = None,
    ) -> typing.Any:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, *args, column=column, timeout=timeout)

    @property
    def pool(self) -> asyncpg.Pool:
        assert self._pool is not None
        return self._pool

    @property
    def pools(self) -> int:
        assert self._pool is not None
        return self._pool.get_size()

    async def close(self) -> None:
        self._pool = None
        # This does the same thing as await pool.close()
        del self._pool
        _LOG.debug("Pool closed.")

    @staticmethod
    def tables(path: pathlib.Path | None = None) -> str:
        p = path or pathlib.Path("core") / "psql" / "tables.sql"

        if not p.exists():
            raise FileNotFoundError(f"Tables file not found in {p!r}")

        with p.open() as table:
            return table.read()

    async def fetch_destiny_member(
        self, user_id: snowflakes.Snowflake
    ) -> models.Destiny:
        query = await self._fetchrow(
            "SELECT * FROM Destiny WHERE ctx_id = $1;", user_id
        )
        if not query:
            raise ExistsError(f"User <@!{user_id}> not found.")

        return models.Destiny.into(dict(query))

    async def fetch_destiny_members(self) -> iterators.LazyIterator[models.Destiny]:
        query = await self._fetch("SELECT * FROM Destiny;")
        if not query:
            raise ExistsError("No users found in Destiny tables.")

        return iterators.FlatLazyIterator(
            [models.Destiny.into(dict(member)) for member in query]
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
            await self._execute(
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
            await self._execute("DELETE FROM Destiny WHERE ctx_id = $1", int(user_id))
        except asyncpg.NoDataFoundError:
            raise ExistsError

    # This is not used and probably will be Removed soonish.
    async def fetch_mutes(self) -> iterators.LazyIterator[models.Mutes]:
        query = await self._fetch("SELECT * FROM Mutes;")
        if not query:
            raise ExistsError("No mutes found.")

        return iterators.FlatLazyIterator(
            [models.Mutes.into(dict(entry)) for entry in query]
        )

    async def put_mute(
        self,
        member_id: snowflakes.Snowflake,
        author_id: snowflakes.Snowflake,
        guild_id: snowflakes.Snowflake,
        duration: float,
        why: str,
    ) -> None:
        try:
            await self._execute(
                "INSERT INTO Mutes(member_id, guild_id, author_id, muted_at, duration, why) "
                "VALUES($1, $2, $3, $4, $5, $6)",
                int(member_id),
                int(guild_id),
                int(author_id),
                datetime.datetime.utcnow(),
                duration,
                why,
            )
        except asyncpg.UniqueViolationError:
            raise ExistsError(f"Member {member_id} is already muted.")

    async def remove_mute(self, user_id: snowflakes.Snowflake) -> None:
        try:
            await self._execute("DELETE FROM Mutes WHERE member_id = $1", int(user_id))
        except asyncpg.NoDataFoundError:
            raise ExistsError(f"User {user_id} is not muted.")

    async def fetch_notes(self) -> iterators.LazyIterator[models.Notes]:
        """Fetch all notes and return a lazy iterator of notes."""
        query = await self._fetch("SELECT * FROM Notes;")
        if not query:
            raise ExistsError("No notes found.")

        return iterators.FlatLazyIterator(
            models.Notes.into(dict(note)) for note in query
        )

    async def fetch_notes_for(
        self, user_id: snowflakes.Snowflake
    ) -> collections.Collection[models.Notes]:
        """Fetch notes for a specific snowflake ID."""
        query = await self._fetch("SELECT * FROM Notes WHERE author_id = $1", user_id)
        if not query:
            raise ExistsError("No notes found.")

        return [models.Notes.into(dict(note)) for note in query]

    async def put_note(
        self,
        name: str,
        content: str,
        author_id: snowflakes.Snowflake,
    ) -> None:
        try:
            await self._execute(
                "INSERT INTO Notes(name, content, author_id, created_at) "
                "VALUES($1, $2, $3, $4)",
                name,
                content,
                int(author_id),
                datetime.datetime.utcnow(),
            )
        except asyncpg.UniqueViolationError as exc:
            raise ExistsError(f"You already have a note with name {name}.") from exc

    async def update_note(
        self, note_name: str, new_content: str, author_id: snowflakes.Snowflake
    ) -> None:
        await self._execute(
            "UPDATE Notes SET content = $1 WHERE name = $2 AND author_id = $3",
            new_content,
            note_name,
            author_id,
        )

    async def remove_note(
        self,
        author_id: snowflakes.Snowflake,
        /,
        strict: bool = False,
        name: str | None = None,
    ) -> None:

        sql = ["DELETE FROM Notes WHERE author_id = $1"]

        # We will remove this whether a name is passed or not since
        # Its strict.
        if strict:
            await self._execute("".join(sql), author_id)
            return

        if name is not None:
            sql += " AND name = $2"
            await self._execute("".join(sql), author_id, name)


PoolT = typing.NewType("PoolT", PgxPool)
"""A new type hint for the Pool class it self.
This only used as a type hint for injecting and type dependencies.
"""
