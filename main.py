from bot.cogs.admin.admin import TMDB_APIKEY
from typing import Optional
import discord 
import os 
import requests 
import asyncio
import tmdbsimple as tmdb
from discord.ext import commands
from discord.ext.commands.errors import ExtensionNotFound
from server import keep_alive
from bot.config.database_path import SQL_GUILDS
import sqlite3
from bot.config.token import Tokens
from motor.motor_asyncio import AsyncIOMotorClient
from bot.utils.commands import mongodb_helper, discord_helper
from bot.data.bot_constants import Emotes

MONGODB_URI = Tokens.MONGODB_URI
DISCORD_TOKEN = Tokens.DISCORD_TOKEN
TMDB_APIKEY = Tokens.TMDB_APIKEY

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = "d.", owner_ids = (414066242476048384, ),
   intents = intents, allowed_mentions = discord.AllowedMentions.all(),
   description = "A bot to keep you updated with latest drama releases.")

@bot.event
async def on_ready():
    bot_status = discord.Status.online
    game = discord.Game("Bingin' dramas 💞")
    await bot.change_presence(status = bot_status, activity = game)

    for root, dirs, files in os.walk(r"bot\cogs"):
        for file in files:
            if file.endswith(".py"):
                try:
                    _path = os.path.join(root,file[:-3]).replace("\\", ".")
                    bot.load_extension(_path)
                except ExtensionNotFound as e:
                    print(e)
    
    mydb = sqlite3.connect(SQL_GUILDS)
    cursor = mydb.cursor()
    cursor.execute("create table if not exists GUILD_CHECK(Guild_ID text, Drama_Channel integer, Notify_Channel integer, Guild_Removed integer)")

    # while bot.is_ready:
    #     requests.get("https://Dramas.omki.repl.co")
    #     await asyncio.sleep(60)

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        pass
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild: discord.Guild):
    mydb = sqlite3.connect(SQL_GUILDS)
    cursor = mydb.cursor()
    client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG

    guild_config = await client.find_one({"guild_id": guild.id})
    if not guild_config:
        base_config = {
            "guild_id": guild.id,
            "dramas_followed": [],
            "dramas_followed_names": {},
            "ping_roles":
            {

            },
            "drama_channels":
            {
                "default_channel": 123,
                "ko_drama_channel": 123,
            },

            "notify_channels":
            {
                "default_channel": 321,
                "ko_notify_channel": 123,
            },

            "dramas":
            {
                "KO":
                [

                ],
                "TW":
                [
    
                ],
            }
        }
        
        await client.insert_one(base_config)

    cursor.execute("select * from GUILD_CHECK where Guild_ID = ?", (guild.id,))
    result = cursor.fetchone()

    _owner = guild.owner_id
    _owner = guild.get_member(414066242476048384)
    _channel = discord.utils.find(lambda x: x.permissions_for(guild.me).send_messages, guild.text_channels)

    if result:  
        if result[3] == 1:
            if _channel:
                await _channel.send(f"""{_owner.mention}, {bot.user.mention} had been in this server in the past. Use `{bot.command_prefix}config` to review the previous configuration and change them accordingly. \
                `{bot.command_prefix}help config` for the list of commands.""")
            
            else:
                _owner.send(f"""You've received this message because I lack the permissions to send messages in **{guild.name}**.
                {bot.user.mention} had been in this server in the past. Use `{bot.command_prefix}config` to review the previous configuration and change them accordingly.
                `{bot.command_prefix}help config` for the list of commands.""")
                print("dm sent")


    else:
        cursor.execute("insert into GUILD_CHECK values(?, ?, ?, ?)", (guild.id, 0, 0, 0))  
        
        if _channel:
            await _channel.send(f"""{_owner.mention}, use `{bot.command_prefix}config` to view the bare minimun configuration that need to be set to avail the bot's full functionality.
            `{bot.command_prefix}help config` for the list of commands.""")
                
        else:
            _owner.send(f"""You've received this message because I lack the permissions to send messages in **{guild.name}**. Use `{bot.command_prefix}config` to view the bare minimun configuration that need to be set to avail the bot's full functionality.
            `{bot.command_prefix}help config` for the list of commands.""")
            print("dm sent")
    

    mydb.commit()
    cursor.close()
    mydb.close()   



@bot.command()
@commands.guild_only()
@commands.has_guild_permissions(administrator = True)
async def drama(ctx, drama_id: int, _channel: Optional[discord.TextChannel] = None):
        """
        Register a Drama/Series for episode releases.

        Usage:
            `[p]add drama <drama_id> <notify_channel>`
        
        **Arguments**
            - `<drama_id>` - The ID of the drama to get the episodes' updates for.
            - `<notify_channel>` - The channel to post the updates for this drama. If omitted, defaults to the general notify channel.
        """

        if not isinstance(drama_id, int):
            raise commands.BadArgument
            
        client = AsyncIOMotorClient(MONGODB_URI).DRAMAS
        tmdb.API_KEY = TMDB_APIKEY

        try:
            show_data = tmdb.TV(drama_id).info()

        except Exception as e :
            print(e)
            await ctx.channel.send(f"Drama not found! Use the correct ID. Use `{bot.command_prefix}search <series name>` to lookup for one.")

        else:
            _notify_channel = None
            if _channel.id is not None:
                _notify_channel = _channel.id

            update_dict = {
                "drama_id": drama_id,
                "notify_channel":  _notify_channel,                                 #_channel.id if _channel else None,
                "language": (show_data.get("origin_country")[0])
            }
            db_drama = await client.EPISODE_TRACK.find_one({"drama_id": drama_id})

            if db_drama is None:
                if "episode_run_time" not in show_data:
                    return await ctx.send(f"Failed! {show_data['title']} is a movie. For movies, use `{bot.command_prefix}add movie <ID>`")

                else:
                    if show_data["status"] == "Ended":
                        return await ctx.send(f"**{show_data['name']}** not added as it concluded on {show_data['last_air_date']}")
                    
                    else:
                
                        data = {"drama_id": drama_id, \
                            "name": show_data.get("name"),
                            "language": (show_data.get("origin_country")[0]),
                            "drama_overview": show_data.get("overview"),
                            "season": show_data["seasons"][-1].get("season_number"), 
                            "dates": {
                                "last_episode": show_data.get("last_air_date"), 
                                "next_episode": show_data.get("next_episode_to_air").get("air_date")
                                }, 
                            "episode": {
                                "last_episode": show_data.get("last_episode_to_air").get("episode_number"), 
                                "next_episode": show_data.get("next_episode_to_air").get("episode_number")
                                }, 
                            "poster": show_data["seasons"][-1].get("poster_path"),
                            "overview": show_data.get("last_episode_to_air").get("overview"),
                            "guilds": [ctx.guild.id, ]
                            }

                        try:
                            await client.EPISODE_TRACK.insert_one(data)

                        except Exception:
                            return await ctx.send("Failed! Try again later.")
                        
                        else:
                            await mongodb_helper.mongodb_add_drama(client.GUILD_CONFIG, ctx.guild.id, update_dict)
                            await ctx.message.add_reaction(Emotes.CONFIRMATION_EMOTE)

                            try:
                                await discord_helper.post_new_drama(bot, ctx, show_data)

                            except Exception as e:
                                await ctx.channel.send(e)

            
            else:
                if ctx.guild.id not in db_drama.get("guilds"):
                    try:
                        await client.EPISODE_TRACK.update_one({"drama_id": drama_id}, {"$addToSet": {"guilds": ctx.guild.id}})
                        await mongodb_helper.mongodb_add_drama(client.GUILD_CONFIG, ctx.guild.id, update_dict)


                    except Exception:
                        return await ctx.send("Failed! Try again later.")
                    
                    else:
                        await ctx.message.add_reaction(Emotes.CONFIRMATION_EMOTE)
                        await discord_helper.post_new_drama(bot, ctx, show_data)
                else:
                    await ctx.channel.send("Failed. The drama's already linked.")
                    await ctx.message.add_reaction(Emotes.NOTALLOWED_EMOTE)

               
@drama.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send(f"{error.param.name} is missing. Use `[p]help drama`.")
    if isinstance(error, commands.MissingPermissions):
        await ctx.channel.send(f"`{ctx.author.name}`, you're missing the Administrator permission.")
    if isinstance(error, commands.BadArgument):
        await ctx.channel.send(f"Usage: `[p]add drama <drama_id> <TextChannel>(optional)`")



keep_alive()
bot.run(DISCORD_TOKEN, bot = True, reconnect = True)