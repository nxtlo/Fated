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

"""API wrapper model."""

from __future__ import annotations

__all__: tuple[str] = ("AnyWrapper",)

import typing

import hikari
import tanjun
from aiobungie.internal import time
from hikari.internal.time import (
    fast_iso8601_datetime_string_to_datetime as fast_datetime,
)

from .. import models
from . import boxed, net

if typing.TYPE_CHECKING:
    import collections.abc as collections
    import datetime

# We spawn a new client for each individual.
def _spawn_client() -> net.HTTPNet:
    return net.HTTPNet()


def _build_anime_embed(
    anime_payload: net.data_binding.JSONObject, date_key: str
) -> hikari.Embed:

    start_date: hikari.UndefinedOr[str] = hikari.UNDEFINED
    if raw_start_date := anime_payload.get(date_key):
        start_date = tanjun.conversion.from_datetime(
            boxed.naive_datetime(fast_datetime(raw_start_date)),  # type: ignore
            style="R",
        )

    end_date: hikari.UndefinedOr[str] = hikari.UNDEFINED
    if raw_end_date := anime_payload.get("end_date"):
        end_date = tanjun.conversion.from_datetime(
            boxed.naive_datetime(fast_datetime(raw_end_date)),  # type: ignore
            style="R",
        )

    return (
        hikari.Embed(
            title=anime_payload.get("title", hikari.UNDEFINED),
            description=anime_payload.get("synopsis", hikari.UNDEFINED),
        )
        .set_footer(
            text=", ".join(
                list(map(lambda tag: tag["name"], anime_payload.get("genres", {})))
            )
        )
        .set_author(url=anime_payload.get("url", str(hikari.UNDEFINED)))
        .set_image(anime_payload.get("image_url", None))
        .add_field(
            "Episodes", anime_payload.get("episodes", hikari.UNDEFINED), inline=True
        )
        .add_field("Score", anime_payload.get("score", hikari.UNDEFINED), inline=True)
        .add_field("Aired at", str(start_date), inline=True)
        .add_field("Finished at", str(end_date), inline=True)
        .add_field(
            "Community members",
            anime_payload.get("members", hikari.UNDEFINED),
            inline=True,
        )
        .add_field(
            "Being aired",
            anime_payload.get("airing", hikari.UNDEFINED),
            inline=True,
        )
    )


def _set_repo_owner_attrs(payload: dict[str, typing.Any]) -> models.GithubUser:
    user: dict[str, typing.Any] = payload
    created_at: datetime.datetime | None = None

    if raw_created := user.get("created_at"):
        created_at = fast_datetime(raw_created)  # type: ignore

    return models.GithubUser(
        name=user.get("login", hikari.UNDEFINED),
        id=user["id"],
        url=user["html_url"],
        repos_url=user["repos_url"],
        public_repors=user.get("public_repos", hikari.UNDEFINED),
        avatar_url=user.get("avatar_url", None),
        email=user.get("email", None),
        type=user["type"],
        bio=user.get("bio", hikari.UNDEFINED),
        created_at=created_at,
        location=user.get("location", None),
        followers=user.get("followers", hikari.UNDEFINED),
        following=user.get("following", hikari.UNDEFINED),
    )


def _set_repo_attrs(
    payload: dict[str, list[dict[str, typing.Any]]]
) -> collections.Sequence[models.GithubRepo]:
    repos: list[models.GithubRepo] = []

    for repo in payload["items"]:
        license_name = "UNDEFINED"

        if repo_license := repo.get("license"):
            license_name = repo_license["name"]

        repo_obj = models.GithubRepo(
            id=repo["id"],
            name=repo["full_name"],
            description=repo.get("description", None),
            url=repo["html_url"],
            is_forked=repo["fork"],
            created_at=time.clean_date(repo["created_at"]).astimezone(),
            last_push=fast_datetime(repo["pushed_at"]),  # type: ignore
            page=repo.get("homepage", None),
            size=repo["size"],
            license=license_name,
            is_archived=repo["archived"],
            forks=repo["forks_count"],
            open_issues=repo["open_issues_count"],
            stars=repo["stargazers_count"],
            language=repo.get("language", hikari.UNDEFINED),
            owner=_set_repo_owner_attrs(repo.get("owner", None)),
        )
        repos.append(repo_obj)

    return repos


def _make_git_releases(
    repo: net.data_binding.JSONObject, user: str, repo_name: str
) -> hikari.Embed:
    embed = hikari.Embed()
    repo_author = _set_repo_owner_attrs(repo["author"])
    embed.set_author(
        name=f'{repo["tag_name"]} | {repo["name"]}',
        url=f'https://github.com/{user}/{repo_name}/releases/tag/{repo["tag_name"]}',
        icon=repo_author.avatar_url,
    )

    if (body := repo.get("body", hikari.UNDEFINED)) and len(str(body)) <= 4096:
        embed.description = boxed.with_block(body, lang="md")

    embed.timestamp = fast_datetime(repo["published_at"])  # type: ignore
    (
        embed.add_field(
            "Information",
            f"ID: {repo['id']}\n"
            f"Prerelease: {repo['prerelease']}\n"
            f"Drafted: {repo['draft']}\n"
            f"Branch: {repo['target_commitish']}\n"
            f"[Download zipball]({repo['zipball_url']})\n"
            f"[Download tarball]({repo['tarball_url']})",
        ).add_field(
            "Owner",
            f"Name: [{repo_author.name}]({repo_author.url})\n"
            f"ID: {repo_author.id}\n"
            f"Type: {repo_author.type}",
        )
    )
    return embed


@typing.final
class AnyWrapper:
    """Wrapper around different APIs."""

    def __init__(self) -> None:
        super().__init__()

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"

    async def fetch_anime(
        self,
        name: str | None = None,
        *,
        random: bool | None = None,
        genre: str,
    ) -> hikari.Embed | collections.Generator[hikari.Embed, None, None] | None:

        async with _spawn_client() as cli:

            if random and name is None:
                # This is True by default in case the name is None.
                path = f"{boxed.ENDPOINT['anime']}/genre/anime/{boxed.GENRES[genre]}/1"
            else:
                path = f'{boxed.ENDPOINT["anime"]}/search/anime?q={str(name).lower()}/Zero&page=1&limit=1'

            # This kinda brain fuck but it will raise KeyError
            # error if we don't check before we make the actual request.
            if genre is not None and random and name is None:
                getter = "anime"
                start = "airing_start"
            else:
                getter = "results"
                start = "start_date"

            if not (
                raw_anime := await cli.request(
                    "GET",
                    path,
                    getter=getter,
                )
            ):
                return None

            if isinstance(raw_anime, dict):
                return _build_anime_embed(raw_anime, start)
            else:
                assert isinstance(
                    raw_anime, list
                ), f"Expected a list or dict anime but got {type(raw_anime).__name__}"
                return (_build_anime_embed(anime, start) for anime in raw_anime)

    async def fetch_manga(
        self, name: str, /
    ) -> collections.Generator[hikari.Embed, None, None] | None:

        async with _spawn_client() as cli:
            if not (
                raw_mangas := await cli.request(
                    "GET",
                    f'{boxed.ENDPOINT["anime"]}/search/manga?q={name}/Zero&page=1&limit=1',
                    getter="results",
                )
            ):
                return None

            assert isinstance(raw_mangas, list)

            embeds = (
                hikari.Embed(
                    colour=boxed.COLOR["invis"],
                    description=manga.get("synopsis", hikari.UNDEFINED),
                )
                .set_author(
                    url=manga.get("url", str(hikari.UNDEFINED)),
                    name=manga.get("title", hikari.UNDEFINED),
                )
                .set_image(manga.get("image_url", None))
                .add_field(
                    "Published at",
                    str(tanjun.conversion.from_datetime(fast_datetime(manga.get("start_date")), style="R") or hikari.UNDEFINED),  # type: ignore
                )
                .add_field(
                    "Finished at",
                    str(tanjun.conversion.from_datetime(fast_datetime(manga.get("end_date")), style="R") or hikari.UNDEFINED),  # type: ignore
                )
                .add_field("Chapters", manga.get("chapters", hikari.UNDEFINED))
                .add_field("Volumes", manga.get("volumes", hikari.UNDEFINED))
                .add_field("Type", manga.get("type", hikari.UNDEFINED))
                .add_field("Score", manga.get("score", hikari.UNDEFINED))
                .add_field("Community members", manga.get("members", hikari.UNDEFINED))
                .add_field("Being published", manga.get("publishing", hikari.UNDEFINED))
                for manga in raw_mangas
            )
            return embeds

    async def fetch_definitions(
        self, name: str
    ) -> collections.Generator[hikari.Embed, None, None]:

        async with _spawn_client() as cli:
            resp = (
                await cli.request(
                    "GET",
                    boxed.ENDPOINT["urban"],
                    params={"term": name.lower()},
                    getter="list",
                )
                or []
            )

            if not resp:
                raise tanjun.CommandError(f"Couldn't find definition about `{name}`")

            assert isinstance(resp, list)

            def _replace(s: str) -> str:
                return s.replace("]", "").replace("[", "")

            embeds = (
                hikari.Embed(
                    colour=boxed.COLOR["invis"],
                    title=f"Definition for {name}",
                    description=_replace(defn.get("definition", hikari.UNDEFINED)),
                    timestamp=fast_datetime(defn.get("written_on")) or None,  # type: ignore
                )
                .add_field("Example", _replace(defn.get("example", hikari.UNDEFINED)))
                .set_footer(
                    text=f"\U0001f44d {defn.get('thumbs_up', 0)} - \U0001f44e {defn.get('thumb_down', 0)}"
                )
                .set_author(
                    name=defn.get("author"), url=defn.get(defn.get("permalink"))
                )
                for defn in resp
            )
        return embeds

    async def fetch_git_user(self, name: str, /) -> models.GithubUser | None:
        async with _spawn_client() as cli:
            if raw_user := await cli.request(
                "GET", f'{boxed.ENDPOINT["git"]["user"]}/{name}'
            ):
                assert isinstance(raw_user, dict)
                return _set_repo_owner_attrs(raw_user)

    async def fetch_git_repo(
        self, name: str
    ) -> collections.Sequence[models.GithubRepo] | None:
        async with _spawn_client() as cli:
            if raw_repo := await cli.request(
                "GET", boxed.ENDPOINT["git"]["repo"].format(name)
            ):
                assert isinstance(raw_repo, dict)
                return _set_repo_attrs(raw_repo)

    # Can we cache this and expire after x hours?
    async def git_release(
        self, user: str, repo_name: str, limit: int | None = None
    ) -> collections.Generator[hikari.Embed, None, None]:
        async with _spawn_client() as cli:
            repos = await cli.request(
                "GET", f"https://api.github.com/repos/{user}/{repo_name}/releases"
            )
            assert isinstance(repos, list)
            return (_make_git_releases(repo, user, repo_name) for repo in repos[:limit])
