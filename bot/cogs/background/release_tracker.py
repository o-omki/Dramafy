from typing import List
from discord.ext import commands, tasks
import pymongo
import datetime
import tmdbsimple as tmdb
from bot.config.token import Tokens
from bot.utils.commands import discord_helper, async_mongodb
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = Tokens.MONGODB_URI
TMDB_APIKEY = Tokens.TMDB_APIKEY

class ReleaseTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_new_episode_releases.start()

    def cog_unload(self):
        self.check_new_episode_releases.cancel()
    @tasks.loop(minutes = 15.0)
    async def check_new_episode_releases(self):
        """
        Checks for the release of new episodes for dramas and series.
        """
        
        client = AsyncIOMotorClient(MONGODB_URI).DRAMAS
        tmdb.API_KEY = TMDB_APIKEY

        concluded_dramas = set()
        doc_count = await async_mongodb.mongodb_count_documents(client.EPISODE_TRACK, {})
        if doc_count != 0:
            drama_list = await async_mongodb.mongodb_find(client.EPISODE_TRACK, get_list = True, length = doc_count)

            for drama in drama_list:
                drama_id = drama["drama_id"]
                drama_guilds = drama["guilds"]
                tmdb_drama_data = tmdb.TV(drama_id).info()

                if tmdb_drama_data["status"] == "Ended":
                    concluded_dramas.add(drama_id)
                    continue
                
                db_last_episode = drama.get("dates").get("last_episode")
                tmdb_last_episode = tmdb_drama_data.get("last_air_date")

                if tmdb_last_episode == None or db_last_episode == tmdb_last_episode:
                    continue 
 
                else:
                    tmdb_last_episode = datetime.datetime.strptime(tmdb_last_episode, "%Y-%m-%d")

                    if db_last_episode == None:
                        discord_helper.drama_update(self, self.bot, drama_guilds, drama_id, tmdb_drama_data)
                        await async_mongodb.mongodb_post_release_update(client.EPISODE_TRACK, {"drama_id": drama_id}, tmdb_drama_data)
                    
                    else:
                        db_last_episode = datetime.datetime.strptime(db_last_episode, "%Y-%m-%d")

                        if tmdb_last_episode > db_last_episode:
                            await discord_helper.drama_update(self, self.bot, drama_guilds, drama_id, tmdb_drama_data)
                            await async_mongodb.mongodb_post_release_update(client.EPISODE_TRACK, {"drama_id": drama_id}, tmdb_drama_data)
            
            await self.remove_concluded_dramas(concluded_dramas)
            
    @check_new_episode_releases.before_loop
    async def wait_for_bot(self):
        await self.bot.wait_until_ready()
            
    # @check_new_episode_releases.after_invoke
    async def remove_concluded_dramas(self, concluded_dramas):
        """
        Removes the dramas which have concluded from the database.
        """

        client = AsyncIOMotorClient(MONGODB_URI).DRAMAS

        for drama in concluded_dramas:
            deleted_drama = await client.EPISODE_TRACK.find_one_and_delete({"drama_id": drama}, {"_id": 0, "guilds": 1, "language": 1})
            if len(deleted_drama["guilds"]):
                try:
                    await client.GUILD_CONFIG.update_many({"guild_id": {"$in": deleted_drama.get("guilds")}}, 
                    {
                        "$pull": {
                            "dramas_followed": drama,
                            f"dramas.{deleted_drama['language']}": {"drama_id": drama}
                        }
                    })
                
                except Exception:
                    pass

                else:
                    concluded_dramas.remove(drama)
                    

def setup(bot):
    bot.add_cog(ReleaseTracker(bot))


    

            

                        