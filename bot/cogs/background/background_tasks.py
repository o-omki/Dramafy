from bot.cogs.admin.admin import TMDB_APIKEY
from discord.ext import commands, tasks
import json 
import tmdbsimple as tmdb
from bot.config.token import Tokens

class BackgroundTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.get_image_config.start()
    
    def cog_unload(self):
        self.get_image_config.cancel()
    
    @tasks.loop(hours = 3.0)
    async def get_image_config(self):
        tmdb.API_KEY = Tokens.TMDB_APIKEY
        try:
            response = tmdb.Configuration().info()["images"]
        except Exception:
            self.get_image_config.restart()

        config_data = {
            "base_url": response["secure_base_url"],
            "poster_sizes": response["poster_sizes"],
            "profile_sizes": response["profile_sizes"],
            "still_sizes": response["still_sizes"]
        }

        with open(r"bot\data\image_config.json", "w") as f:
            f.write(json.dumps(config_data, indent = 4))
        
    @get_image_config.before_loop
    async def wait_for_bot(self):
        await self.bot.wait_until_ready()
        
def setup(bot):
    bot.add_cog(BackgroundTasks(bot))