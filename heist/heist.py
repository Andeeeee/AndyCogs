import argparse #here we go again
import asyncio
import discord 
from redbot.core import commands, Config 
from redbot.core.commands import Converter, BadArgument
from typing import Optional

class TimeConverter(Converter):
    async def convert(self, ctx: commands.Context, time: str) -> int:
        conversions = {"s": 1, "m": 60}
        
        if str(time[-1]) not in conversions:
            if not str(time).isdigit():
                raise BadArgument(f"{time} was not able to be converted to a time.")
            return int(time) 
        
        multiplier = conversions[str(time[-1])]
        
        time = time[:-1]
        if not str(time).isdigit():
            raise BadArgument(f"{time} was not able to be converted to a time.")
        
        return int(time) * multiplier

class Heist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(
            self,
            identifier=160805014090190130501014,
            force_registration=True,
        )

        default_guild = {
            "pingrole": None,
            "waittime": 60,
        }

        self.config.register_guild(**default_guild)
    
    @commands.group(name="heist")
    async def heist(self, ctx):
        pass 
    
    @heist.command(name="pingrole", aliases=["role"])
    @commands.admin_or_permissions(manage_guild=True)
    async def pingrole(self, ctx, role: Optional[discord.Role] = None):
        """Set the role to ping for heist start"""
        if not role:
            await self.config.guild(ctx.guild).pingrole.clear()
            await ctx.send("Cleared your servers pingrole. I will no longer ping a role for heists")
        else:
            await self.config.guild(ctx.guild).pingrole.set(role.id)
            await ctx.send(f"`{role}` will now be pinged for heists.")
    
    @heist.command(name="waittime", aliases=["time"])
    @commands.admin_or_permissions(manage_guild=True)
    async def heist_waittime(self, ctx, time: Optional[TimeConverter] = None):
        """Set the delay time before the bot gives up on a heist. Cannot be less than 10 seconds or greater than 240 seconds"""
        if not time:
            return await ctx.send("The time was not specified or was invalid. Please try again")
        elif time < 10 or time > 240:
            return await ctx.send("The time cannot be less than 10 seconds and greater than 240 seconds.")
        else:
            await self.config.guild(ctx.guild).waittime.set(time)
            await ctx.send(f"The time before I give up for heists is now {time} seconds")
    
    @heist.command(name="start")
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.cooldown(1, 30, commands.BucketType.channel) 
    @commands.mod_or_permissions(manage_channels=True, mention_everyone=True)
    @commands.bot_has_permissions(manage_channels=True, mention_everyone=True)
    async def h_start(
        self,
        ctx,
        four_minutes: Optional[bool] = False,
        role: Optional[discord.Role] = None,
        *,
        flags,
    ):
        """Starts a heist, when dankmemer sends the heist message, it will unlock the channel
        for a role, or for everyone, if four_minutes is True, it will lock in four minutes.

        Flags:
        --firstrole: Specify the role to unlock before unlocking the role specified
        --time: Specify the time the firstrole should have before the normal role unlocks

        If time is not specified and firstrole is. The time will be 20 seconds.
        If time is specified and firstrole is not, this will throw an error.
        """

        parser = argparse.ArgumentParser(description="argparse")
 
        parser.add_argument(
            "--firstrole",
            nargs="?",
            type=str,
            default=None,
            help="The first role to unlock",
        )

        parser.add_argument(
            "--time",
            nargs="?",
            type=int,
            default=20,
            help="The time before the role unlocks.",
        )
        
        try:
            args = vars(parser.parse_args(flags))
        except:
            return await ctx.send("I had trouble parsing flags. Please try again")

        if args["firstrole"]:
            firstrole = args["firstrole"].lstrip("<@&").rstrip(">")
            
            if firstrole.isdigit():
                firstrole = ctx.guild.get_role(int(firstrole))
            else:
                firstrole = discord.utils.get(ctx.guild.roles, name=firstrole)
            
            if not firstrole:
                return await ctx.send("`{0}` was not recognized as a role").format(args["firstrole"])
        
        if not role:
            role = ctx.guild.default_role 

        time = 90
        formatted_time = "1 minute 30 seconds"

        if four_minutes:
            time = 240
            formatted_time = "4 minutes"
        
        if args["time"] >= time:
            return await ctx.send("The delay time for firstrole cannot be greater than or equal to the heist time.")
        
        if args["time"] and firstrole:
            time = time - args["time"]
        else:
            return await ctx.send("The time or the firstrole was specified without the other argument. If one is provided, both must.")
        
        waittime = await self.config.guild(ctx.guild).waittime()

        correct_answer = "is starting a bank robbery"
        
        def check(m):
            return m.author.id == 270904126974590976 and m.channel == ctx.channel and correct_answer in m.content and m.channel.last_message.content.startswith("pls heist") #imagine changing danks prefix
        try:
            message = await self.bot.wait_for("message", check=check, timeout=waittime)
        except asyncio.TimeoutError:
            return await ctx.send("Uh oh. No heist found. Try again later")
        
        mentions = discord.AllowedMentions(roles=True, everyone=False)
        pingrole = await self.config.guild(ctx.guild).pingrole()
        if pingrole:
            pingrole = ctx.guild.get_role(pingrole)
            if not pingrole:
                await self.config.guild(ctx.guild).pingrole.clear()
                heist_message = f"Channel unlocked for `{role.name}`! Locking in {formatted_time}"
            else:
                heist_message = f"{pingrole.mention}: Channel unlocked for `{role.name}`! Locking in {formatted_time} seconds"
        else:
            heist_message = f"Channel unlocked for `{role.name}`! Locking in {formatted_time}"

        if args["time"] and firstrole:
            overwrites = ctx.channel.overwrites_for(firstrole)
            overwrites.send_messages = True
            try:
                await ctx.channel.set_permissions(firstrole, overwrite=overwrites)
            except (discord.errors.Forbidden, discord.HTTPException):
                return await ctx.send("I do not have permissions to do this or an internal server error occured. Try again.")
            
            await ctx.channel.send(heist_message, allowed_mentions=mentions)

            await asyncio.sleep(args["time"])
        
        overwrites = ctx.channel.overwrites_for(role)
        overwrites.send_messages = True 
        try:
            await ctx.channel.set_permissions(role, overwrite=overwrites)
        except (discord.errors.Forbidden, discord.HTTPException):
                return await ctx.send("I do not have permissions to do this or an internal server error occured. Try again.")             
                
        await ctx.channel.set_permissions(role, overwrite=overwrites)

        await asyncio.sleep(time)

        if args["time"] and firstrole:
            overwrites = ctx.channel.overwrites_for(firstrole)
            overwrites.send_messages = False
            try:
                await ctx.channel.set_permissions(firstrole, overwrite=overwrites)
            except (discord.errors.Forbidden, discord.HTTPException):
                return await ctx.send("I do not have permissions to do this or an internal server error occured. Try again.")
            
            await ctx.channel.send(heist_message, allowed_mentions=mentions)

            await asyncio.sleep(args["time"])
        
        overwrites = ctx.channel.overwrites_for(role)
        overwrites.send_messages = False
        try:
            await ctx.channel.set_permissions(role, overwrite=overwrites)
        except (discord.errors.Forbidden, discord.HTTPException):
                return await ctx.send("I do not have permissions to do this or an internal server error occured. Try again.")      

        await channel.send("Times Up. Channel Locked.")       
