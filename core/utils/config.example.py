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

"""The bot's configutation."""

from __future__ import annotations

__all__: typing.Sequence[str] = (
    "BOT_TOKEN",
    "BUNGIE_TOKEN",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "RAPID_TOKEN",
)

import typing

BOT_TOKEN: typing.Final[str] = ""
"""The bot's token."""

BUNGIE_TOKEN: typing.Final[str | None] = None
"""Bungie api key for interacting with aiobungie."""

DB_USER: typing.Final[str] = ""
"""Your database username."""

DB_PASSWORD: typing.Final[str | int] = ""
"""Your database password. this can be an int or a string."""

DB_HOST: typing.Final[str] = "127.0.0.1"
"""Your database host. default to `127.0.0.1`"""

DB_PORT: typing.Final[str | int] = 5432
"""Your database's port. Defaults to 5432."""

RAPID_TOKEN: typing.Final[str | None] = None
"""Rapid api token for urban def command."""
