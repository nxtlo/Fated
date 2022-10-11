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

"""Commands related to github's API"""

from __future__ import annotations

__all__: tuple[str] = ("git",)

import alluka
import hikari
import tanjun
import yuyo

from core.std import api, boxed, cache

git_group = tanjun.slash_command_group("git", "Commands related to github.")


@git_group.with_command
@tanjun.with_str_slash_option("name", "The name gitub user name.")
@tanjun.as_slash_command("user", "Get information about a github user.")
async def git_user(
    ctx: tanjun.abc.SlashContext,
    name: str,
    git: alluka.Injected[api.AnyWrapper],
    cache: alluka.Injected[cache.Memory[str, hikari.Embed]],
) -> None:
    if cached_user := cache.get(name):
        await ctx.respond(embed=cached_user)
        return

    await ctx.defer()
    try:
        user = await git.fetch_git_user(name)
    except Exception:
        raise tanjun.CommandError(f"User {name} was not found.")

    if user is not None:
        embed = hikari.Embed(
            title=user.id, description=user.bio, timestamp=user.created_at
        )

        if user.avatar_url is not None:
            embed.set_thumbnail(user.avatar_url)
        embed.set_author(name=str(user.name), url=user.url)
        (
            embed.add_field("Followers", str(user.followers), inline=True)
            .add_field("Following", str(user.following), inline=True)
            .add_field("Public repos", str(user.public_repors), inline=True)
            .add_field("Email", str(user.email if user.email else "N/A"), inline=True)
            .add_field(
                "Location", str(user.location if user.location else "N/A"), inline=True
            )
            .add_field("User type", user.type, inline=True)
        )
        cache.put(name, embed)
    await ctx.respond(embed=embed)


@git_group.with_command
@tanjun.with_str_slash_option("name", "The repo name to search for.")
@tanjun.as_slash_command("repo", "Search for Github repos.")
async def git_repo(
    ctx: tanjun.abc.SlashContext,
    name: str,
    git: alluka.Injected[api.AnyWrapper],
    component_client: alluka.Injected[yuyo.ComponentClient],
) -> None:

    try:
        repos = await git.fetch_git_repo(name)
    except Exception:
        raise tanjun.CommandError("Nothing was found.")

    if repos:
        pages = (
            (
                hikari.UNDEFINED,
                hikari.Embed(
                    title=repo.name,
                    url=repo.url,
                    timestamp=repo.created_at,
                    description=repo.description or hikari.UNDEFINED,
                )
                .set_author(
                    name=str(repo.owner.name) or None, url=repo.owner.url or None
                )
                .set_thumbnail(repo.owner.avatar_url if repo.owner else None)
                .add_field("Stars", str(repo.stars), inline=True)
                .add_field("Forks", str(repo.forks), inline=True)
                .add_field("Is Archived", str(repo.is_archived), inline=True)
                .add_field(
                    "Stats:",
                    f"**Last push**: {repo.last_push}\n"
                    f"**Size**: {repo.size}\n"
                    f"**Is Forked**: {repo.is_forked}\n"
                    f"**Top Language**: {repo.language}\n"
                    f"**Open Issues**: {repo.open_issues}\n"
                    f"**License**: {repo.license}\n"
                    f"**Pages**: {repo.page}",
                ),
            )
            for repo in repos
        )
        await boxed.generate_component(ctx, pages, component_client)


@git_group.with_command
@tanjun.with_str_slash_option("user", "The user or org.")
@tanjun.with_str_slash_option("repo", "The repo name to look up.")
@tanjun.with_int_slash_option("limit", "Limit the returned results.", default=None)
@tanjun.as_slash_command(
    "release", "Fetch a github project releases and returns information about them."
)
async def get_release(
    ctx: tanjun.abc.SlashContext,
    user: str,
    repo: str,
    limit: int | None,
    git: alluka.Injected[api.AnyWrapper],
    component_client: alluka.Injected[yuyo.ComponentClient],
) -> None:

    try:
        embeds = await git.git_release(user, repo, limit)
    except Exception:
        raise tanjun.CommandError(f"Couldn't find any releases for {user}/{repo}.")

    await boxed.generate_component(
        ctx, ((hikari.UNDEFINED, embed) for embed in embeds), component_client
    )


git = tanjun.Component(name="Git", strict=True).load_from_scope().make_loader()
