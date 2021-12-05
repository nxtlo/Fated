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

import yuyo

__all__: tuple[str, ...] = ("git",)

import datetime

import hikari
import tanjun

from core.utils import cache
from core.utils import net as net_

git_group = tanjun.slash_command_group("git", "Commands related to github.")


@git_group.with_command
@tanjun.with_str_slash_option("name", "The name gitub user.")
@tanjun.as_slash_command("user", "Get information about a github user.")
async def git_user(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
    cache: cache.Memory[str, hikari.Embed] = tanjun.inject(type=cache.Memory),
) -> None:
    if cached_user := cache.get(name):
        await ctx.respond(embed=cached_user)
        return

    git = net_.Wrapper(net)
    await ctx.defer()
    try:
        user = await git.get_git_user(name)
    except net_.NotFound:
        await ctx.respond(f"User {name} was not found.")
        return

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
        cache.put(name, embed).set_expiry(datetime.timedelta(hours=6))
    await ctx.respond(embed=embed)


@git_group.with_command
@tanjun.with_str_slash_option("name", "The name gitub user.")
@tanjun.as_slash_command("repo", "Get information about a github repo.")
async def git_repo(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
    component_client: yuyo.ComponentClient = tanjun.inject(type=yuyo.ComponentClient),
) -> None:
    git = net_.Wrapper(net)

    try:
        repos = await git.get_git_repo(name)
    except net_.NotFound:
        await ctx.respond("Nothing was found.")
        return

    if repos:
        pages = iter(
            (
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
        )
        paginator = yuyo.ComponentPaginator(
            pages,
            authors=(ctx.author,),
            triggers=(
                yuyo.pagination.LEFT_DOUBLE_TRIANGLE,
                yuyo.pagination.LEFT_TRIANGLE,
                yuyo.pagination.STOP_SQUARE,
                yuyo.pagination.RIGHT_TRIANGLE,
                yuyo.pagination.RIGHT_DOUBLE_TRIANGLE,
            ),
        )
        next_repo = await paginator.get_next_entry()
        assert next_repo
        content, embed = next_repo
        msg = await ctx.respond(
            content=content, embed=embed, component=paginator, ensure_result=True
        )
        component_client.set_executor(msg, paginator)


@git_group.with_command
@tanjun.with_str_slash_option("user", "The user or org ot look up.")
@tanjun.with_str_slash_option("repo", "The repo name to look up.")
@tanjun.with_str_slash_option("release", "The release tag to get.")
@tanjun.as_slash_command(
    "release", "Fetch a github project release and returns information about it."
)
async def get_release(
    ctx: tanjun.SlashContext,
    user: str,
    repo: str,
    release: str,
    net: net_.HTTPNet = tanjun.injected(type=net_.HTTPNet),
) -> None:
    git = net_.Wrapper(net)
    try:
        embed, err = await git.git_release(user, repo, release)
    except hikari.BadRequestError:
        return None
    if embed:
        await ctx.respond(embed=embed)
        return
    elif err:
        await ctx.respond(err)
        return None


git = tanjun.Component(name="Git", strict=True).load_from_scope().make_loader()