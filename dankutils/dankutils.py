import discord 
from redbot.core import commands, Config 
from typing import Optional
import asyncio

class DankUtilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(
            self,
            identifier=160805014090190130501014,
            force_registration=True,
        )

        default_guild = {
            "channel": None,
        }

        default_user = {
            "reputation": 0,
            "title": "{user}'s shop",
            "description": "{user} doesn't have a shop...",
            "color": 0x000000,
            "entries": [],
            "reviews": {}, #coming soon...
        }

        self.config.register_user(**default_user)
        self.config.register_guild(**default_guild)
    
    @commands.group(name="tradeset")
    async def tradeset(self, ctx):
        """A group for managing server settings for tradeshop"""
        pass 

    @tradeset.command(name="channel")
    @commands.admin_or_permissions(manage_guild=True)
    async def tradeset_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Sets the channel that trade ads will post to"""
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("I've cleared the channel. Trade ads will now post in the channel the command was used in.")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(f"I will post trade advertisements in {channel.mention}")
    
    @commands.group(name="tradeshop", aliases=["tshop", "ts"])
    async def tradeshop(self, ctx):
        """A group for managing your tradeshop"""
        pass 

    @tradeshop.command(name="description", aliases=["about"])
    async def tradeshop_description(self, ctx, description: str = None):
        """Set the embed description for tradeshop"""
        if not description:
            return await ctx.send("You need to specify a valid description after this")
        await self.config.user(ctx.author).description.set(description)
    
    @tradeshop.command(name="add")
    async def tradeshop_add(self, ctx, text: str = None):
        """Add an entry to your tradeshop"""
        if not text:
            return await ctx.send("You need to specify some text for this entry!")
        async with self.config.user(ctx.author).entries() as entries:
            entries.append(text)
        await ctx.send(f"Entry Added.")

    @tradeshop.command(name="color")
    async def tradeshop_color(self, ctx, color: Optional[discord.Color] = None):
        """Set the embed color for tradeshop posts"""
        if not color:
            await self.config.user(ctx.author).color.clear()
            await ctx.send(f"I will no longer have colors on your trade embed")
        else:
            await self.config.user(ctx.author).color.set(color.value)
            await ctx.send(f"Your color is now {color}")
    
    @tradeshop.command(name="reputation", aliases=["rep"])
    async def reputation(self, ctx, member: Optional[discord.Member] = None):
        """View a members reputation, leave the member blank to view your own"""
        if not member:
            member = ctx.author 
        rep = await self.config.user(member).reputation()
        await ctx.send(f"**{member.name}** has **{rep}** reputation")
    
    @tradeshop.command(name="view", aliases=["settings"])
    async def view(self, ctx, member: Optional[discord.Member] = None):
        """View another members tradeshop"""
        if not member:
            member = ctx.author 
        
        data = await self.config.user(member).all()

        e = discord.Embed(
            title=data["title"].replace("{user}", member.name),
            description=data["description"].replace("{user}", member.mention),
            color=data["color"]
        )

        formatted_entries = ""

        for i, entry in enumerate(data["entries"], start=1):
            formatted_entries += f"{i}. {entry}\n"
        
        if len(formatted_entries) == 0:
            formatted_entries = "Nothing Here"


        e.add_field(name="Entries", value=formatted_entries[:2000], inline=False)
        e.add_field(name="Reputation", value=data["reputation"], inline=False)

        await ctx.send(embed=e)
    
    @tradeshop.command(name="post")
    async def post(self, ctx):
        """Post your trade ad either in the current channel or to the servers set channel"""
        channel = await self.config.guild(ctx.guild).channel()
        if not channel:
            channel = ctx.channel 
        else:
            channel = self.bot.get_channel(channel)
            if not channel:
                await self.config.guild(ctx.guild).channel.clear()
                channel = ctx.channel
        
        if not channel.permissions_for(ctx.me).send_messages:
            if channel == ctx.channel:
                return 
            return await ctx.send(f"I don't have permissions to send messages in {channel.mention}")
        
        data = await self.config.user(ctx.author).all()

        e = discord.Embed(
            title=data["title"].replace("{user}", ctx.author.name),
            description=data["description"].replace("{user}", ctx.author.mention),
            color=data["color"]
        )

        formatted_entries = ""

        for i, entry in enumerate(data["entries"], start=1):
            formatted_entries += f"{i}. {entry}\n"
        
        if len(formatted_entries) == 0:
            formatted_entries = "Nothing Here"


        e.add_field(name="Entries", value=formatted_entries[:2000], inline=False)
        e.add_field(name="Reputation", value=str(data["reputation"]), inline=False)

        try:
            await channel.send(embed=e)
        except (discord.errors.Forbidden, discord.HTTPException):
            return 
    
    @tradeshop.command(name="remove")
    async def remove(self, ctx, number: Optional[int] = None):
        """Remove an entry"""
        if not number:
            return await ctx.send(f"You need to specify a number after this!")
        entries = await self.config.user(ctx.author).entries()
        if len(entries) < number - 1:
            return await ctx.send("This isn't in your entries!")
        
        async with self.config.user(ctx.author).entries() as entries:
            entries.pop(number - 1)
        await ctx.send("This entry has been removed")
        
    
    @commands.command(name="trade", cooldown_after_parsing=True)
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def trade(self, ctx, user: Optional[discord.Member] = None, * , offer: str = None):
        """Trade with another user"""
        if not user:
            await ctx.send("You can't trade with nobody. Specify a members ID, name, or mention after this please.")
            ctx.command.reset_cooldown
            return 
        if not offer:
            await ctx.send("Make an offer, such as `I'll give you a santa hat`")
            ctx.command.reset_cooldown
            return 

        await ctx.send(f"{user.mention}: {ctx.author.mention} wants to trade {offer}. Do you accept?")

        def check(m):
            return m.author == user and m.channel == ctx.channel

        try:
            resp = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            ctx.command.reset_cooldown
            return await ctx.send("The other user didn't reply. :(")

        if resp.content.lower() == "yes":
            async with self.config.user(ctx.author).reputation() as rep:
                rep += 1
            async with self.config.user(user).reputation() as rep:
                rep += 1

            await ctx.send(f"{user.name} agrees! You've both earned 1 reputation point")
        else:
            await ctx.send("The other user didn't agree to the trade :(")
        