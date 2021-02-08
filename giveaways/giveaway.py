import asyncio
import argparse
from datetime import datetime, timedelta
import discord
from discord.ext import tasks
from discord.message import Message
from discord.utils import sleep_until
from redbot.core import commands, Config
from typing import Optional, Union
from random import choice, randint
from .converters import FuzzyRole, IntOrLink
from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()

async def is_manager(ctx):
    if not ctx.guild:
        return False
    perms = ctx.author.guild_permissions

    if perms.administrator or perms.manage_guild:
        return True

    cog = ctx.bot.get_cog("Giveaways")

    role = await cog.config.guild(ctx.guild).manager()

    if not role:
        return False
    role = ctx.guild.get_role(role)
    if not role:
        await cog.config.guild(ctx.guild).manager.clear()
        return
    if role not in ctx.author.roles:
        return False
    return True


class Giveaways(commands.Cog):
    """A fun cog for giveaways"""

    def __init__(self, bot):
        self.bot = bot
        self.giveaway_task = bot.loop.create_task(self.giveaway_loop())
        self.config = Config.get_conf(
            self, identifier=160805014090190130501014, force_registration=True)

        default_guild = {
            "manager": None,
            "pingrole": None,
            "delete": True,
            "default_req": None,
            "giveaways": {},
            "dmwin": True,
            "dmhost": True,
            "bypassrole": None
        }

        default_member = {
            "hosted": 0,
            "donated": 0,
            "notes": [],
        }

        self.cache = {}

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        

#-------------------------------------Functions---------------------------------
    def convert_time(self, time: str):
        conversions = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

        conversion = time[-1]

        if conversion not in conversions:
            try:
                return int(time)
            except ValueError:
                return 1

        return int(time[:-1]) * conversions[time[-1]]

    def display_time(self, seconds: int) -> str:
        """
        Turns seconds into human readable time.
        """
        message = ''

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

    async def giveaway_loop(self):
        await self.bot.wait_until_ready()
        self.tasks = []

        for guild, data in (await self.config.all_guilds()).items():
            for messageid, info in data["giveaways"].items():
                if info["Ongoing"] == True:
                    self.tasks.append(asyncio.create_task(self.start_giveaway(int(messageid), info)))
    
    
    async def start_giveaway(self, messageid: int, info):
        channel = self.bot.get_channel(info["channel"])

        if not channel:
            return

        try:
            message = await channel.fetch_message(messageid)
        except discord.NotFound:
            return 

        if not message:
            return

        endtime = info["endtime"]

        while True:
            remaining = endtime - datetime.utcnow().timestamp()

            if remaining <= 0:
                await self.end_giveaway(int(messageid), info)
                return
            gaws = await self.config.guild(message.guild).giveaways()

            if str(messageid) not in gaws:
                return

            elif gaws[str(messageid)]["Ongoing"] == False:
                return 

            remaining = datetime.fromtimestamp(endtime) - datetime.utcnow()
            pretty_time = self.display_time(round(remaining.total_seconds()))

            host = message.guild.get_member(info["host"])

            if not host:
                host = "Host Not Found"
            else:
                host = host.mention
        
            if remaining.total_seconds() <= 30:
                color = discord.Color(value=0xFF0000)
            elif remaining.total_seconds() <= 240:
                color = discord.Color.orange()
            elif remaining.total_seconds() <= 600:
                color = discord.Color.dark_green()
            else:
                color = discord.Color.green()

            e = discord.Embed(
                title=info["title"], description="React with :tada: to enter! \n", color=color)

            e.description += f"Time Left: {pretty_time} \n"
            e.description += f"Host: {host}"

            if info["donor"]:
                donor = message.guild.get_member(info["donor"])
                if not donor:
                    donor = "Donor Not Found"
                else:
                    donor = donor.mention

                e.add_field(name="Donor", value=donor, inline=False)

            if info["requirement"]:
                formatted_requirements = ""
                for r in info["requirement"]:
                    role = message.guild.get_role(int(r))
                    if not role:
                        continue 
                    formatted_requirements += f"{role.mention} "
                e.add_field(name="Requirement",
                            value=formatted_requirements, inline=False)
            
            bypassrole = await self.config.guild(message.guild).bypassrole()
            if not bypassrole:
                pass 
            else:
                role = message.guild.get_role(int(bypassrole))
                if not role:
                    await self.config.guild(Message.guild).bypassrole.clear()
                else:
                    e.add_field(name="Bypassrole", value=role.mention, inline=False)

            e.timestamp = datetime.fromtimestamp(endtime)
            winners = info["winners"]
            e.set_footer(text=f"Winners: {winners} | Ends at")

            try:
                await message.edit(embed=e)
            except discord.NotFound:
                return

            await message.add_reaction("🎉")

            await asyncio.sleep(round(remaining.total_seconds()/6))

    async def end_giveaway(self, messageid: int, info, reroll: int = -1):
        channel = self.bot.get_channel(info["channel"])

        if not channel:
            return

        message = await channel.fetch_message(messageid)

        if not message:
            return

        giveaways = await self.config.guild(message.guild).giveaways()
        giveaways[str(messageid)]["Ongoing"] = False
        await self.config.guild(message.guild).giveaways.set(giveaways)

        winners_list = []

        users = await message.reactions[0].users().flatten()

        requirement = info["requirement"]

        winners = info["winners"]

        title = info["title"]

        donor = info["donor"]

        bypassrole = await self.config.guild(message.guild).bypassrole()

        for user in users:
            if user.mention in winners_list:
                continue
            if user.bot:
                continue
            if not requirement:
                winners_list.append(user.mention)
            if bypassrole in [r.id for r in user.roles]:
                winners_list.append(user.mention)
            else:
                holding = False
                for r in requirement:
                    role = message.guild.get_role(r)
                    if not role:
                        continue
                    if role not in user.roles:
                        holding = True
                        break 
                if holding:
                    continue
                else:
                    winners_list.append(user.mention)

        final_list = []

        if reroll == -1:
            pass
        else:
            winners = reroll
        for i in range(winners):
            if len(winners_list) == 0:
                continue
            count = 0
            win = choice(winners_list)
            while win in final_list:
                win = choice(winners_list)
                count += 1
                if count >= 6:
                    break  # for when it runs out of reactions etc.
            final_list.append(win)


        if len(final_list) == 0:
            host = info["host"]
            e = discord.Embed(title=title, description=f"Host: <@{host}> \n Winners: None")
            if requirement:
                formatted_requirements = ""
                for r in requirement:
                    role = message.guild.get_role(r)
                    if not role:
                        continue 
                    formatted_requirements += f"{role.mention} "
                e.add_field(name="Requirement",
                            value=formatted_requirements, inline=False)

            if donor:
                donor = message.guild.get_member(donor)
                e.add_field(name="Donor", value=donor.mention, inline=False)
            await channel.send(f"There were no valid entries for the **{title}** giveaway \n {message.jump_url}")
            await message.edit(content="Giveaway Ended", embed=e)

        else:
            winners = ", ".join(final_list)
            host = info["host"]

            e = discord.Embed(
                title=title,
                description=f"Winner(s): {winners}\nHost: <@{host}>",
            )

            if requirement:
                formatted_requirements = ""
                for r in requirement:
                    role = message.guild.get_role(r)
                    if not role:
                        continue 
                    formatted_requirements += f"{role.mention} "
                e.add_field(name="Requirement",
                            value=formatted_requirements, inline=False)
            if donor:
                donor = message.guild.get_member(donor)
                e.add_field(name="Donor", value=donor.mention, inline=False)
            
            if bypassrole:
                role = message.guild.get_role(int(bypassrole))
                if not role:
                    await self.config.guild(message.guild).bypassrole.clear()
                else:
                    e.add_field(name="Bypassrole", value=role.mention)

            await message.edit(content="Giveaway Ended", embed=e)
            await message.channel.send(f"The winners for the **{title}** giveaway are \n{winners}\n{message.jump_url}")

            dmhost = await self.config.guild(message.guild).dmhost()
            dmwin = await self.config.guild(message.guild).dmwin()
            if dmhost:
                host = message.guild.get_member(int(host))
                if not host:
                    pass 
                else:
                    e = discord.Embed(
                        title=f"Your giveaway has ended",
                        description=f"Your giveaway for {title} in {message.guild.name} has ended. The winners were {winners}.\n [Click here for the original message]({message.jump_url})"
                    )
                    await host.send(embed=e)
            if dmwin:
                for mention in final_list:
                    mention = message.guild.get_member(int(mention.lstrip("<@!").lstrip("<@").rstrip(">")))
                    if not mention:
                        continue
                    e = discord.Embed(
                        title=f"You won a giveaway!",
                        description=f"You won the giveaway for {title} in {message.guild.name}.\n[Click here for the original message]({message.jump_url})"
                    )
                    await mention.send(embed=e)

    def cog_unload(self):
        self.giveaway_task.cancel()
        for task in self.tasks:
            task.cancel()

    async def send_final_message(self, ctx, ping, msg):
        allowed_mentions = discord.AllowedMentions(roles=True, everyone=False)
        final_message = ""
        if ping:
            pingrole = await self.config.guild(ctx.guild).pingrole()
            if not pingrole:
                pass
            else:
                role = ctx.guild.get_role(int(pingrole))
                if not role:
                    await self.config.guild(ctx.guild).pingrole.clear()
                else:
                    final_message += role.mention
                    final_message += " "

        if msg:
            final_message += " ".join(msg)

        if final_message == "" or len(final_message) == 0:
            return

        else:
            await ctx.send(final_message, allowed_mentions=allowed_mentions)

    async def setnote(self, user: discord.Member, note: list):
        notes = await self.config.member(user).notes()
        notes.append(" ".join(note))
        await self.config.member(user).notes.set(notes)

    async def add_amount(self, user: discord.Member, amt: int):
        previous = await self.config.member(user).donated()
        previous += amt
        await self.config.member(user).donated.set(previous)
#-------------------------------------gset---------------------------------

    @commands.group(name="giveawayset", aliases=["gset"])
    @commands.guild_only()
    async def giveawayset(self, ctx):
        """Set your server settings for giveaways"""
        pass

    @giveawayset.command(name="manager")
    @commands.admin_or_permissions(administrator=True)
    async def manager(self, ctx, role: Optional[discord.Role] = None):
        """Set the role that can create giveaways, end them, and reroll them"""
        if not role:
            return await ctx.send("This isn't a role.")

        await self.config.guild(ctx.guild).manager.set(role.id)

        await ctx.send(f"**{role.name}** can now create giveaways, end them, and reroll them")

    @giveawayset.command(name="pingrole")
    @commands.admin_or_permissions(administrator=True)
    async def cmd_pingrole(self, ctx, role: Optional[discord.Role] = None):
        """Set the role to ping if a ping is used"""
        if not role:
            return await ctx.send("This isn't a role")

        await self.config.guild(ctx.guild).pingrole.set(role.id)

        await ctx.send(f"**{role.name}** will now be pinged if a ping is specified")

    @giveawayset.command(name="defaultrequirement", aliases=["requirement", "defaultreq"])
    @commands.admin_or_permissions(administrator=True)
    async def defaultrequirement(self, ctx, role: Optional[discord.Role] = None):
        """The default requirement for giveaways"""
        if not role:
            await self.config.guild(ctx.guild).default_req.clear()
            return await ctx.send("I will no longer have default requirements")

        await self.config.guild(ctx.guild).default_req.set(role.id)

        await ctx.send(f"The default role requirement is now **{role.name}**")

    @giveawayset.command(name="delete")
    @commands.admin_or_permissions(administrator=True)
    async def cmd_delete(self, ctx, delete: Optional[bool] = True):
        """Toggle whether to delete the giveaway creation message"""
        if not delete:
            await self.config.guild(ctx.guild).delete.set(False)
            await ctx.send("I will no longer delete invocation messages when creating giveaways")
        else:
            await self.config.guild(ctx.guild).delete.set(True)
            await ctx.send("I will now delete invocation messages when creating giveaways")
    
    @giveawayset.command(name="dmhost")
    async def dmhost(self, ctx, dmhost: Optional[bool] = True):
        """Toggle whether to DM the host when the giveaway ends"""
        if not dmhost:
            await self.config.guild(ctx.guild).dmhost.set(False)
            await ctx.send("I will no longer dm hosts")
        else:
            await self.config.guild(ctx.guild).dmhost.set(True)
            await ctx.send("I will now dm hosts")
    
    @giveawayset.command(name="dmwin")
    async def dmwin(self, ctx, dmwin: Optional[bool] = True):
        """Toggles whether to DM the winners of the giveaway"""
        if not dmwin:
            await self.config.guild(ctx.guild).dmwin.set(False)
            await ctx.send("I will no longer dm winners")
        else:
            await self.config.guild(ctx.guild).dmwin.set(True)
            await ctx.send("I will now dm winners")
    
    @giveawayset.command(name="bypassrole", aliases=["aarole", "bprole", "alwaysallowedrole"])
    async def bypassrole(self, ctx, role: Optional[discord.Role] = None):
        """Set the role that can bypass all giveaway requirements"""
        if not role:
            await self.config.guild(ctx.guild).bypassrole.clear()
            await ctx.send("Cleared the bypass role")
        else:
            await self.config.guild(ctx.guild).bypassrole.set(role.id)
            await ctx.send(f"Your bypass role is now **{role}**")

#-------------------------------------giveaways---------------------------------
    @commands.group(name="giveaway", aliases=["g"])
    @commands.guild_only()
    async def giveaway(self, ctx):
        pass
    
    @giveaway.command(name="clearended")
    @commands.admin_or_permissions(manage_guild=True)
    async def clearended(self, ctx, *dontclear):
        """Clear the giveaways that have already ended in your server. Put all the message ids you dont want to clear after this to not clear them"""
        gaws = await self.config.guild(ctx.guild).giveaways()
        to_delete = []
        for messageid, info in gaws.items():
            if str(messageid) in dontclear:
                continue
            if not info["Ongoing"]:
                to_delete.append(str(messageid))
        
        for messageid in to_delete:
            gaws.pop(messageid)
        await self.config.guild(ctx.guild).giveaways.set(gaws)
        await ctx.send("Done.")
    
    @giveaway.command(name="help")
    async def g_help(self, ctx):
        """Explanation on how to start a giveaway"""
        e = discord.Embed(
            title="Giveaway Help",
            color=discord.Color.blurple(),
            description="Start a giveaway in your server. Flags and Arguments will be explained below."
        )
        e.description += """
        Flags:
        --donor: Add a field with the donors mention. Additionally if you store an amount or note for this giveaway it will add to the donors storage.
        --amt: The amount to store for gprofile/gstore. Must be an integer, 50k, 50M, etc are not accepted.
        --note: The note to add to the host/donors notes. 
        --msg: The message to send right after the giveaway starts. 
        --ping: Specify True or False after this flag, if a pingrole for your server is set, it will ping that role.

        Specify `none` to the requirement to remove fuzzyrole converters and not have a role requirement
        Multiple requirements need to be split with `;;`
        
        Example:
        `.g start 10m 1 @Owners lots of yummy coins --ping True --msg I will eat these coins --donor @Andee#8552 --amt 50000 --note COINS ARE YUMMY`
        `.g start 10m 1w none coffee`
        `.g start 10m 1w GiveawayPing;;Admin;;Mod food`

        """
        await ctx.send(embed=e)

    @giveaway.command(name="start")
    @commands.check(is_manager)
    async def g_start(
        self,
        ctx,
        time: str,
        winners: str = "1",
        role: Optional[FuzzyRole] = None,
        *,
        title="Giveaway!",

    ):
        """Start a giveaway in your server. Flags and Arguments are explained with .giveaway help
        """
        title = title.split("--")
        title = title[0]
        flags = ctx.message.content
        winners = winners.rstrip("w")

        if not str(winners).isdigit():
            return await ctx.send(f"I could not get an amount of winners from {winners}")
        winners = int(winners)
        if winners < 0:
            return await ctx.send("Can've have less than 1 winner")

        if len(flags) == 2:
            flags = {
                "ping": False,
                "msg": None,
                "donor": None,
                "amt": 0,
                "note": None
            }

        else:
            parser = NoExitParser(description="argparse", add_help=False)

            parser.add_argument("--ping", nargs="?", type=bool, default=False,
                                help="Toggles whether to pong the pingrole or not")
            parser.add_argument("--msg", nargs='*', type=str, default=None,
                                help="Sends a message after the giveaway message")
            parser.add_argument("--donor", nargs='?', type=str,
                                default=None, help="Adds a field with the donor")
            parser.add_argument("--amt", nargs='?', type=int,
                                default=0, help="Stores the amount for this giveaway")
            parser.add_argument("--note", nargs='*', type=str, default=None,
                                help="Adds a note to the donor/hosts notes")

            try:
                flags, uk = parser.parse_known_args(flags.split())
                flags = vars(flags)

                if flags["donor"]:
                    donor = flags["donor"].lstrip("<@!").lstrip("<@").rstrip(">")
                    if str(donor).isdigit():
                        donor = ctx.guild.get_member(int(donor))
                    else:
                        donor = discord.utils.get(ctx.guild.members, name=donor)
                    if not donor:
                        return await ctx.send("The donor provided is not valid")
                    flags["donor"] = donor.id
                else:
                    pass
                    
            except Exception as exc:
                raise BadArgument() from exc

        guild = ctx.guild
        data = await self.config.guild(guild).all()

        gaws = await self.config.guild(guild).giveaways()

        if not role:
            role = data["default_req"]
            if not role:
                roleid = None
            else:
                role = ctx.guild.get_role(role)
                roleid = role.id
        else:
            roleid = [r.id for r in role]

        e = discord.Embed(
            title=title,
            description=f"Hosted By: {ctx.author.mention}",
            timestamp=datetime.utcnow(),
            color=discord.Color.green(),
        )

        e.set_footer(text="Ending at")

        time = self.convert_time(time)
        ending_time = datetime.utcnow().timestamp() + float(time)
        ending_time = datetime.fromtimestamp(ending_time)
        pretty_time = self.display_time(time)

        e.description += f"\n Time Left: {pretty_time}"
        e.timestamp = ending_time

        gaw_msg = await ctx.send(embed=e)

        msg = str(gaw_msg.id)

        gaws[msg] = {}
        gaws[msg]["host"] = ctx.author.id
        gaws[msg]["Ongoing"] = True
        gaws[msg]["requirement"] = roleid
        gaws[msg]["winners"] = winners
        gaws[msg]["title"] = title
        gaws[msg]["endtime"] = datetime.utcnow().timestamp() + float(time)
        gaws[msg]["channel"] = ctx.channel.id
        gaws[msg]["donor"] = flags["donor"]

        await self.config.guild(guild).giveaways.set(gaws)

        delete = await self.config.guild(ctx.guild).delete()

        if ctx.channel.permissions_for(ctx.me).manage_messages and delete:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass

        await self.send_final_message(ctx, flags["ping"], flags["msg"])

        if flags["note"]:
            if flags["donor"]:
                await self.setnote(ctx.guild.get_member(flags["donor"]), flags["note"])
            else:
                await self.setnote(ctx.author, flags["note"])

        if flags["amt"]:
            if flags["donor"]:
                await self.add_amount(ctx.guild.get_member(flags["donor"]), flags["amt"])
            else:
                await self.add_amount(ctx.author, flags["amt"])
        
        if flags["donor"]:
            hosted = await self.config.member(ctx.guild.get_member(flags["donor"])).hosted()
            hosted += 1
            await self.config.member(ctx.guild.get_member(flags["donor"])).hosted.set(hosted)
        else:
            prev = await self.config.member(ctx.author).hosted()
            prev += 1
            await self.config.member(ctx.author).hosted.set(prev)

        self.cache[str(msg)] = gaw_msg 
        
        await self.start_giveaway(int(msg), gaws[msg])
    
    @giveaway.command(name="end")
    @commands.check(is_manager)
    async def end(self, ctx, messageid: Optional[IntOrLink] = None):
        gaws = await self.config.guild(ctx.guild).giveaways()
        """End a giveaway"""
        if messageid is None:
            for messageid, info in list(gaws.items())[::-1]:
                if info["channel"] == ctx.channel.id and info["Ongoing"]:
                    await self.end_giveaway(messageid, info)
                    return 
            return await ctx.send("There aren't any giveaways in this channel, specify a message id/link to end another channels giveaways")
        gaws = await self.config.guild(ctx.guild).giveaways()
        if str(messageid) not in gaws:
            return await ctx.send("This isn't a giveaway.")
        elif gaws[str(messageid)]["Ongoing"] == False:
            return await ctx.send(f"This giveaway has ended. You can reroll it with `{ctx.prefix}g reroll {messageid}`")
        else:
            await self.end_giveaway(messageid, gaws[str(messageid)])
    
    @giveaway.command(name="reroll")
    @commands.check(is_manager)
    async def reroll(self, ctx, messageid: Optional[IntOrLink], winners: Optional[int] = 1):
        """Reroll a giveaway"""
        gaws = await self.config.guild(ctx.guild).giveaways()
        if not messageid:
            for messageid, info in list(gaws.items())[::-1]:
                if info["channel"] == ctx.channel.id and info["Ongoing"] == False:
                    await self.end_giveaway(messageid, info)
                    return 
            return await ctx.send("There aren't any giveaways in this channel, specify a message id/link to end another channels giveaways")
        elif winners <= 0:
            return await ctx.send("You can't have no winners.")
        if str(messageid) not in gaws:
            return await ctx.send("This giveaway does not exist")
        elif gaws[str(messageid)]["Ongoing"] == True:
            return await ctx.send(f"This giveaway has not yet ended, you can end it with `{ctx.prefix}g end {messageid}`")
        else:
            await self.end_giveaway(messageid, gaws[str(messageid)], winners)
    
    @giveaway.command(name="ping")
    @commands.check(is_manager)
    async def g_ping(self, ctx, * , message: str = None):
        """Ping the pingrole for your server with an optional message, it wont send anything if there isn't a pingrole"""
        m = discord.AllowedMentions(roles=True, everyone=False)
        await ctx.message.delete()
        pingrole = await self.config.guild(ctx.guild).pingrole()
        if not pingrole:
            try:
                return await ctx.send(message, allowed_mentions=m)
            except discord.HTTPException:
                return 
        role = ctx.guild.get_role(pingrole)
        if not role:
            await self.config.guild(ctx.guild).pingrole.clear()
            try:
                return await ctx.send(message, allowed_mentions=m)
            except discord.HTTPException:
                return 
        try:
            await ctx.send(f"{role.mention} {message}", allowed_mentions=m)
        except discord.HTTPException:
            return 
    
    @giveaway.command(name="cache")
    @commands.is_owner()
    async def cache(self, ctx, active: bool = True):
        """Owner Utility to force a cache on a server in case something broke or you reloaded the cog and need it needs to be cached"""
        async with ctx.typing():
            msg = await ctx.send("0 giveaways cached")
            counter = 0
            for messageid, info in (await self.config.guild(ctx.guild).giveaways()).items():
                counter += 1
                if active:
                    if info["Ongoing"] == False:
                        continue 
                    
                if counter % 25 == 0:
                    await msg.edit(content=f"{counter} messages cached")
                if messageid not in self.cache:
                    messageid = str(messageid)
                    channel = self.bot.get_channel(info["channel"])
                    try:
                        m = await channel.fetch_message(int(messageid))
                    except discord.NotFound:
                        continue 
                    self.cache[messageid] = m
        
        await ctx.send("Cached")
    
    @giveaway.command(name="list")
    @commands.cooldown(1, 30, commands.BucketType.member)
    @commands.max_concurrency(2, commands.BucketType.user)
    async def g_list(self, ctx, can_join: bool = False):
        """List the giveways in the server. Specify True for can_join paramater to only list the ones you can join"""
        async with ctx.typing():
            giveaway_list = []
            counter = 0
            gaws = await self.config.guild(ctx.guild).giveaways()
            startmessage = await ctx.send("0 giveaways gathered")
            for messageid, info in gaws.items():
                messageid = str(messageid)
                try:
                    if counter % 10 == 0:
                        await startmessage.edit(content=f"{counter} messages out of {len(gaws.values())} messages gathered")
                except ZeroDivisionError:
                    pass
                counter += 1
                if not info["Ongoing"]:
                    continue
                if not can_join:
                    channel = info["channel"]
                    channel = self.bot.get_channel(channel)
                    if not channel:
                        continue
                    m = self.cache.get(messageid, ctx.bot._connection._get_message(int(messageid)))
                    if not m:
                        try:
                            m = await channel.fetch_message(int(messageid))
                            self.cache[messageid] = m
                        except discord.NotFound:
                            deleted_gaws = await self.config.guild(ctx.guild).giveaways()
                            deleted_gaws.pop(messageid)
                            await self.config.guild(ctx.guild).giveaways.set(deleted_gaws)
                            continue
                        
                    title = info["title"]
                    requirement = info["requirement"]
                    header = f"[{title}]({m.jump_url})"
                    header += " | Winners: {0} | Host: <@{1}>".format(info["winners"], info["host"])
                    header += " | Channel: <#{0}> | ID: {1}".format(info["channel"], messageid)
                    if len(requirement) == 0:
                        header += " :white_check_mark: You can join this giveaway\n"
                        giveaway_list.append(header)
                        continue

                    for r in requirement:
                        r = ctx.guild.get_role(r)
                        if not r:
                            continue 
                        if r not in ctx.author.roles:
                            header += " :octagonal_sign: You cannot join this giveaway\n"
                            giveaway_list.append(header)
                            break
                    if ":octagonal_sign:" in header:
                        continue 
                    header += " :white_check_mark: You can join this giveaway\n"
                    
                    giveaway_list.append(header)
                else:
                    channel = info["channel"]
                    channel = self.bot.get_channel(channel)
                    if not channel:
                        continue
                    m = self.cache.get(messageid, ctx.bot._connection._get_message(int(messageid)))
                    if not m:
                        try:
                            m = await channel.fetch_message(int(messageid))
                            self.cache[messageid] = m
                        except discord.NotFound:
                            deleted_gaws = await self.config.guild(ctx.guild).giveaways()
                            deleted_gaws.pop(messageid)
                            await self.config.guild(ctx.guild).giveaways.set(deleted_gaws)
                            continue

                    title = info["title"]
                    requirement = info["requirement"]
                    header = f"[{title}]({m.jump_url})"
                    header += " | Winners: {0} | Host: <@{1}>".format(info["winners"], info["host"])
                    header += " | Channel: <#{0}> | ID: {1}".format(info["channel"], messageid)
                    holding = True
                    for r in requirement:
                        r = ctx.guild.get_role(r)
                        if not r:
                            continue 
                        if r not in ctx.author.roles:
                            holding = False 
                            continue 
                    
                    if not holding:
                        continue
                    header += " :white_check_mark: You can join this giveaway\n"

                    giveaway_list.append(header)
        
        await startmessage.delete()
        
        formatted_giveaways = "\n".join(giveaway_list)
        if len(formatted_giveaways) > 2048:
            pages = list(pagify(formatted_giveaways))
            embeds = []
            
            for i, page in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Giveaways Page {i}/{len(pages)}",
                    description=page,
                    color=discord.Color.green()
                )
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title="Giveaway Page 1",
                description=formatted_giveaways,
                color=discord.Color.green()
            )
            await ctx.send(embed=e)
    
    @giveaway.command(name="cancel")
    @commands.check(is_manager)
    async def cancel(self, ctx, giveaway: Optional[IntOrLink] = None):
        """Cancel a giveaway"""
        gaws = await self.config.guild(ctx.guild).giveaways()
        if not giveaway:
            for messageid, info in list(gaws.items())[::-1]:
                if info["Ongoing"] and info["channel"] == ctx.channel.id:
                    chan = self.bot.get_channel(info["channel"])
                    if not chan:
                        continue
                    try:
                        m = self.cache.get(giveaway, await chan.fetch_message(int(messageid)))
                    except discord.NotFound:
                        continue 

                    e = discord.Embed(
                        title=info["title"],
                        description=f"Giveaway Cancelled\n",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    e.description += "Hosted By: <@{0}>\nCancelled By: {1}".format(info["host"], ctx.author.mention)
                    e.set_footer(text="Cancelled at")

                    try:
                        await m.edit(content="Giveaway Cancelled", embed=e)
                    except discord.NotFound:
                        continue
                    info["Ongoing"] = False 
                    gaws[messageid] = info
                    await self.config.guild(ctx.guild).giveaways.set(gaws)
                    return await ctx.send("Cancelled the giveaway for **{0}**".format(info["title"]))

            return await ctx.send("There are no active giveaways in this channel to be cancelled, specify a message id/link after this in another channel to cancel one")
        giveaway = str(giveaway)
        if giveaway not in gaws.keys():
            return await ctx.send("This giveaway does not exist")
        if not gaws[giveaway]["Ongoing"]:
            return await ctx.send("This giveaway has ended")
        
        data = gaws[giveaway]
        chan = self.bot.get_channel(data["channel"])
        if not chan:
            return await ctx.send("This message is no longer available")
        try:
            m = self.cache.get(giveaway, await chan.fetch_message(int(giveaway)))
        except discord.NotFound:
            return await ctx.send("Couldn't find this giveaway")

        gaws[giveaway]["Ongoing"] = False 
        await self.config.guild(ctx.guild).giveaways.set(gaws)

        e = discord.Embed(
            title=data["title"],
            description=f"Giveaway Cancelled\n",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        e.description += "Hosted By: <@{0}>\nCancelled By: {1}".format(data["host"], ctx.author.mention)
        e.set_footer(text="Cancelled at")
        try:
            await m.edit(content="Giveaway Cancelled", embed=e)
        except discord.NotFound:
            return await ctx.send("I couldn't find this giveaway")
        gaws[giveaway]["Ongoing"] = False 
        await self.config.guild(ctx.guild).gaws.set(gaws)
        await ctx.send("Cancelled the giveaway for **{0}**").format(data["title"])
        
        
#-------------------------------------gprofile---------------------------------

    @commands.group(name="giveawayprofile", aliases=["gprofile"], invoke_without_command=True)
    @commands.guild_only()
    async def giveawayprofile(self, ctx, member: Optional[discord.Member] = None):
        """View your giveaway donations and notes"""
        if not ctx.invoked_subcommand:
            if not member:
                pass 
            else:
                ctx.author = member
            donated = await self.config.member(ctx.author).donated()
            format_donated = "{:,}".format(donated)
            notes = await self.config.member(ctx.author).notes()
            hosted = await self.config.member(ctx.author).hosted()
            try:
                average_donated = "{:,}".format(round(donated/hosted))
            except ZeroDivisionError:
                average_donated = 0

            e = discord.Embed(title="Donated", description=f"Giveaways Hosted: {hosted} \n", color=ctx.author.color)
            e.description += f"Amount Donated: {format_donated} \n"
            e.description += f"Average Donation Value: {average_donated}"
            
            if len(notes) == 0:
                pass 
            else:
                e.set_footer(text=f"{len(notes)} notes")
            
            await ctx.send(embed=e)
    
    @giveawayprofile.command(name="notes")
    async def gprofile_notes(self, ctx, member: Optional[discord.Member] = None):
        """View your giveaway notes"""
        if member:
            ctx.author = member
        notes = await self.config.member(ctx.author).notes()
        if len(notes) == 0:
            return await ctx.send("You have no notes")

        formatted_notes = []

        for i, note in enumerate(notes, start=1):
            formatted_notes.append(f"{i}. {note}")
        
        formatted_notes = "\n\n".join(formatted_notes)

        if len(formatted_notes) >= 2048:
            embeds = []
            pages = list(pagify(formatted_notes))
            for i, page in enumerate(pages, start=1):
                e = discord.Embed(
                    title="Notes", 
                    description=page, 
                    color=ctx.author.color
                )
                e.set_footer(text=f"{i} out of {len(pages)} pages.")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title="Notes",
                description=formatted_notes,
                color=ctx.author.color
            )
            await ctx.send(embed=e)

#-------------------------------------gstore---------------------------------

    @commands.group(name="giveawaystore", aliases=["gstore"])
    @commands.check(is_manager)
    async def giveawaystore(self, ctx):
        """Manage donation and note tracking for members"""
        pass 
    
    @giveawaystore.command(name="clear")
    async def gstore_clear(self, ctx, member: Optional[discord.Member] = None):
        """Clear everything for a member"""
        if not member:
            return await ctx.send("A member needs to be specified after this")
        else:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            await ctx.send(f"Are you sure? This will clear all of **{member.name}'s** data. Type `YES I WANT TO DO THIS` exact below if you are sure")
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=20)
            except asyncio.TimeoutError:
                return await ctx.send(f"Looks like we won't be removing **{member.name}'s** data.")
            
            if msg.content != "YES I WANT TO DO THIS":
                return await ctx.send(f"Looks like we won't clear **{member.name}**'s data.")
            await self.config.member(member).clear()
            await ctx.send(f"I've removed **{member.name}**'s data")
    
    @giveawaystore.group(name="donate")
    async def donate(self, ctx):
        """A group for managing giveway donations/amounts"""
        pass
    
    @donate.command(name="add")
    async def donate_add(self, ctx, member: Optional[discord.Member] = None, amt: str = None):
        """Add an amount to a users donations"""
        if not member:
            return await ctx.send("A member needs to be specified after this")
        if not amt:
            return await ctx.send("You need to specify an amount to donate")
        amt = amt.replace(",", "")

        if not str(amt).isdigit():
            return await ctx.send("This isn't a number.")
        
        previous_amount = await self.config.member(member).donated()
        new_amount = int(amt) + previous_amount 
        await self.config.member(member).donated.set(new_amount)
        await ctx.send("Done.")
    
    @donate.command(name="remove")
    async def donate_remove(self, ctx, member: Optional[discord.Member] = None, amt: str = None):
        """Remove a certain amount from a members donation amount"""
        if not member:
            return await ctx.send("A member needs to be specified after this")
        if not amt:
            return await ctx.send("You need to specify an amount to donate")
        amt = amt.replace(",", "")

        if not str(amt).isdigit():
            return await ctx.send("This isn't a number.")
        
        previous_amount = await self.config.member(member).donated()
        new_amount = previous_amount - int(amt)
        if new_amount < 0:
            return await ctx.send("You can't go below 0")
        await self.config.member(member).donated.set(new_amount)
        await ctx.send("Done.")
    
    @giveawaystore.group(name="note")
    async def note(self, ctx):
        """A group for managing giveaway notes"""
        pass 

    @note.command(name="add")
    async def note_add(self, ctx, member: Optional[discord.Member] = None , * , note: str = None):
        """Add a note to a member"""
        if not member:
            return await ctx.send("A member needs to be specified.")
        if not note:
            return await ctx.send("A note needs to be specified.")
        
        notes = await self.config.member(member).notes()
        notes.append(note)
        await self.config.member(member).notes.set(notes)
        await ctx.send("Added a note.")
    
    @note.command(name="remove")
    async def note_remove(self, ctx, member: Optional[discord.Member] = None , note: Optional[int] = None):
        """Remove a note from a member, you can do `[p]gprofile notes @member` to find the note ID, and specify that for the note param"""
        if not member:
            return await ctx.send("A member needs to be specified.")
        if not note:
            return await ctx.send("A note ID needs to be specified.")
        
        notes = await self.config.member(member).notes()
        if note > len(notes):
            return await ctx.send("This note does not exist")
        else:
            notes.pop(note-1)
        await self.config.member(member).notes.set(notes)
        await ctx.send("Removed a note.")
    


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = message.guild.get_member(payload.user_id)
        if user.bot:
            return
        gaws = await self.config.guild(message.guild).giveaways()
        if str(message.id) not in gaws:
            return
        elif gaws[str(message.id)]["Ongoing"] == False:
            return
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        if str(payload.emoji) != "🎉": 
            return
        
        bypassrole = await self.config.guild(message.guild).bypassrole()
        if bypassrole in [r.id for r in user.roles]:
            return 

        req = gaws[str(message.id)]["requirement"]
        if not req:
            req = await self.config.guild(message.guild).default_req()
            if not req:
                return
            else:
                for r in req:
                    r = message.guild.get_role(int(r))
                    if not req:
                        await self.config.guild(message.guild).default_req.clear()
                        return
                    if req not in user.roles:
                        try:
                            await message.reactions[0].remove(user)
                        except discord.HTTPException:
                            return
                        e = discord.Embed(title="Missing Giveaway Requirement",
                                        description=f"You do not have the `{r.name}` role which is required for [this]({message.jump_url}) giveaway.")
                        await user.send(embed=e)
                        return 
        else:
            for r in req:
                r = message.guild.get_role(int(r))
                if not r:
                    await self.config.guild(message.guild).default_req.clear()
                    return
                if r not in user.roles:
                    try:
                        await message.reactions[0].remove(user)
                    except discord.HTTPException:
                        return
                    e = discord.Embed(title="Missing Giveaway Requirement",
                                    description=f"You do not have the `{r.name}` role which is required for [this]({message.jump_url}) giveaway.")
                    await user.send(embed=e)
                    return 
