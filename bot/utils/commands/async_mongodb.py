from typing import Optional, Any, Dict
from bot.config.token import Tokens

async def mongodb_find_one(client, *args, _filter: Dict = None , **kwargs):
    """
    To get a single document from MongoDB asynchronously.

    Parameters:
    --
        - `client`: MotorClient instance.
        - `_filter`(optional): A dict specifying the query.
        - `*args`(optional): Other positional arguments.
        - `**kwargs`(optional): Other keyword arguments.
    """

    if _filter == None:
        _filter = {}

    return await client.find_one(_filter, *args, **kwargs)

async def mongodb_count_documents(client, _filter: Dict, **kwargs) -> Any:
    """
    To count the number of documents in the collection asynchronously.

    Parameters:
    --
        - `client`: MotorClient instance.
        - `_filter`: A dict specifying the query. Can be an empty document to count all the documents
        - `**kwargs`(optional): Other keyword arguments.
    """

    return await client.count_documents(_filter, **kwargs)

async def mongodb_find(client, *args, get_list = False, length = None,  **kwargs):
    """
    Return a MotorCursor instance (asynchronous)

    Parameters:
    --
        - `client`: MotorClient instance.
        - `get_list`: To get a list containing all the documents.
        - `length`: The number of documents to be in the list.
        - `*args`(optional): Other positional arguments.
        - `**kwargs`(optional): Other keyword arguments.
    """
    
    cursor = client.find(*args, **kwargs)
    if get_list:
        return await cursor.to_list(length = length)

    return cursor 

async def mongodb_update_one(client, _filter, _update, array_filters = None):
    """
    Update a document asynchronously.

    Parameters:
    --
        - `client`: MotorClient instance.
        - `_filter`: A query to match the document to be updated.
        - `_update`: The modification to made to the document.
    """
    pass

async def mongodb_post_release_update(client, _filter, drama_data):
    """
    Finds and updates a document asynchronously.

    Parameters:
    --
        - `client` - MotorClient instance.
        - `_filter` - A query to match the document to be updated.
        - `drama_data` - The dict retrieved from the API.
    """

    last_ep = drama_data.get("last_episode_to_air")
    overview = None
    next_date = None
    last_ep = None
    next_ep = drama_data.get("next_episode_to_air")

    if last_ep is not None:
        last_ep = drama_data.get("last_episode_to_air").get("episode_number")
        overview = drama_data.get("last_episode_to_air").get("overview")
    
    if next_ep is not None:
        next_ep = drama_data.get("next_episode_to_air").get("episode_number")
        next_date = drama_data.get("next_episode_to_air").get("air_date")
    _update = {
        "$set": 
        {
            "season": drama_data["seasons"][-1].get("season_number"),
            "dates": 
            {
                "last_episode": drama_data.get("last_air_date"), 
                "next_episode": next_date
            },
            "episodes":
            {
                "last_episode": last_ep, 
                "next_episode": next_ep
            },
            "poster": drama_data["seasons"][-1].get("poster_path"),
            "overview": overview,
        }
    }

    try:
        await client.find_one_and_update(_filter, _update)
    
    except Exception as e:
        print(e)
