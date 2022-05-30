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

__all__: tuple[str, ...] = ("PgxPool", "PartialPool")

import datetime
import logging
import pathlib
import typing

import asyncpg
import asyncpg.exceptions
from hikari import iterators

from core import models
from core.std import traits

if typing.TYPE_CHECKING:
    import collections.abc as collections

    import aiobungie
    from hikari import snowflakes

_LOG: typing.Final[logging.Logger] = logging.getLogger("fated.pool")


class ExistsError(RuntimeError):
    """A runtime error raised when either the data exists or not found."""

    def __init__(self, message: str = "") -> None:
        self.message = message

    def __repr__(self) -> str:
        return self.message

    def __str__(self) -> str:
        return self.message


class PartialPool(traits.PartialPool):
    """Partial pool implementation. A low-level wrapper around asyncpg.Pool."""

    __slots__: tuple[str, ...] = ("_pool",)

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def __call__(self) -> asyncpg.Pool:
        return await self.create_pool()

    def __await__(self) -> collections.Generator[typing.Any, None, asyncpg.Pool]:
        return self.create_pool().__await__()

    def __repr__(self) -> str:
        return f"<PartialPool>"

    @staticmethod
    def tables(path: pathlib.Path | None = None) -> str:
        p = path or pathlib.Path("core") / "psql" / "tables.sql"

        if not p.exists():
            raise FileNotFoundError(f"Tables file not found in {p!r}")

        with p.open('r') as schema:
            return schema.read()

    @classmethod
    async def create_pool(
        cls, *, build: bool = False, schema_path: pathlib.Path | None = None
    ) -> asyncpg.Pool:
        """Creates a new connection pool and create the tables if build is True."""

        from core.std import config

        config_ = config.Config.into_dotenv()

        cls._pool = pool = await asyncpg.create_pool(
            database=config_.DB_NAME,
            user=config_.DB_USER,
            password=config_.DB_PASSWORD,
            host=config_.DB_HOST,
            port=config_.DB_PORT,
        )

        if build:
            tables = cls.tables(schema_path)

            async with pool.acquire() as conn:
                try:
                    await conn.execute(tables)
                    _LOG.info("Tables build success.")

                except Exception as exc:
                    raise RuntimeError("Failed to build the database tables.") from exc

                finally:
                    await pool.release(conn)
        return pool

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

        self._pool = None
        _LOG.debug("Pool closed.")

    async def execute(
        self, sql: str, /, *args: typing.Any, timeout: float | None = None
    ) -> None:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
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

        assert self._pool is not None
        async with self._pool.acquire() as conn:
            return await conn.fetch(sql, *args, timeout=timeout)

    async def fetchrow(
        self,
        sql: str,
        /,
        *args: typing.Any,
        timeout: float | None = None,
    ) -> list[typing.Any] | collections.Mapping[str, typing.Any] | tuple[typing.Any]:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(sql, *args, timeout=timeout)

    async def fetchval(
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


@typing.final
class PgxPool(traits.PoolRunner):
    """Core database pool implementation."""

    __slots__: tuple[str, ...] = ("_pool",)

    def __init__(self) -> None:
        self._pool = PartialPool()

    def __repr__(self) -> str:
        return f"<PgxPool>"

    async def fetch_destiny_member(
        self, user_id: snowflakes.Snowflake
    ) -> models.Destiny:
        query = await self._pool.fetchrow(
            "SELECT * FROM Destiny WHERE ctx_id = $1;", user_id
        )
        if not query:
            raise ExistsError(f"User <@!{user_id}> not found.")

        return models.Destiny.into(dict(query))

    async def fetch_destiny_members(self) -> iterators.LazyIterator[models.Destiny]:
        query = await self._pool.fetch("SELECT * FROM Destiny;")
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

    async def fetch_notes(self) -> iterators.LazyIterator[models.Notes]:
        """Fetch all notes and return a lazy iterator of notes."""
        query = await self._pool.fetch("SELECT * FROM Notes;")
        if not query:
            raise ExistsError("No notes found.")

        return iterators.FlatLazyIterator(
            models.Notes.into(dict(note)) for note in query
        )

    async def fetch_notes_for(
        self, user_id: snowflakes.Snowflake
    ) -> collections.Collection[models.Notes]:
        """Fetch notes for a specific snowflake ID."""
        query = await self._pool.fetch(
            "SELECT * FROM Notes WHERE author_id = $1", user_id
        )
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
            await self._pool.execute(
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
        await self._pool.execute(
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
            await self._pool.execute("".join(sql), author_id)
            return

        if name is not None:
            sql += " AND name = $2"
            await self._pool.execute("".join(sql), author_id, name)

    # This is not used and probably will be Removed soonish.
    if typing.TYPE_CHECKING:
        async def fetch_mutes(self) -> iterators.LazyIterator[models.Mutes]:
            # query = await self._pool.fetch("SELECT * FROM Mutes;")
            # if not query:
            #     raise ExistsError("No mutes found.")

            # return iterators.FlatLazyIterator(
            #     [models.Mutes.into(dict(entry)) for entry in query]
            # )
            raise NotImplementedError

        async def put_mute(
            self,
            member_id: snowflakes.Snowflake,
            author_id: snowflakes.Snowflake,
            guild_id: snowflakes.Snowflake,
            duration: float,
            why: str,
        ) -> None:
            # try:
            #     await self._pool.execute(
            #         "INSERT INTO Mutes(member_id, guild_id, author_id, muted_at, duration, why) "
            #         "VALUES($1, $2, $3, $4, $5, $6)",
            #         int(member_id),
            #         int(guild_id),
            #         int(author_id),
            #         datetime.datetime.utcnow(),
            #         duration,
            #         why,
            #     )
            # except asyncpg.UniqueViolationError:
            #     raise ExistsError(f"Member {member_id} is already muted.")
            raise NotImplementedError

        async def remove_mute(self, user_id: snowflakes.Snowflake) -> None:
            # try:
            #     await self._pool.execute(
            #         "DELETE FROM Mutes WHERE member_id = $1", int(user_id)
            #     )
            # except asyncpg.NoDataFoundError:
            #     raise ExistsError(f"User {user_id} is not muted.")
            raise NotImplementedError
