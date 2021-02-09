import discord 
from redbot.core import commands, Config 
from redbot.core.commands import Converter, BadArgument
from discord.ext import tasks
from typing import Optional
from .converters import FuzzyItem

class StrippedInteger(Converter):
    async def convert(self, ctx, argument: str) -> int:
        argument = argument.replace(",", "")

        if not str(argument).isdigit():
            raise BadArgument(f"{argument} was not recognized as a digit")
        if int(argument) <= 0:
            raise BadArgument(f"The integer must be greater than 1.")

        return int(argument)
        
class CookieClicker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(
            self,
            identifier=160805014090190130501014,
            force_registration=True
        )

        self.cookie_task = bot.loop.create_task(self.autocookie())

        default_user = {
            "cookies": 0,
            "items": {},
        }

        default_global = {
            "cursor": 50,
            "grandma": 500,
            "megaclicker": 2000,
            "superclicker": 6000,
            "epicclicker": 10000,
            "factory": 50000,
            "ultraclicker": 125000,
            "godclicker": 500000,
            "spamclicker": 1000000,
            "holyclicker": 1500000,
            "memeclicker": 69696969,
            "cookietrophy": 3000000000,
            "blob": 10000000000, #dankmemer
            "phencookie": 20000000000,
            "flamecookie": 50000000000,
            "flarecookie": 100000000000,
            "aikacookie": 150000000000,
            "trustycookie": 300000000000,
            "kablekookie": 500000000000,
            "neurocookie": 1000000000000,
            "yamicookie": 5000000000000,
            "rickcookie": 10000000000000,
            "geocookie": 50000000000000,
            "pandacookie": 100000000000000,
            "bobloycookie": 500000000000000,
            "twentysixcookie": 1000000000000000,
            "jackcookie": 6969696969694242424242,
        }

        default_channel = {
            "sessions": {}
        }
        
        self.items = [
            "cursor",
            "grandma",
            "megaclicker",
            "superclicker",
            "epicclicker",
            "farm"
            "factory",
            "ultraclicker",
            "godclicker",
            "spamclicker",
            "holyclicker",
            "memeclicker",
            "cookietrophy"
            "blob",
            "phencookie",
            "flamecookie",
            "flarecookie",
            "aikacookie",
            "trustycookie",
            "kablekookie",
            "neurocookie",
            "yamicookie",
            "rickcookie",
            "geocookie",
            "pandacookie",
            "bobloycookie",
            "twentysixcookie",
            "jackcookie"
        ]

        self.config.register_user(**default_user)
        self.config.register_global(**default_global)
        self.config.register_channel(**default_channel)
    
    async def addcookies(self, user: int, amount: int):
        cookies = await self.config.user_from_id(user).cookies()
        cookies += amount 
        await self.config.user_from_id(user).cookies.set(cookies)

    async def autocookie(self):
        await self.bot.wait_until_ready()
        self.autotask.start()
    
    def comma_format(self, number: int):
        return "{:,}".format(number)
    
    @commands.group(name="cookieclicker", aliases=["cc"])
    async def cookieclicker(self, ctx):
        """Cookie clicker on discord"""
        pass 

    @cookieclicker.command(name="start")
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.bot_has_permissions(add_reactions=True)
    async def cc_start(self, ctx):
        """Start a game of cookie clicker"""
        e = discord.Embed(
            title="Cookie Clicker!",
            description="Click on :cookie: to get more cookies!\n",
            color=discord.Color.green()
        )

        e.description += "Click on :trophy: to view your current cookies\n"
        e.description += "Click on :octagonal_sign: to stop the session"

        message = await ctx.send(embed=e)

        sessions = await self.config.channel(ctx.channel).sessions()
        sessions[str(message.id)] = {}
        sessions[str(message.id)]["user"] = ctx.author.id

        await self.config.channel(ctx.channel).sessions.set(sessions)
        
        await self.add_reactions(message)
    
    @cookieclicker.command(name="buy")
    async def cc_buy(self, ctx, item: Optional[FuzzyItem] = None, amount: Optional[StrippedInteger] = 1):
        """Buy things from the cookieclicker shop!"""
        if not item:
            return await ctx.send(f"You need to specify something to buy")
        
        prices = await self.config.all()
        price = prices[item]
        
        user_items = await self.config.user(ctx.author).items()
        if item not in user_items:
            user_items[item] = 0
        
        cookies = await self.config.user(ctx.author).cookies()
        if (price * amount) > cookies:
            return await ctx.send(f"{item} requires {self.comma_format(price * amount)} :cookie: to buy, but you only have {self.comma_format(cookies)} :cookie:")
        
        cookies -= price
        user_items[item] += amount

        await self.config.user(ctx.author).items.set(user_items)
        await self.config.user(ctx.author).cookies.set(cookies)

        itemamount = user_items[item]

        await ctx.send(f"You bought {amount} {item}'s. You now have {itemamount} {item}'s and {self.comma_format(cookies)} :cookie:.")
    
    @cookieclicker.command(name="sell")
    async def cc_sell(self, ctx, item: Optional[FuzzyItem] = None, amount: Optional[StrippedInteger] = 1):
        """Sell items for 1/3 the normal price"""
        if not item:
            return await ctx.send(f"You need to specify something to sell.")
        
        prices = await self.config.all()
        price = prices[item]

        cookies = await self.config.user(ctx.author).cookies()
        
        cookies += round(price/3) * amount 
        user_items = await self.config.user(ctx.author).items()
        if item not in user_items:
            user_items[item] = 0
        
        if amount > user_items[item]:
            return await ctx.send("You don't have this much of this item.")
        user_items[item] -= amount

        await self.config.user(ctx.author).items.set(user_items)
        await self.config.user(ctx.author).cookies.set(cookies)

        itemamount = user_items[item]

        await ctx.send(f"You sold {amount} {item}'s. You now have {itemamount} {item}'s and {cookies} :cookie:.")
        
    @cookieclicker.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, user: Optional[discord.Member] = None):
        """View a members inventory"""
        if not user:
            user = ctx.author 
        
        item_list = []
        data = await self.config.user(user).items()

        for item, amount in data.items():
            item_list.append(f"{item}: {amount}")

        e = discord.Embed(
            title=f"{user}'s items",
            description="\n".join(item_list),
            color=discord.Color.green()
        )

        await ctx.send(embed=e)
    
    @cookieclicker.command(name="shop")
    async def cc_shop(self, ctx):
        """View the shop and its prices"""
        items = await self.config.all()
        item_list = []

        for item, cost in items.items(): #lmao
            item_list.append(f"{item}: {self.comma_format(cost)}")
        
        e = discord.Embed(
            title="Item Costs",
            description="\n".join(item_list),
            color=discord.Color.green()
        )

        await ctx.send(embed=e)
    

    
    @cookieclicker.command(name="cookies")
    async def cookies(self, ctx, user: Optional[discord.Member] = None):
        """View your cookies"""
        if not user:
            user = ctx.author 
        cookies = self.comma_format(await self.config.user(user).cookies())
        await ctx.send(f"You have {cookies} :cookie:")

    @tasks.loop(minutes=1)
    async def autotask(self):
        for userid, info in (await self.config.all_users()).items():
            userid = int(userid)
            data = info["items"]
            prices = await self.config.all()
            for item, count in data.items():
                multi = prices[item]
                multi = multi / 5 
                await self.addcookies(userid, multi * int(count))
      
    async def cancel_session(self, messageid: int, channelid: int):
        sessions = await self.config.channel_from_id(channelid).sessions()
        sessions.pop(str(messageid))
        await self.config.channel_from_id(channelid).sessions.set(sessions)
        c = self.bot.get_channel(channelid)
        if not c:
            return 
        m = c.fetch_message(messageid)
        if not m:
            return 
        e = discord.Embed(title="Session Closed")
        await m.edit(embed=e)
    
    async def add_reactions(self, message: discord.Message):
        await message.add_reaction("🍪")
        await message.add_reaction("🛑")
        await message.add_reaction("🏆")

    async def edit_cookie_message(self, messageid: int, channelid: int, userid: int):
        channel = self.bot.get_channel(channelid)
        if not channel:
            return 
        message = await channel.fetch_message(messageid)

        if not message:
            return 
        
        e = discord.Embed(
            title="Cookie Clicker!",
            description="Click on :cookie: to get more cookies!\n",
            color=discord.Color.green()
        )

        e.description += "Click on :trophy: to view your current cookies\n"
        e.description += "Click on :octagonal_sign: to stop the session\n"

        cookies = self.comma_format(await self.config.user_from_id(userid).cookies())

        e.description += f"You have {cookies} :cookie:"

        await message.edit(embed=e)
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        sessions = await self.config.channel_from_id(payload.channel_id).sessions()
        if str(payload.message_id) not in sessions:
            return 
        elif sessions[str(payload.message_id)]["user"] != payload.user_id:
            return 
            
        guild = self.bot.get_guild(payload.guild_id)
        if guild.get_member(payload.user_id) is None:
            return 
            
        if str(payload.emoji) == "🛑":
            await self.cancel_session(payload.message_id, payload.channel_id)
            return 
        elif str(payload.emoji) == "🍪":
            await self.addcookies(payload.user_id, 1)
            return   
        elif str(payload.emoji) == "🏆":
            await self.edit_cookie_message(payload.message_id, payload.channel_id, payload.user_id)
            return 
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        sessions = await self.config.channel_from_id(payload.channel_id).sessions()
        if str(payload.message_id) not in sessions:
            return 
        elif sessions[str(payload.message_id)]["user"] != payload.user_id:
            return 
            
        guild = self.bot.get_guild(payload.guild_id)
        if guild.get_member(payload.user_id) is None:
            return 
            
        if str(payload.emoji) == "🛑":
            await self.cancel_session(payload.message_id, payload.channel_id)
            return 
        elif str(payload.emoji) == "🍪":
            await self.addcookies(payload.user_id, 1)
            return   
        elif str(payload.emoji) == "🏆":
            await self.edit_cookie_message(payload.message_id, payload.channel_id, payload.user_id)
            return 
        
        
    
    def cog_unload(self):
        self.cookie_task.cancel()