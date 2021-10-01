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

"""Commands that makes api calls."""

from __future__ import annotations

__all__: list[str] = ["component"]

import itertools
import json
import typing

import hikari
import tanjun
from tanjun import abc as tabc

from core import client
from core.utils import consts, format, interfaces
from core.utils import net as net_

component = tanjun.Component(name="api")
git_group = component.with_slash_command(
    tanjun.SlashCommandGroup("git", "Commands related to github.")
)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The anime's name.", default=None)
@tanjun.with_bool_slash_option("random", "Get a random anime.", default=True)
@tanjun.with_str_slash_option(
    "genre",
    "The anime genre. This can be used with the random option.",
    choices=consts.iter(),
    default=consts.randomize(),
)
@tanjun.as_slash_command("anime", "Returns basic information about an anime.")
async def get_anime(
    ctx: tabc.SlashContext,
    name: str,
    random: bool | None,
    genre: str,
    net: net_.HTTPNet = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = net_.Wrapper(net)
    anime = await jian.get_anime(ctx, name, random=random, genre=genre)
    await ctx.respond(embed=anime)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The manga name")
@tanjun.as_slash_command("manga", "Returns basic information about a manga.")
async def get_manga(
    ctx: tabc.SlashContext,
    name: str,
    net: net_.HTTPNet = net_.HTTPNet(),
) -> None:
    await ctx.defer()
    jian = net_.Wrapper(net)
    manga = await jian.get_manga(ctx, name)
    await ctx.respond(embed=manga)


@component.with_slash_command
@tanjun.with_str_slash_option("name", "The name of the definition.")
@tanjun.as_slash_command("def", "Returns a definition given a name.")
async def define(
    ctx: tanjun.abc.SlashContext,
    name: str,
    net: net_.HTTPNet = net_.HTTPNet(),
) -> None:
    urban = net_.Wrapper(net)
    definition = await urban.get_definition(ctx, name)
    await ctx.respond(embed=definition)


@component.with_message_command
@tanjun.with_owner_check(halt_execution=True)
@tanjun.with_greedy_argument("url", converters=str)
@tanjun.with_option("getter", "--get", "-g", default=None)
@tanjun.with_parser
@tanjun.as_message_command("net")
async def run_net(
    ctx: tabc.MessageContext,
    url: str,
    getter: str | None,
    net: net_.HTTPNet = net_.HTTPNet(),
) -> None:
    """Make a GET http request to an api or else.

    Note: The api must be application/json type.

    TODO: make this command with options for POST and GET methods maybe?

    Parameters:
        url : str
            The api url to call.
        net : HTTPNet
            The http client we're making the request with.
        --get | -g:
            An optional key to get.
    """
    async with net as cli:
        try:
            result = await cli.request("GET", url, getter=getter)
            formatted = format.with_block(json.dumps(result, sort_keys=True), lang="json")

        except Exception as exc:
            await ctx.respond(f"```hs\n{exc}\n```")
        try:
            await ctx.respond(formatted)
        except hikari.BadRequestError as err:
            await ctx.respond(f"```hs\n{err}\n```")

@git_group.with_command
@tanjun.with_str_slash_option("name", "The name gitub user.")
@tanjun.as_slash_command("user", "Get information about a github user.")
async def git_user(
    ctx: tanjun.abc.SlashContext, name: str, net: net_.HTTPNet = net_.HTTPNet()
) -> None:

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
    await ctx.edit_initial_response(embed=embed)

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
    net: net_.HTTPNet = net_.HTTPNet(),
    bot: hikari.GatewayBot = tanjun.injected(type=client.Fated),
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
        try:
            await ctx.create_initial_response(
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
                embed=_make_embed(next(future)[0])
            )
            async with bot.stream(hikari.InteractionCreateEvent, 30) as stem:
                async for event in stem.filter(
                    lambda e: type(e.interaction) is hikari.ComponentInteraction and
                    e.interaction.user == ctx.author
                ):
                    try:
                        match event.interaction.custom_id: # type: ignore
                            case "next":
                                nxt = next(future)[1]
                                await ctx.edit_initial_response(embed=_make_embed(nxt))

                            case "prev":
                                prev = next(future)[0]
                                await ctx.edit_initial_response(embed=_make_embed(prev))

                            case _:
                                await ctx.delete_initial_response()

                    except StopIteration:
                        await ctx.respond("Reached maximum reuslts.")
                        break
        except hikari.HTTPError:
            raise

@tanjun.as_loader
def load_api(client: tanjun.Client) -> None:
    client.add_component(component.copy())
