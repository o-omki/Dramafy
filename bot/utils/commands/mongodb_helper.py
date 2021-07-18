from motor.motor_asyncio import AsyncIOMotorClient

async def mongodb_add_drama(client: AsyncIOMotorClient, guild_id: int,  update_data: dict):
    """
    Adds a drama to the guild's data.

    Parameters:
    --
        - `client`: Instance of a pymongo MongoClient.
        - `guild_id`: The guild's ID.
        - `update_data`: The drama data to be added.
    """

    guild_config = await client.find_one({"guild_id": guild_id})

    drama_language = update_data.pop("language")
    update_data["members"] = []

    if drama_language in guild_config["dramas"].keys():
        guild_config["dramas"][drama_language].append(update_data)
    
    else:
        guild_config["dramas"][drama_language] = [update_data,]
    
    guild_config["dramas_followed"].append(update_data.get("drama_id"))

    await client.find_one_and_replace({"guild_id": guild_id}, guild_config)

async def mongodb_remove_drama(client: AsyncIOMotorClient, guild_id: int, update_data: dict):
    """
    Deletes a drama to the guild's data.

    Parameters:
    --
        - `client`: Instance of a pymongo MongoClient.
        - `guild_id`: The guild's ID.
        - `update_data`: The drama data to be deleted.
    """

    guild_config = await client.find_one({"guild_id": guild_id})
    drama_language = update_data.pop("language")
    drama_category = guild_config["dramas"].get(drama_language)
    deletion_index = [index for (index, _) in enumerate(drama_category) if _["drama_id"] == update_data["drama_id"]][0]
    del guild_config["dramas"][drama_language][deletion_index]
    guild_config["dramas_followed"].remove(update_data["drama_id"])

    await client.find_one_and_replace({"guild_id": guild_id}, guild_config)




