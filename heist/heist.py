import argparse 
import asyncio
import discord 

from rapidfuzz import process
from redbot.core import commands, Config 
from redbot.core.commands import Converter, BadArgument
from redbot.core.utils.chat_formatting import humanize_list
from typing import Optional
from unidecode import unidecode

async def heist_manager(ctx):
    if not ctx.guild:
        return False
    if (await ctx.bot.is_owner(ctx.author)):
        return True 
    elif ctx.channel.permissions_for(ctx.author).administrator or ctx.channel.permissions_for(ctx.author).manage_guild:
        return True 
    else:
        cog = ctx.bot.get_cog("Heist")
        manager = await cog.config.guild(ctx.guild).manager()
        if not manager:
            return False 
        if manager not in [r.id for r in ctx.author.roles]:
            return False 
        return True

class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise commands.BadArgument(message)

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
            "sendembed": True,
            "manager": None
        }

        self.config.register_guild(**default_guild)
    
    def convert_amount(self, amount: str):
        conversions = {"k": 1000, "m": 1000000}
        if amount[-1] not in conversions:
            return round(int(amount))
        else:
            return round(int(amount[:-1]) * conversions[amount[-1]])
    
    def display_time(self, seconds: int) -> str:
        message = ""

        intervals = (
            ('week', 604_800),  # 60 * 60 * 24 * 7
            ('day',   86_400),  # 60 * 60 * 24
            ('hour',   3_600),  # 60 * 60
            ('minute',    60),
            ('second',     1),
        )

        for name, amount in intervals:
            n, seconds = divmod(seconds, amount)

            if n == 0:
                continue

            message += f'{n} {name + "s" * (n != 1)} '

        return message.strip()
    
    def get_fuzzy_role(self, ctx, name: str):
        result = []
        for r in process.extract(
            name,
            {r: unidecode(r.name) for r in ctx.guild.roles},
            limit=None,
            score_cutoff=75,
        ):
            result.append((r[2], r[1]))
        
        if not result:
            raise BadArgument("{} is not a valid role")

        sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]
    
    async def get_heist_message(self, ctx, flags, sleep_time, early_time, role):
        heist_message = ""
        early_heist_message = ""

        if flags["ping"]:
            pingrole = await self.config.guild(ctx.guild).pingrole()
            role = ctx.guild.get_role(pingrole)
            heist_message += f"{role.mention}: "
        
        if flags["early-roles"]:
            roles = humanize_list([r.name for r in flags["early-roles"]])
            early_heist_message += f"Channel Unlocked for {roles}! Unlocking in {self.display_time(early_time)} "
        
        heist_message += f"Channel Unlocked for {role.name}! Locking in {sleep_time} seconds"

        return heist_message, early_heist_message
    
    async def clean_flags(self, ctx, flags):
        if flags["donor"]:
            try:
                donor = ctx.guild.get_member(int(flags["donor"]))
            except ValueError:
                donor = discord.utils.get(ctx.guild.members, name=flags["donor"])
            
            if not donor:
                raise BadArgument("{} is not a valid member for the donor flag".format(flags["donor"]))

            flags["donor"] = donor
        
        if flags["amt"]:
            try:
                amt = self.convert_amount(flags["amt"])
            except ValueError:
                raise BadArgument("{} was not able to be converted to a proper amount".format(flags["amt"]))

            flags["amt"] = amt
        
        if flags["total"]:
            try:
                total = self.convert_amount(flags["total"])
            except ValueError:
                raise BadArgument("{} was not able to be converted to a proper amount".format(flags["total"]))
        
        if flags["early-roles"]:
            final_roles = []
            for r in flags["early-roles"]:
                try:
                    role = ctx.guild.get_role(int(r))
                except ValueError:
                    role = self.get_fuzzy_role(r) 
                final_roles.append(role)
            flags["early-roles"] = final_roles 
        
        if flags["ping"]:
            pingrole = await self.config.guild(ctx.guild).pingrole()
            if not pingrole:
                ping = False 
            elif ctx.guild.get_role(pingrole) is None:
                await self.config.guild(ctx.guild).pingrole.clear()
                ping = False 
            else:
                ping = True 
            flags["ping"] = ping
            
        return flags
    
    def get_sleep_time(self, long, early_roles, early_seconds):
        if long:
            sleep_time = 240 
        else:
            sleep_time = 90
        if not early_roles:
            return sleep_time, None
            
        sleep_time -= early_seconds
        return sleep_time, early_seconds
    
    async def get_last_message(self, ctx, message):
        async for m in ctx.channel.history(before=message, limit=1):
            return m
                
    @commands.group()
    async def heistset(self, ctx):
        pass 

    @heistset.command()
    async def manager(self, ctx, role: Optional[discord.Role] = None):
        """Set the role that can create/start/update heists and amounts"""
        if not role:
            await self.config.guild(ctx.guild).manager.clear()
            await ctx.send("Cleared the manager role for your server")
        else:
            await self.config.guild(ctx.guild).manager.set(role.id)
            await ctx.send(f"**{role.name}** is now the manager role")
    
    @heistset.command(aliases=["role"])
    @commands.admin_or_permissions(manage_guild=True)
    async def pingrole(self, ctx, role: Optional[discord.Role] = None):
        """Set the role to ping for heist start"""
        if not role:
            await self.config.guild(ctx.guild).pingrole.clear()
            await ctx.send("Cleared your servers pingrole. I will no longer ping a role for heists")
        else:
            await self.config.guild(ctx.guild).pingrole.set(role.id)
            await ctx.send(f"**{role.name}** will now be pinged for heists")
    
    @commands.group()
    async def heist(self, ctx):
        pass 

    @heist.command(cooldown_after_parsing=True)
    @commands.guild_only()
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.cooldown(1, 30, commands.BucketType.channel) 
    @commands.check(heist_manager)
    @commands.bot_has_permissions(manage_channels=True, mention_everyone=True)
    async def start(
        self,
        ctx,
        unlockrole: Optional[discord.Role] = None,
        *args,
    ):
        """Starts a heist"""
        if not unlockrole:
            unlockrole = ctx.guild.default_role
            
        allowed_mentions = discord.AllowedMentions(everyone=False, roles=True, users=True)

        parser = NoExitParser()
        parser.add_argument("--long", action="store_true", default=False)
        parser.add_argument("--embed", type=bool, default=False)
        parser.add_argument("--ping", action="store_true", default=False)
        parser.add_argument("--donor", default=None, nargs="?")
        parser.add_argument("--amt", type=str, nargs="?", default=None)
        parser.add_argument("--total", default=None, nargs="?")
        parser.add_argument("--early-roles", default=None, nargs="*")
        parser.add_argument("--early-seconds", default=30, type=int, nargs="?")
        
        if not args:
            flags = {
                "long": False,
                "embed": False,
                "ping": False,
                "donor": None,
                "amt": None,
                "early-roles": None,
                "early-seconds": 30,
                "total": None,
            }
        else:
            try:
                flags = vars((parser.parse_known_args(args))[0])
            except BadArgument as e:
                return await ctx.send(str(e))
            
            try:
                args = await self.clean_flags(ctx, flags)
            except BadArgument as e:
                return await ctx.send(str(e))
        
        sleep_time, early_time = self.get_sleep_time(flags["long"], flags["early-roles"], flags["early-seconds"])
        heist_message, early_heist_message = await self.get_heist_message(ctx, flags, sleep_time, early_time, unlockrole)

        emoji = self.bot.get_emoji(794006801019568138)
        if not emoji:
            await ctx.send("Waiting for a heist message, send `CANCEL` to cancel the heist")
        else:
            await ctx.send(f"Waiting for a heist message, send `CANCEL` to cancel the heist {emoji}")
            
        def heist_check(m):
            message = asyncio.create_task(self.get_last_message(ctx, m))
            return (m.author.id == 270904126974590976 and not message.content.lower().startswith("pls say") and "They're trying to break into" in m.content) or m.content == "CANCEL"

        try:
            m = await self.bot.wait_for("message", check=heist_check, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send("Uh oh, you ran out of time. Try again later")
        
        if m.content == "CANCEL":
            return await ctx.send("Cancelled the heist")
        

        if flags["early-roles"]:
            for r in flags["early-roles"]:
                overwrites = ctx.channel.overwrites_for(r)
                overwrites.send_messages = True 
                overwrites.read_messages = True 
                await ctx.channel.set_permissions(r, overwrite=overwrites)
            await ctx.send(early_heist_message, allowed_mentions=allowed_mentions)
            await asyncio.sleep(early_time)
        
        overwrites = ctx.channel.overwrites_for(unlockrole)
        overwrites.send_messages = True 
        overwrites.read_messages = True 
        await ctx.channel.set_permissions(unlockrole, overwrite=overwrites)
        
        try:
            await ctx.send(heist_message, allowed_mentions=allowed_mentions)
        except discord.HTTPException:
            pass 

        await asyncio.sleep(sleep_time)
        
        if flags["early-roles"]:
            for r in flags["early-roles"]:
                overwrites = ctx.channel.overwrites_for(r)
                overwrites.send_messages = False
                overwrites.read_messages = False
                await ctx.channel.set_permissions(r, overwrite=overwrites)
        
        overwrites = ctx.channel.overwrites_for(unlockrole)
        overwrites.send_messages = False
        overwrites.read_messages = False
        await ctx.channel.set_permissions(unlockrole, overwrite=overwrites)

        await ctx.send("Times Up. Channel Locked")  