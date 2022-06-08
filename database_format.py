guild_config = {
    "guild_id": 123,
    "dramas_followed": [],
    "dramas_followed_names": {},
    "ping_roles":
    {
        "kpop": 123,
        "kdrama": 234,
        "cdrama": 345
    },
    "drama_channels":
    {
        "default_channel": 321,
        "ko_drama_channel": 123,
    },
    "notify_channels":
    {
        "default_channel": 321,
        "ko_notify_channel": 123,
        "tw_notify_channel": 234,
    },

    "dramas":
    {
        "KO":
        [
            {
                "drama_id": 123,
                "notify_channel": 123,
                "members": [1,2,3]
            }
        ],
        "TW":
        [
            {
                "drama_id": 123,
                "notify_channel": 123,
                "members": [5]
            }
        ],
    }
}
# https://discord.com/api/oauth2/authorize?client_id=861913355693064203&permissions=355392&scope=bot



# data = {"drama_id": drama_id, \
#     "name": show_data.get("name"),
#     "language": show_data.get("original_language"),
#     "drama_overview": show_data.get("overview"),
#     "season": show_data["seasons"][-1].get("season_number"), 
#     "dates": {
#         "last_episode": show_data.get("last_air_date"), 
#         "next_episode": show_data.get("next_episode_to_air").get("air_date")
#         }, 
#     "episode": {
#         "last_episode": show_data.get("last_episode_to_air").get("episode_number"), 
#         "next_episode": show_data.get("next_episode_to_air").get("episode_number")
#         }, 
#     "poster": show_data["seasons"][-1].get("poster_path"),
#     "overview": show_data.get("last_episode_to_air").get("overview"),
#     "guilds": [ctx.guild.id, ]
# }