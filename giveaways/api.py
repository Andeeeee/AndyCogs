from mee6_py_api import API 
from aiohttp import ClientSession
from bs4 import BeautifulSoup
import re
import discord 

class mee6_api():
    def __init__(self):
        self.api_guild_cache = {}

    async def get_user_rank(self, guild: str, user: str):
        if guild not in self.api_guild_cache:
            self.api_guild_cache[guild] = API(int(guild))
        
        api = self.api_guild_cache[guild]

        return (await api.levels.get_user_level(int(user)))

class Amari():
    def __init__(self):
        self.session = ClientSession()

    async def get_amari_rank(self, guild: int, user: discord.User):
        gid = guild
        username = user.name 
        url = f"https://lb.amaribot.com/weekly.php?gID={gid}"
        
        async with self.session.request("GET", url) as response:
            text = await response.text()
        obj = BeautifulSoup(text, "html.parser")
        rank_list = obj.body.main.findAll("div")[2].div.find("table").findAll("tr")
        tag = None 
        for tag in rank_list:
            if username in str(tag):
                break
        check = re.compile(r"<tr><td>(\d+)<\/td><td>({})<\/td><td>(\d+)<\/td><td>(\d+)<\/td><\/tr>".format(username))
        if not tag:
            return None
        match = re.match(check, str(tag))
        
        try:
            return int(match.group(4))
        except TypeError:
            return 0
    
    async def get_weekly_rank(self, guild: int, user: discord.User):
        gid = guild
        username = user.name 
        url = f"https://lb.amaribot.com/weekly.php?gID={gid}"
        
        async with self.session.request("GET", url) as response:
            text = await response.text()
        obj = BeautifulSoup(text, "html.parser")
        rank_list = obj.body.main.findAll("div")[2].div.find("table").findAll("tr")
        for tag in rank_list:
            if username in str(tag):
                break
        check = re.compile(r"<tr><td>(\d+)<\/td><td>({})<\/td><td>(\d+)<\/td><td>(\d+)<\/td><\/tr>".format(username))
        if not tag:
            return 
        match = re.match(check, str(tag))

        
        try:
            return int(match.group(3))
        except TypeError:
            return 0