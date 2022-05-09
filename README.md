# Fated
General purpose Discord bot built with hikari and Tanjun.

This was originally made for testing [aiobungie](https://github.com/nxtlo/aiobungie)

## Requirements
- Python >= 3.10
- PostgreSQL >=13, Used for storing muted members information and Destiny 2 memberships.
- Redis >= 6, Used for storing custom prefixes, and OAuth2 tokens. _Optional_.

You'll also need to make the user and database from psql yourself.

## Running
- Configs found [here](https://github.com/nxtlo/Fated/blob/master/core/std/config.example.py).
- Requirements `python -m pip install -r requirements.txt`
- Init the database `python run.py db init`
- Run redis `redis-server &`
- Run the bot `python run.py`
