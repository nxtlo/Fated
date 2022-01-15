/*
MIT License

Copyright (c) 2021 - Present nxtlo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. */

CREATE TABLE IF NOT EXISTS Destiny (
    ctx_id          BIGINT PRIMARY KEY NOT NULL,
    membership_id   BIGINT NOT NULL UNIQUE,
    name            TEXT,
    code            SMALLINT NOT NULL UNIQUE CHECK (code > 1),
    membership_type VARCHAR(6)
);

CREATE TABLE IF NOT EXISTS Mutes (
    member_id   BIGINT PRIMARY KEY NOT NULL,
    guild_id    BIGINT NOT NULL,
    author_id   BIGINT NOT NULL,
    muted_at    TIMESTAMP NOT NULL,
    why         TEXT,
    duration    BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS Notes (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    content     TEXT NOT NULL,
    author_id   BIGINT NOT NULL,
    guild_id    BIGINT NOT NULL,
    created_at  TIMESTAMP NOT NULL
);
