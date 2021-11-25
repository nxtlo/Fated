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

__all__: tuple[str, ...] = ("git", "git_loader")

import asyncio
import datetime
import itertools
import typing

import hikari
import tanjun

from core.utils import cache, interfaces
from core.utils import net as net_

git_group = tanjun.slash_command_group("git", "Commands related to github.")

@git_group.with_command
@tanjun.with_str_slash_option("name", "The name gitub user.")
@tanjun.as_slash_command("user", "Get information about a github user.")
async def git_user(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
    cache: cache.Memory[str, hikari.Embed] = tanjun.inject(type=cache.Memory)
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

def _make_embed(repo: interfaces.GithubRepo) -> hikari.Embed:
    embed = (
        hikari.Embed(title=repo.name, url=repo.url, timestamp=repo.created_at)
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
        )
    )

    if repo.description:
        embed.description = repo.description
    if (owner := repo.owner) is not None:
        if owner.avatar_url:
            embed.set_thumbnail(owner.avatar_url)
        embed.set_author(name=str(owner.name), url=owner.url)
    return embed


@git_group.with_command
@tanjun.with_str_slash_option("name", "The name gitub user.")
@tanjun.as_slash_command("repo", "Get information about a github repo.")
async def git_repo(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = tanjun.inject(type=net_.HTTPNet),
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None:
    git = net_.Wrapper(net)

    try:
        repos = await git.get_git_repo(name)
    except net_.NotFound:
        await ctx.respond("Nothing was found.")
        return

    if repos is not None:

        def pairs(i: typing.Iterable[interfaces.GithubRepo]):
            a, b = itertools.tee(i)
            next(b, None)
            return zip(a, b)

        future = pairs(iter(repos))
        await ctx.defer()
        try:
            old = next(future)[0]
            await ctx.edit_initial_response(
                component=(
                    ctx.rest.build_action_row()
                    .add_button(hikari.ButtonStyle.SECONDARY, "prev")
                    .set_label("Previous")
                    .add_to_container()
                    .add_button(hikari.ButtonStyle.DANGER, "exit")
                    .set_label("Exit")
                    .add_to_container()
                    .add_button(hikari.ButtonStyle.PRIMARY, "next")
                    .set_label("Next")
                    .add_to_container()
                ),
                embed=_make_embed(old)
            )
            nxt = old
            try:
                with bot.stream(hikari.InteractionCreateEvent, 30) as stream:
                    async for event in stream.filter(("interaction.user.id", ctx.author.id)):
                        try:
                            match event.interaction.custom_id:  # type: ignore
                                case "next":
                                    old = nxt
                                    nxt = next(future)[1]
                                    await ctx.edit_initial_response(embed=_make_embed(nxt))
                                case "prev":
                                    nxt = old
                                    await ctx.edit_initial_response(embed=_make_embed(old))
                                case _:
                                    await ctx.delete_initial_response()
                        except StopIteration:
                            await ctx.respond("Reached maximum reuslts.")
                            break
            except asyncio.TimeoutError:
                await ctx.edit_initial_response("Timed out.")
                return
        except hikari.HTTPError:
            raise

@git_group.with_command
@tanjun.with_str_slash_option("user", "The user or org ot look up.")
@tanjun.with_str_slash_option("repo", "The repo name to look up.")
@tanjun.with_str_slash_option("release", "The release tag to get.")
@tanjun.as_slash_command("release", "Fetch a github project release and returns information about it.")
async def get_release(
    ctx: tanjun.SlashContext,
    user: str,
    repo: str,
    release: str,
    net: net_.HTTPNet = tanjun.injected(type=net_.HTTPNet)
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

git = tanjun.Component(name="Git", strict=True).load_from_scope()
git.metadata['about'] = "Component related to Github's API."
git_loader = git.make_loader()