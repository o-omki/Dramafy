import discord 
from discord.ext import commands
from bot.data.bot_constants import Emotes
from motor.motor_asyncio import AsyncIOMotorClient
from bot.config.token import Tokens

MONGODB_URI = Tokens.MONGODB_URI

class DramaPings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Adds the member who reacted to the database to get mentioned during the episode release. 
        """

        reaction_channel = self.bot.get_channel(payload.channel_id)
        
        if isinstance(reaction_channel, discord.DMChannel):
            return 

        user = self.bot.get_user(payload.user_id)
        if user == self.bot.user:
            return 

        _guild = self.bot.get_guild(payload.guild_id)   
        _member = _guild.get_member(payload.user_id)
        _message = await reaction_channel.fetch_message(payload.message_id)
        client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG

        for emote in _message.reactions:
            if str(emote.emoji) == Emotes.REMINDER_EMOTE:
                drama_id = int(_message.embeds[0].fields[0].value)
                drama_language = _message.embeds[0].fields[3].value

                _update = {
                    "$addToSet":
                    {
                        f"dramas.{drama_language}.$.members": _member.id
                    }
                }
                try:
                    await client.find_one_and_update({"guild_id": _guild.id, f"dramas.{drama_language}.drama_id": drama_id}, _update)
                
                except Exception as e:
                    print(e)
                    await _message.remove_reaction(Emotes.REMINDER_EMOTE, user)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        Removes the member who un-reacted, from the database. 
        """

        reaction_channel = self.bot.get_channel(payload.channel_id)
        if isinstance(reaction_channel, discord.DMChannel):
            return 

        user = self.bot.get_user(payload.user_id)
        if user == self.bot.user:
            return 

        _guild = self.bot.get_guild(payload.guild_id)   
        _member = _guild.get_member(payload.user_id)
        _message = await reaction_channel.fetch_message(payload.message_id)
        client = AsyncIOMotorClient(MONGODB_URI).DRAMAS.GUILD_CONFIG

        for emote in _message.reactions:
            if str(emote.emoji) == Emotes.REMINDER_EMOTE:
                drama_id = int(_message.embeds[0].fields[0].value)
                drama_language = _message.embeds[0].fields[3].value

                _update = {
                    "$pull":
                    {
                        f"dramas.{drama_language}.$.members": _member.id
                    }
                }
                try:
                    await client.find_one_and_update({"guild_id": _guild.id, f"dramas.{drama_language}.drama_id": drama_id}, _update)
                
                except Exception as e:
                    print(e)
                    await reaction_channel.send(f"Some error occured. {_member.mention} Please react to the same message and remove it once again.", delete_after = 60)

def setup(bot):
    bot.add_cog(DramaPings(bot))