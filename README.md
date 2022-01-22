# Fated
A flexible and general purpose discord bot built with Hikari and Tanjun.

This is mainly used to function with Bungie's API but also have some useful commands.

## Requirements
- Python >=3.10
- PostgreSQL >=13, Used for storing muted members information and Destiny2 memberships.
- Redis > 6, Used for storing custom prefixes, mute role ids and OAuth2 tokens. _Optional_.

You'll also need to make the user and database from psql yourself.

### Running
- Configs found here `"./core/utils/config.example.py"`.
- Requirements `python -m pip install -r requirements.txt`
- Init the database `python run.py db init`
- Run redis `redis-server &`
- Run the bot `python run.py`
