from mee6_py_api import API 

class mee6_api:
    def __init__(self):
        self.api_guild_cache = {}

    async def get_user_rank(self, guild: str, user: str):
        if guild not in self.api_guild_cache:
            self.api_guild_cache[guild] = API(int(guild))
        
        api = self.api_guild_cache[guild]

        return (await api.levels.get_user_level(int(user)))