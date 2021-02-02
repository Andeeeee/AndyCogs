import discord 
from datetime import datetime
from redbot.core import commands, Config 
from redbot.core.commands import Converter, BadArgument
from typing import Optional

class TimeConverter(Converter):
    async def convert(self, ctx: commands.Context, time: str) -> int:
        conversions = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "mo": 604800*30 }
        
        if str(time[-1]) not in conversions:
            if not str(time).isdigit():
                raise BadArgument(f"{time} was not able to be converted to a time.")
            return int(time) 
        
        multiplier = conversions[str(time[-1])]
        
        time = time[:-1]
        if not str(time).isdigit():
            raise BadArgument(f"{time} was not able to be converted to a time.")
        
        if int(time) * multiplier <= 0:
            raise BadArgument("You can't have less than 0")

        return int(time) * multiplier

class FreeLoaderMode(commands.Cog):
    """A highlight useful cog dedicated to make banning those stupid freeloaders that leave your server right after an event or something"""
    
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(
            self,
            identifier=160805014090190130501014,
            force_registration=True
        )

        default_guild = {
            "toggled": False,
            "untoggletime": None,
            "ignored": [],
        }

        self.config.register_guild(**default_guild)
    
    @commands.group(name="freeloadermode", aliases=["fm", "freeloader"])
    @commands.admin_or_permissions(manage_guild=True)
    async def freeloadermode(self, ctx):
        """Manage settings for freeloadermode"""
        pass 
    
    @freeloadermode.command(name="on")
    async def on(self, ctx, time: Optional[TimeConverter] = None):
        """Toggle freeloader mode with an optional time to untoggle"""
        toggled = await self.config.guild(ctx.guild).toggled()
        if toggled:
            return await ctx.send("You are already on freeloader mode")
        await self.config.guild(ctx.guild).toggled.set(True)
        if not time:
            return await ctx.send("You are now in freeloader mode.")
        endtime = datetime.utcnow().timestamp() + time 
        await self.config.guild(ctx.guild).untoggletime.set(endtime)
        endtime = datetime.fromtimestamp(endtime) - datetime.utcnow()
        await ctx.send(f"You are now toggled. You will untoggle in {endtime.total_seconds()} seconds.")
        
    @freeloadermode.command(name="off")
    async def off(self, ctx):
        """Toggle freeloader mode off"""
        toggled = await self.config.guild(ctx.guild).toggled()
        if not toggled:
            return await ctx.send("You are not on freeloader mode")
        await self.config.guild(ctx.guild).toggled.clear()
        await self.config.guild(ctx.guild).untoggletime.clear()
        await ctx.send("No longer in freeloader mode.")
    
    @freeloadermode.command(name="ignore")
    async def ignore(self, ctx, user: Optional[discord.Member] = None):
        """Don't ban a user if they leave the server"""
        ignored = await self.config.guild(ctx.guild).ignored()
        if user.id in ignored:
            return await ctx.send("This user is already being ignored")
        ignored.append(user.id)
        await ctx.send("Added to the ignore list")
    
    @freeloadermode.command(name="unignore")
    async def unignore(self, ctx, user: Optional[discord.Member] = None):
        """Unignore a user"""
        ignored = await self.config.guild(ctx.guild).ignored()
        if user.id not in ignored:
            return await ctx.send("This user is not being ignored")
        ignored.remove(user.id)
        await ctx.send("Removed to the ignore list")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return 
        guild = member.guild
        if not (await self.config.guild(guild).toggled()):
            return 
        time = await self.config.guild(guild).untoggletime()
        if time is None:
            pass 
        else:
            if time - datetime.utcnow().timestamp() <= 0:
                await self.config.guild(guild).toggled.clear()
                await self.config.guild(guild).untoggletime.clear()
                return 
        
        if member.id in (await self.config.guild(guild).ignored()):
            return 
        
        await guild.ban(member, reason="Member Left while freeloader mode was toggled")