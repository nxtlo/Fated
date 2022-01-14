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

CREATE TABLE IF NOT EXISTS destiny (
    ctx_id    BIGINT PRIMARY KEY NOT NULL,
    bungie_id BIGINT NOT NULL,
    name      TEXT,
    code      BIGINT,
    memtype   VARCHAR(6)
);

CREATE TABLE IF NOT EXISTS mutes (
    member_id   BIGINT PRIMARY KEY NOT NULL,
    guild_id    BIGINT,
    author_id   BIGINT NOT NULL,
    muted_at    TIMESTAMP NOT NULL,
    why         TEXT,
    duration    BIGINT
);

/* We don't need this since we're using redis for the prefixes. */

/*CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    prefix VARCHAR(5)
); */
