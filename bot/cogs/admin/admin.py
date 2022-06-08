from typing import Optional
from discord import guild
from discord.ext import commands
import discord
from discord.ext.commands.converter import TextChannelConverter
import requests
import pymongo
import tmdbsimple as tmdb
from bot.data.bot_constants import Emotes
from bot.config.token import Tokens
from bot.utils.commands import async_mongodb, discord_helper, mongodb_helper
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = Tokens.MONGODB_URI
TMDB_APIKEY = Tokens.TMDB_APIKEY

class AdministratorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.has_guild_permissions(administrator = True)
    @commands.group(name = "add", invoke_without_command = True)
    async def add_show(self, ctx):
        """
        Base command to add dramas/ movies the guild's tracking list.
        """
        
        return await ctx.send(f"Usage: `{self.bot.command_prefix}add <drama/movie> <ID> <channel(optional)>`")
    
    @add_show.command(usage = "<drama_id> <notify_channel>(optional)")
    async def drama(self, ctx, drama_id: int, _channel: Optional[discord.TextChannel] = None):
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
            await ctx.channel.send(f"Drama not found! Use the correct ID. Use `{self.bot.command_prefix}search <series name>` to lookup for one.")

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
                    return await ctx.send(f"Failed! {show_data['title']} is a movie. For movies, use `{self.bot.command_prefix}add movie <ID>`")

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
                                await discord_helper.post_new_drama(self.bot, ctx, show_data)

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
                        await discord_helper.post_new_drama(self.bot, ctx, show_data)
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


    @commands.guild_only()
    @commands.has_permissions(administrator = True)
    @commands.group(name = "search", invoke_without_command = True)
    async def search_command(self, ctx):
        """
        Base command to search for drama or movie.
        """
        pass

    @search_command.command(usage = "<name>")
    async def drama(self, ctx, *, drama_name: str):
        """
        To search for a drama.

        Parameters:
        --
            - `drama_name`: The name of the drama to search for.
        """
        if not isinstance(drama_name, str):
            raise ValueError
        
        tmdb.API_KEY = TMDB_APIKEY
        search = tmdb.Search().tv(query = drama_name)

    @commands.guild_only()
    @commands.has_permissions(administrator = True)
    @commands.group(name = "config", invoke_without_command = True)
    async def guild_config(self, ctx):
        """
        To see the guild's configuration.
        """
        client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG
        guild_config = await async_mongodb.mongodb_find_one(client, _filter = {"guild_id": ctx.guild.id})

        num_of_dramas_followed = len(guild_config.get("dramas_followed"))
        default_drama_channel = "NOT SET!" if guild_config.get("drama_channels").get("default_channel") == None else self.bot.get_channel(guild_config.get("drama_channels").get("default_channel")).mention
        default_notify_channel = "NOT SET!" if guild_config.get("notify_channels").get("default_channel") == None else self.bot.get_channel(guild_config.get("notify_channels").get("default_channel")).mention
        drama_channels = ""
        notify_channels = ""
        dramas_followed = ""
        for _channel in guild_config.get("drama_channels").values():
            if _channel != "NOT SET!":
                try:
                    drama_channels += f" {self.bot.get_channel(_channel).mention}"
                
                except Exception as e:
                    drama_channels += f" <#{_channel}>"
        
        for _channel in guild_config.get("notify_channels").values():
            if _channel != "NOT SET!":
                try:
                    notify_channels += f" {self.bot.get_channel(_channel).mention}"
                
                except Exception:
                    notify_channels += f" <#{_channel}>"
        
        for (drama_id, drama_name) in guild_config.get("dramas_followed_names").items():
            dramas_followed += f" ; {drama_name}: ({drama_id})"
        
        config_text = f"""
        Minimum Channels which must be set: 

        Default Drama Channel: {default_drama_channel}
        Default Notify Channel: {default_notify_channel}
        
        *the above channels must be set to run the bot.*
        
        Other Configuration:

        Number of Dramas being followed: {num_of_dramas_followed}
        Dramas Being Followed: {dramas_followed}
        Drama Channels: {drama_channels}
        Notify Channels: {notify_channels}

        *goes to the embed footer: Use {self.bot.command_prefix}help config
        """
        
        await ctx.send(config_text)

    def get_language_code(self, country_name: str):
        """
        Returns the ISO 639-1 tag for a language.

        Parameters:
        --
            - `country_name`: The name of the country.
        """

        country_name = country_name.lower()
        language_dict = {
            "KR": ["korean", "korea", "kr"],
            "TW": ["taiwan", "taiwanese", "tw"],
            "CN": ["chinese", "china", "cn"],
            "JP": ["japanese", "japan", "jp"],
            "TH": ["thailand", "thai", "th"],
            "SG": ["singapore", "singa", "sg", "singaporean"],
            "PH": ["philippines", "filipino", "ph"]
        }

        for code, language in language_dict.items():
            if country_name in language:
                return code

        return None
    
    def check_channel_permissions(self, ctx: commands.Context, _channel: discord.TextChannel):
        """
        Checks if the bot has the necessary permissions in the channel.

        Parameters:
        --
            - `ctx`: the context under which the caller was invoked.
            - `_channel`: A channel : discord.TextChannel.
        """

        required_permissions = (
            discord.Permissions.add_reactions,
            discord.Permissions.send_messages, 
            discord.Permissions.read_message_history,
            discord.Permissions.external_emojis
        )

        for perm in required_permissions:
            if not _channel.permissions_for(ctx.guild.me).send_messages and _channel.permissions_for(ctx.guild.me).add_reactions and _channel.permissions_for(ctx.guild.me).read_message_history and _channel.permissions_for(ctx.guild.me).external_emojis:
                return False
        
        return True

    @guild_config.command(name = "setdrama", aliases = ("setd", "sd", "sdrama"), usage = "<channel> <language>(optional)")
    async def set_drama(self, ctx, _channel: commands.TextChannelConverter,  language: str = None):
        """
        Sets the channel to which the new dramas added for the given language get posted.

        Parameters:
        --
            - `_channel`: The text channel where the drama info would be posted.
            - `language`(optional): The language of the dramas to be posted in this channel. If omitted, the default channel would be changed.
        """

        if language != None:
            if not isinstance(language, str):
                raise commands.BadArgument

            else:
                language_code = self.get_language_code(language)
                if language_code == None:
                    return await ctx.channel.send("Language not found! Enter the correct language.")
            
        if not self.check_channel_permissions(ctx, _channel):
            return await ctx.channel.send(f"Failed. Ensure that I have the permissions to send messages, add rections and read message history in {_channel.mention}.")
        
        else:
            client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG
            drama_channel = language_code + "_drama_channel" if language != None else "default_channel"
            try:
                await client.find_one_and_update({"guild_id": ctx.guild.id}, {"$set": {f"drama_channels.{drama_channel}": _channel.id}})
            
            except Exception as e:
                print(e)
                return await ctx.channel.send("Failed. Try again later!")
            
            else:
                return await ctx.message.add_reaction(Emotes.CONFIRMATION_EMOTE)
        
    @guild_config.command(name = "setnotify", aliases = ("setn", "sn", "snotify", "setnotif"), usage = "<channel> <language>(optional)")
    async def set_notify(self, ctx, _channel: commands.TextChannelConverter, language: str = None):
        """
        Sets the channel to which the new episode releases for the language specified would be posted to. Gets overridden by individual drama channels if configured.

        Parameters:
        --
            - `_channel`: The text channel where the episode release details would be posted.
            - `language`: The language of the dramas to be posted in this channel. If omitted the default notify channel would be changed.
        """

        if language != None:
            if not isinstance(language, str):
                raise commands.BadArgument

            else:
                language_code = self.get_language_code(language)
                if language_code == None:
                    return await ctx.channel.send("Language not found! Enter the correct language.")

        if not self.check_channel_permissions(ctx, _channel):
            return await ctx.channel.send(f"Failed. Ensure that I have the permissions to send messages, add rections and read message history in {_channel.mention}.")
        
        else:
            client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG
            drama_channel = language_code + "_notify_channel" if language != None else "default_channel"

            try:
                await client.find_one_and_update({"guild_id": ctx.guild.id}, {"$set": {f"notify_channels.{drama_channel}": _channel.id}})
            
            except Exception as e:
                print(e)
                return await ctx.channel.send("Failed. Try again later!")
            
            else:
                return await ctx.message.add_reaction(Emotes.CONFIRMATION_EMOTE)

def setup(bot):
    bot.add_cog(AdministratorCommands(bot))