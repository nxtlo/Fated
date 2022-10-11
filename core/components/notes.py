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

__all__: tuple[str, ...] = ("notes_component",)

import alluka
import hikari
import tanjun
import yuyo

from core.psql import pool as pgpool
from core.std import boxed, traits

note = tanjun.slash_command_group("note", "Create notes.")


@note.with_command
@tanjun.with_str_slash_option("content", "The note content.")
@tanjun.with_str_slash_option("name", "The note name.")
@tanjun.as_slash_command("create", "Create a new note.")
async def create_note(
    ctx: tanjun.abc.SlashContext,
    name: str,
    content: str,
    pool: alluka.Injected[traits.PoolRunner],
) -> None:

    try:
        await pool.put_note(
            name,
            content,
            ctx.author.id,
        )
    except pgpool.ExistsError as e:
        raise tanjun.CommandError(e.message)

    await ctx.respond("\U0001f44d")


@note.with_command
@tanjun.with_str_slash_option("name", "The note name to get.")
@tanjun.as_slash_command("get", "Gets a note your created.")
async def get_note(
    ctx: tanjun.abc.SlashContext,
    name: str,
    pool: alluka.Injected[traits.PoolRunner],
) -> None:

    try:
        note = await pool.fetch_notes_for(ctx.author.id, name)
    except pgpool.ExistsError as exc:
        raise tanjun.CommandError(exc.message)

    embed = hikari.Embed(title=f"{note.name}", description=note.content)
    embed.set_footer(f"ID: {note.id}")
    await ctx.respond(embed=embed)


@note.with_command
@tanjun.with_bool_slash_option(
    "strict", "If True, Then all notes will be removed.", default=False
)
@tanjun.with_str_slash_option("name", "The note name to remove.", default=None)
@tanjun.as_slash_command("remove", "Remove a note you created.")
async def delete_note(
    ctx: tanjun.abc.SlashContext,
    name: str | None,
    strict: bool,
    pool: alluka.Injected[traits.PoolRunner],
) -> None:

    try:
        await pool.remove_note(ctx.author.id, strict, name)
    except ValueError as e:
        raise tanjun.CommandError(f"{e!s}")

    await ctx.respond("\U0001f44d")


@note.with_command
@tanjun.as_slash_command("all", "Get all the notes you created.")
async def get_all_notes(
    ctx: tanjun.abc.SlashContext,
    pool: alluka.Injected[traits.PoolRunner],
    component_client: alluka.Injected[yuyo.ComponentClient],
) -> None:

    try:
        notes = await pool.fetch_notes_for(ctx.author.id)
    except pgpool.ExistsError as e:
        raise tanjun.CommandError(e.message)

    component = (
        (
            hikari.UNDEFINED,
            hikari.Embed(title=n.name, description=n.content)
            .add_field("Creator", f"<@!{n.author_id}>")
            .add_field(
                "Created at",
                f"{tanjun.conversion.from_datetime(boxed.naive_datetime(n.created_at))}",
            )
            .set_footer(f"ID: {n.id}"),
        )
        for n in notes
    )
    await boxed.generate_component(ctx, component, component_client)


@note.with_command
@tanjun.with_str_slash_option("content", "The new content to set.")
@tanjun.with_str_slash_option("name", "The note name you want to update.")
@tanjun.as_slash_command("update", "Update an existing note you created.")
async def update_note_(
    ctx: tanjun.abc.SlashContext,
    name: str,
    content: str,
    pool: alluka.Injected[traits.PoolRunner],
) -> None:
    await pool.update_note(name, content, ctx.author.id)
    await ctx.respond("\U0001f44d")


notes_component = (
    tanjun.Component(name="Notes", strict=True).load_from_scope().make_loader()
)
