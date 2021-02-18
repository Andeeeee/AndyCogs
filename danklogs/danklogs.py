import discord, asyncio

from datetime import datetime
from rapidfuzz import process
from redbot.core import commands, Config 
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from typing import Optional 
from unidecode import unidecode



class DankLogs(commands.Cog):
    """Track things for dankmemer"""
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, 160805014090190130501014, True)

        default_item_values = {
            "bank": 250000,
            "pepe": 100000,
            "pizza": 100000,
            "pepecoin": 1000000,
            "pepemedal": 8000000,
            "pepetrophy": 45000000,
            "toe": 1000000,
            "cutter": 300000000,
            "blob": 750000000,
            "oddeye": 0,
            "alcohol": 4000,
            "apple": 1500,
            "sand": 1500,
            "phone": 700,
            "coinbomb": 4000,
            "fakeid": 750,
        } 
        #this will only be used for giveaways when they must have shared `x` coins

        default_guild = {
            "channel": None,
            "toprole": None,
            "enabled": False,
        }

        default_member = {
            "shared": 0,
            "gifted": {},
            "received": 0,
            "receiveditems": {},
            "giftedusers": {},
            "sharedusers": {},
            "logs": []
        }

        default_channel = {
            "ignored": False,
        }


        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.config.register_channel(**default_channel)
    
    def comma_format(self, number: int):
        return "{:,}".format(number)
    
    async def get_last_message(self, message):
        async for m in message.channel.history:
            if m.author.bot:
                pass 
            else:
                return m
    
    def get_fuzzy_member(self, ctx, name):
        result = []
        name = name.lstrip("<@!").lstrip("<@").rstrip(">")
        if name.isdigit():
            m = ctx.guild.get_member(int(name))
            if not m:
                pass 
            else:
                return m
        for r in process.extract(
            name,
            {m: unidecode(m.name) for m in ctx.guild.members},
            limit=None,
            score_cutoff=75,
        ):
            result.append((r[2], r[1]))

            
        sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]
    
    @commands.group(aliases=["dls"])
    @commands.mod_or_permissions(manage_guild=True)
    async def danklogset(self, ctx):
        """Set server settings for dank logs"""
        pass 
    
    @danklogset.command()
    async def channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set the channel to log actions to"""
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("I will no longer have a channel")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(f"I will now log actions to {channel.mention}")
    
    @danklogset.command()
    async def enabled(self, ctx, state: Optional[bool] = False):
        """Set whether tracking is enabled"""
        await self.config.guild(ctx.guild).enabled.set(state)
        if state == False:
            await ctx.send("No longer tracking dankmemer actions")
        else:
            await ctx.send("I will now track dankmemer actions")
    
    @commands.group(aliases=["dankstats"], invoke_without_command=True)
    async def dankinfo(self, ctx, user: Optional[discord.Member] = None):
        """View info for yourself or a user from dankmemer"""
        if not ctx.invoked_subcommand:
            if not user:
                user = ctx.author
            
            data = await self.config.member(user).all()

            e = discord.Embed(
                title = f"Dank Memer Gift & Share Stats for {user}",
                color = await ctx.embed_color(),
                description = "Shared Money: {}\nTotal Shared Items: {}\nTotal Shared Users: {}\nTotal Gifted Users: {}".format(
                    data["shared"], len(data["gifted"]), len(data["sharedusers"]), len(data["giftedusers"])
                )
            )
            await ctx.send(embed=e)
    
    @dankinfo.command()
    async def shared(self, ctx, user: Optional[discord.Member] = None):
        """View the amount you or a user has shared"""
        if not user:
            user = ctx.author 
        
        shared = await self.config.member(user).shared()

        await ctx.send(f"**{user}** has shared a total of **{self.comma_format(shared)}** coins in this server")
    
    @dankinfo.command()
    async def gifted(self, ctx, user: Optional[discord.Member] = None):
        """View the amount a user has gifted (only shows items)"""
        if not user:
            user = ctx.author
        
        gifted = await self.config.member(user).gifted()
        gifted = sorted(gifted.items(), key = lambda m: m[1], reverse=True)

        e = discord.Embed(title=f"{user}'s gifted items")

        formatted_gifted = ""

        for item, amount in gifted:
            formatted_gifted += "{}: {}\n".format(item, amount)
        
        if len(formatted_gifted) == 0 or formatted_gifted == "":
            return await ctx.send("This user has not gifted anything yet")
        
        if len(formatted_gifted) >= 2048:
            pages = list(pagify(formatted_gifted))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Gifted Items for {user}",
                    description=p,
                    color = await ctx.embed_color(),
                )
                e.set_footer(text=f"Page {i} out of {len(pages)} pages")
                embeds.append(e)
            
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Gifted Items for {user}",
                description=formatted_gifted,
                color = await ctx.embed_color()
            )
            await ctx.send(embed=e)
    
    @dankinfo.command()
    async def received(self, ctx, user: Optional[discord.Member] = None):
        """View the items a user has received"""
        if not user:
            user = ctx.author 
        
        received = await self.config.member(user).received()
        received = sorted(received.items(), key = lambda m: m[1], reverse=True)

        formatted_received = ""

        for item, amount in received:
            formatted_received += f"{item}: {amount}\n"
        
        if len(formatted_received) == 0 or formatted_received == "":
            return await ctx.send("This user has not gifted anything yet")
        
        if len(formatted_received) >= 2048:
            pages = list(pagify(formatted_received))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Received Items for {user}",
                    description=p,
                    color = await ctx.embed_color(),
                )
                e.set_footer(text=f"Page {i} out of {len(pages)} pages")
                embeds.append(e)
            
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Received Items for {user}",
                description=formatted_received,
                color = await ctx.embed_color()
            )
            await ctx.send(embed=e)
    
    @dankinfo.command()
    async def sharedusers(self, ctx, user: Optional[discord.Member] = None):
        """View the users a user has shared money to"""
        if not user:
            user = ctx.author
        sharedusers = await self.config.member(user).sharedusers()
        sharedusers = sorted(sharedusers.items(), key = lambda m: m[1], reverse=True)

        formatted_shared = ""

        for user, shared in sharedusers:
            formatted_shared += f"<@{user}>: {shared}"
        
        if len(formatted_shared) == 0 or formatted_shared == "":
            return await ctx.send("This user has shared nothing")
        
        if len(formatted_shared) >= 2048:
            pages = list(pagify(formatted_shared))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Users {user} has shared to",
                    description=p,
                    color = await ctx.embed_color(),
                )
                embeds.append(e)
            
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Users {user} has shared to",
                description=formatted_shared,
                color = await ctx.embed_color()
            )
            await ctx.send(embed=e)
    
    @dankinfo.command()
    async def giftedusers(self, ctx, user: Optional[discord.Member] = None):
        """View the users a user has gifted items to"""
        if not user:
            user = ctx.author
        giftedusers = await self.config.member(user).giftedusers()
        giftedusers = sorted(giftedusers.items(), key = lambda m: m[1], reverse=True)

        formatted_shared = ""

        for user, shared in giftedusers:
            formatted_shared += f"<@{user}>: {shared}"
        
        if len(formatted_shared) == 0 or formatted_shared == "":
            return await ctx.send("This user has shared nothing")
        
        if len(formatted_shared) >= 2048:
            pages = list(pagify(formatted_shared))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Users {user} has gifted to",
                    description=p,
                    color = await ctx.embed_color(),
                )
                embeds.append(e)
            
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Users {user} has gifted to",
                description=formatted_shared,
                color = await ctx.embed_color()
            )
            await ctx.send(embed=e)
    
    @dankinfo.command()
    @commands.mod_or_permissions(manage_guild=True)
    async def logs(self, ctx, user: Optional[discord.Member] = None):
        if not user:
            user = ctx.author 
        
        logs = await self.config.member(user).logs()

        if len(logs) == 0:
            return await ctx.send("This user has no logs to show")
        
        logs = "\n\n".join(logs)

        if len(logs) >= 2048:
            pages = list(pagify(logs))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(title=f"Logs for {user}", description=p, color = await ctx.embed_color())
                e.set_footer(text=f"Page {i} out of {len(pages)} pages")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send(embed=discord.Embed(title=f"Logs for {user}", description=logs, color = await ctx.embed_color()))
    

    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        if not message.author.id == 270904126974590976:
            return 
        if "You gave" not in message.content:
            return 
        if not (await self.config.guild(message.guild).enabled()):
            return 
        if (await self.config.channel(message.channel).ignored()):
            return 
        last_message = await self.get_last_message(message)
        filtered_content = message.content.strip().lstrip(f"<@{last_message.author.id}>").lstrip(f"<@!{last_message.author.id}>").strip().lstrip("You gave").strip()
        filtered_content = " ".join(filtered_content.split()).strip()

        amount = int(filtered_content.split("**")[1].strip("⏣ ")) 
        member = last_message.content.lower().lstrip("pls gift").lstrip("pls share").split()[0]
        shared_user = self.get_fuzzy_member(message, member)
        if not shared_user:
            return 

        shared_user_data = await self.config.member(shared_user).all()
        user_data = await self.config.member(last_message.author).all()
        
        if last_message.content.lower().startswith("pls share"):
            if str(shared_user.id) not in user_data["sharedusers"]:
                user_data["sharedusers"][str(shared_user.id)] = 0 

            user_data["sharedusers"][str(shared_user.id)] += 1 
            user_data["shared"] += amount 
            shared_user_data["received"] += amount 
            formatted_now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")
            user_data["logs"].append(f"At {formatted_now}, {amount} was shared to {shared_user} (ID of {shared_user.id})")
            shared_user_data["logs"].append(f"At {formatted_now}, {amount} was received from {message.author} (ID of {message.author.id})")
            await self.config.member(shared_user).set(shared_user_data)
            await self.config.member(last_message.author).set(user_data)

            channel = await self.config.guild(message.guild).channel()
            channel = self.bot.get_channel(channel)
            if not channel:
                return 
            e = discord.Embed(title="Dankmemer Logs", description=f"{last_message.author.mention} shared {amount} coins to {shared_user.mention} in {message.channel.mention}")
            await channel.send(embed=e)
        
        else:
            if str(shared_user.id) not in user_data["giftedusers"]:
                user_data["giftedusers"][str(shared_user.id)] = 0 
            
            user_data["giftedusers"][str(shared_user.id)] += 1 
            if filtered_content.split("**")[2] not in user_data["gifted"]:
                user_data["gifted"][filtered_content.split("**")[2]] = 0
            user_data["gifted"][filtered_content.split("**")[2]] += 1

            if filtered_content.split("**")[2] not in shared_user_data["receiveditems"]:
                user_data["receiveditems"][filtered_content.split("**")[2]] = 0
            user_data["receiveditems"][filtered_content.split("**")[2]] += 1

            formatted_now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")
            shared_user_data["logs"].append(f"On {formatted_now}, {last_message.author} gave {amount} {filtered_content.split('**')[1]}")
            user_data["logs"].append(f"On {formatted_now}, {amount} {filtered_content.split('**')[1]} was sent to {shared_user}")

            channel = await self.config.guild(message.guild).channel()
            channel = self.bot.get_channel(channel)
            await self.config.member(shared_user).set(shared_user_data)
            await self.config.member(last_message.author).set(user_data)
            if not channel:
                return 
            e = discord.Embed(title="Dankmemer Logs", description=f"{message.author.mention} gave {amount} {filtered_content.split('**')[2]} to {shared_user.mention} in {message.channel.mention}")
            await channel.send(embed=e)
        

        
