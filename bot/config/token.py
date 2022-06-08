from typing import NamedTuple
import os

class Tokens(NamedTuple):
    MONGODB_URI = os.environ.get("MONGODB_URI")
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
    TMDB_APIKEY = os.environ.get("TMDB_APIKEY")