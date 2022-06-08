 from functools import lru_cache
from discord.ext import commands
import discord
import pymongo
from motor.motor_asyncio  import AsyncIOMotorClient
from typing import Union
from bot.config.token import Tokens
from bot.data.bot_constants import Emotes
import json 
import os 

MONGODB_URI = Tokens.MONGODB_URI

@lru_cache
def get_full_path(_path: str):
    """
    Returns the full path as per the API.

    Parameters:
    --
        - `_path` - The path of the poster, etc.
    """
    if _path is None:
        return None

    with open(r"bot\data\image_config.json") as f:
        try:
            image_config = json.load(f)

        except json.decoder.JSONDecodeError as e:
            print(e)
            return None

    base_url = image_config.get("base_url")
    poster_size = image_config.get("poster_sizes")[-2]
    return f"{base_url}{poster_size}{_path}"

async def drama_update(self, bot: commands.Bot , guilds: Union[int, list], drama_id: int, drama_data: dict):
    """
    Sends Message in a channel: discord.TextChannel 

    Parameters:
    --
        - `self` - class instance.
        - `drama_id` - ID of the drama/ series.
        - `guilds` - Guild IDs which follow the aforementioned drama.    
        - `drama_data` - The dict of the drama data received from the API.
    """
    client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG
    drama_name = drama_data.get("name")
    drama_season = drama_data["seasons"][-1].get("season_number")
    drama_episode = drama_data.get("last_episode_to_air").get("episode_number")
    drama_overview = drama_data.get("last_episode_to_air").get("overview") or drama_data.get("overview")
    drama_language = (drama_data.get("origin_country")[0])
    drama_channel = drama_language + "_notify_channel"
    drama_poster = drama_data["seasons"][-1].get("poster_path")
    poster_path = get_full_path(drama_poster)

    if isinstance(guilds, int):
        solo_guild = []
        solo_guild.append(guilds)
    
    for guild_id in (solo_guild if len(solo_guild) else guilds):
        _guild = bot.get_guild(guild_id)

        

        if _guild == None:
            continue

        else:
            guild_config = await client.find_one({"guild_id": guild_id, f"dramas.{drama_language}.drama_id": drama_id}, {"_id": 0, f"dramas.{drama_language}.$": 1, "notify_channels": 1})
            
            _channel = _guild.get_channel(guild_config.get("dramas").get(drama_language)[0].get("notify_channel")) \
                or _guild.get_channel(guild_config.get("notify_channels").get(drama_channel)) \
                or _guild.get_channel(guild_config.get("notify_channels").get("default_channel"))
            if _channel != None:
                drama_members = guild_config.get("dramas").get(drama_language)[0].get("members")
                _members = ""

                for _member in drama_members:
                    _members = _members + discord.User(_member).mention
                
                embed = discord.Embed(title = f"**{drama_name}**")
                embed.set_author(name = f"{bot.user.name}", icon_url= bot.user.avatar_url)
                embed.add_field(name = "**Drama ID:**", value = str(drama_id))
                embed.add_field(name = f"**Season:**", value = str(drama_season))
                embed.add_field(name = "**Episode Released:**", value = str(drama_episode))

                if drama_overview:
                    embed.add_field(name = "**Overview:**", value = drama_overview, inline = False)
                            
                if poster_path:
                    embed.set_image(url = poster_path)

                embed.set_footer(text = f"React to the emote in the drama channels to get pinged during new episode releases.")

                try:
                    msg = await _channel.send(embed = embed, content = f"A new episode has been released! {_members}")

                except discord.HTTPException as e:
                    print(e)
                    
            
            
async def post_new_drama(bot: commands.Bot, ctx: commands.Context, drama_data: dict) -> None:
    """
    Posts the new drama added to the concerned channel: discord.TextChannel

    Parameters:
    --
        - `ctx`: the context under which the caller function was evoked.
        - `drama_dict`: The dict of the drama received from the TMDB API.
    """
    
    client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG
    drama_id = drama_data.get("id")
    drama_name = drama_data.get("name")
    drama_season = drama_data["seasons"][-1].get("season_number")
    drama_episode = drama_data.get("last_episode_to_air").get("episode_number")
    drama_language = drama_data.get("origin_country")[0]
    drama_channel = drama_language + "_drama_channel"
    drama_overview = drama_data.get("overview") # or drama_data.get("last_episode_to_air").get("overview") or
    drama_poster = drama_data["seasons"][-1].get("poster_path")
    poster_path = get_full_path(drama_poster)


    guild_config = await client.find_one({"guild_id": ctx.guild.id}, {"_id": 0, "drama_channels": 1})
    _channel = ctx.guild.get_channel(guild_config.get("drama_channels").get(drama_channel)) \
        or ctx.guild.get_channel(guild_config.get("drama_channels").get("default_channel"))
    if _channel:
        embed = discord.Embed(title = f"**{drama_name}**")
        embed.set_author(name = f"{bot.user.name}", icon_url= bot.user.avatar_url)
        embed.add_field(name = "**Drama ID:**", value = str(drama_id))
        embed.add_field(name = f"**Season:**", value = str(drama_season))
        embed.add_field(name = "**Lastest Episode:**", value = str(drama_episode))
        embed.add_field(name = "**Origin Country:**", value = str(drama_language))
        embed.set_thumbnail(url = bot.user.avatar_url)
        if drama_overview:
            embed.add_field(name = "**Overview:**", value = drama_overview, inline = False)
                    
        if poster_path:
            embed.set_image(url = poster_path)

        embed.set_footer(text = f"React to the emote below to get notified whenever a new episode of {drama_name} is released.")

        try:
            msg = await _channel.send(embed = embed)
            await msg.add_reaction(Emotes.REMINDER_EMOTE)

        except discord.HTTPException as e:
            print(e) 
            
