import asyncio
import argparse
from datetime import datetime, timedelta
import discord
from discord.ext import tasks
from discord.utils import sleep_until
from redbot.core import commands, Config
from typing import Optional, Union
from random import choice
from .converters import FuzzyRole
from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class TimeRanOutError(Exception):
    pass


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
            "dmhost": True
        }

        default_member = {
            "hosted": 0,
            "donated": 0,
            "notes": [],
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

#-------------------------------------Functions---------------------------------
    def convert_time(self, time: str):
        conversions = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

        conversion = time[-1]

        if conversion not in conversions:
            return time[:-1]

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
        coros = []

        for guild, data in (await self.config.all_guilds()).items():
            for messageid, info in data["giveaways"].items():
                if info["Ongoing"] == True:
                    coros.append(self.start_giveaway(int(messageid), info))
        await asyncio.gather(*coros)
    
    
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

            e = discord.Embed(
                title=info["title"], description="React with :tada: to enter! \n", color=discord.Color.green())

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
                req = message.guild.get_role(info["requirement"])
                if not req:
                    pass
                else:
                    e.add_field(name="Requirement",
                                value=req.mention, inline=False)

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

        for user in users:
            if user.mention in winners_list:
                continue
            if user.bot:
                continue
            if not requirement:
                winners_list.append(user.mention)
            else:
                role = message.guild.get_role(requirement)
                if role not in user.roles:
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
                role = message.guild.get_role(requirement)
                e.add_field(name="Requirement",
                            value=role.mention, inline=False)
            elif donor:
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
                role = message.guild.get_role(requirement)
                e.add_field(name="Requirement",
                            value=role.mention, inline=False)
            elif donor:
                donor = message.guild.get_member(donor)
                e.add_field(name="Donor", value=donor.mention, inline=False)

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
            final_message += msg.replace("_", " ").replace("-", " ")

        if final_message == "" or len(final_message) == 0:
            return

        else:
            await ctx.send(final_message, allowed_mentions=allowed_mentions)

    async def setnote(self, user: discord.Member, note: str):
        notes = await self.config.member(user).notes()
        notes.append(note)
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
    
    @giveawayset.command(name="clearall")
    async def clearall(self, ctx):
        await self.config.guild(ctx.guild).giveaways.clear()
        await ctx.send("Cleared.")

#-------------------------------------giveaways---------------------------------
    @commands.group(name="giveaway", aliases=["g"])
    @commands.guild_only()
    async def giveaway(self, ctx):
        pass

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
        """Start a giveaway in your server. Flags and Arguments will be explained below.

        Flags:
        --donor: Add a field with the donors mention. Additionally if you store an amount or note for this giveaway it will add to the donors storage.
        --amt: The amount to store for gprofile/gstore. Must be an integer, 50k, 50M, etc are not accepted.
        --note: The note to add to the host/donors notes. This will not accept spaces, if you want spaces, use `-` and `_` and it will subsitute spaces
        --msg: The message to send right after the giveaway starts. It will not take spaces, to add spaces, use `-` or `_` and the bot will replace those with spaces.
        --ping: Specify True or False after this flag, if a pingrole for your server is set, it will ping that role.

        Flags need to be seperated from the normal arguments with `|`
        Specify `none` to the requirement to remove fuzzyrole converters and not have a role requirement
        
        Example:
        `.g start 10m 1 @Owners lots of yummy coins | --ping True --msg I-will-eat-these-coins --donor @Andee#8552 --amt 50000 --note COINS_ARE_YUMMY`
        `.g start 10m 1w none coffee`
        """
        title = title.split("|")
        title = title[0]
        flags = ctx.message.content.split("|")
        winners = winners.rstrip("w")

        if not str(winners).isdigit():
            return await ctx.send(f"I could not get an amount of winners from {winners}")
        winners = int(winners)

        if len(flags) == 1:
            flags = {
                "ping": False,
                "msg": None,
                "donor": None,
                "amt": 0,
                "note": None
            }

        else:
            parser = argparse.ArgumentParser(description="argparse")

            parser.add_argument("--ping", nargs="?", type=bool, default=False,
                                help="Toggles whether to pong the pingrole or not")
            parser.add_argument("--msg", nargs='?', type=str, default=None,
                                help="Sends a message after the giveaway message")
            parser.add_argument("--donor", nargs='?', type=str,
                                default=None, help="Adds a field with the donor")
            parser.add_argument("--amt", nargs='?', type=int,
                                default=0, help="Stores the amount for this giveaway")
            parser.add_argument("--note", nargs='?', type=str, default=None,
                                help="Adds a note to the donor/hosts notes")

            try:
                flags = vars(parser.parse_args(flags[1].split()))
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
                    
            except BaseException as e:
                return await ctx.send("I encountered an error while parsing flags, please check to make sure the types are correct")

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
            roleid = role.id

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
                await self.setnote(ctx.author, flags["note"].replace("_", " ").replace("-", " "))

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

        await self.start_giveaway(int(msg), gaws[msg])
    
    @giveaway.command(name="end")
    @commands.check(is_manager)
    async def g_end(self, ctx, messageid: Optional[int] = None):
        """End a giveaway"""
        if not messageid:
            return await ctx.send("You need to supply a valid message ID for this to work")
        gaws = await self.config.guild(ctx.guild).giveaways()
        if str(messageid) not in gaws:
            return await ctx.send("This isn't a giveaway.")
        elif gaws[str(messageid)]["Ongoing"] == False:
            return await ctx.send(f"This giveaway has ended. You can reroll it with `{ctx.prefix}g reroll {messageid}`")
        else:
            await self.end_giveaway(messageid, gaws[str(messageid)])
    
    @giveaway.command(name="reroll")
    @commands.check(is_manager)
    async def g_reroll(self, ctx, messageid: Optional[int] = None, winners: Optional[int] = 1):
        """Reroll a giveaway"""
        if not messageid:
            return await ctx.send("You need to supply a valid message id.")
        elif winners <= 0:
            return await ctx.send("You can't have no winners.")
        gaws = await self.config.guild(ctx.guild).giveaways()
        if str(messageid) not in gaws:
            return await ctx.send("This giveaway does not exist")
        elif gaws[str(messageid)]["Ongoing"] == True:
            return await ctx.send(f"This giveaway has not yet ended, you can end it with `{ctx.prefix}g end {messageid}`")
        else:
            await self.end_giveaway(messageid, gaws[str(messageid)], winners)
    
    @giveaway.command(name="ping")
    @commands.check(is_manager)
    async def g_ping(self, ctx, * , message: str = None):
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
    
    @giveaway.command(name="list")
    async def g_list(self, ctx, can_join=False):
        async with ctx.typing():
            giveaway_list = []
            counter = 0
            gaws = await self.config.guild(ctx.guild).giveaways()
            for messageid, info in gaws.items():
                counter += 1
                if not info["Ongoing"]:
                    continue
                if not can_join:
                    channel = info["channel"]
                    channel = self.bot.get_channel(channel)
                    if not channel:
                        continue
                    try:
                        m = await channel.fetch_message(messageid)
                    except discord.NotFound:
                        continue
                    title = info["title"]
                    requirement = info["requirement"]
                    if not requirement:
                        header = f"[{title}]({m.jump_url})"
                        header += " :white_check_mark: You can join this giveaway"
                        giveaway_list.append(header)
                        continue
                    req = ctx.guild.get_role(requirement)
                    if not req:
                        continue
                    header = f"[{title}]({m.jump_url})"
                    if req in ctx.author.roles:
                        header += " :white_check_mark: You can join this giveaway"
                    else:
                        header += " :octagonal_sign: You cannot join this giveaway"

                    giveaway_list.append(header)
                else:
                    channel = info["channel"]
                    channel = self.bot.get_channel(channel)
                    if not channel:
                        continue
                    try:
                        m = await channel.fetch_message(messageid)
                    except discord.NotFound:
                        continue 
                    title = info["title"]
                    requirement = info["requirement"]
                    header = f"[{title}]({m.jump_url})"
                    if not requirement:
                        header += " :white_check_mark: You can join this giveaway"
                        giveaway_list.append(header)
                        continue
                    req = ctx.guild.get_role(requirement)
                    if not req:
                        header += " :white_check_mark: You can join this giveaway"
                        giveaway_list.append(header)
                        continue
                    if req in ctx.author.roles:
                        header += " :white_check_mark: You can join this giveaway"
                    else:
                        continue 

                    giveaway_list.append(header)
        
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

#-------------------------------------gprofile---------------------------------

    @commands.group(name="giveawayprofile", aliases=["gprofile"])
    @commands.guild_only()
    async def giveawayprofile(self, ctx):
        if not ctx.invoked_subcommand:
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
    async def gprofile_notes(self, ctx):
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
        pass 
    
    @giveawaystore.command(name="clear")
    async def gstore_clear(self, ctx, member: Optional[discord.Member] = None):
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
        pass
    
    @donate.command(name="add")
    async def donate_add(self, ctx, member: Optional[discord.Member] = None, amt: str = None):
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
        pass 

    @note.command(name="add")
    async def note_add(self, ctx, member: Optional[discord.Member] = None , * , note: str = None):
        if not member:
            return await ctx.send("A member needs to be specified.")
        if not note:
            return await ctx.send("A note needs to be specified.")
        
        notes = await self.config.member(member).notes()
        notes.append(note)
        await self.config.member(member).notes.set(notes)
        await ctx.send("Added a note.")
    
    @note.command(name="remove")
    async def note_remove(self, ctx, member: Optional[discord.Member] = None , * , note: Optional[int] = None):
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

        req = gaws[str(message.id)]["requirement"]
        if not req:
            req = await self.config.guild(message.guild).default_req()
            if not req:
                return
            else:
                req = message.guild.get_role(int(req))
                if not req:
                    await self.config.guild(message.guild).default_req.clear()
                    return
                if req not in user.roles:
                    try:
                        await message.reactions[0].remove(user)
                    except discord.HTTPException:
                        return
                    e = discord.Embed(title="Missing Giveaway Requirement",
                                      description=f"You do not have the `{req.name}` role which is required for [this]({message.jump_url}) giveaway.")
                    await user.send(embed=e)
        else:
            req = message.guild.get_role(int(req))
            if not req:
                await self.config.guild(message.guild).default_req.clear()
                return
            if req not in user.roles:
                try:
                    await message.reactions[0].remove(user)
                except discord.HTTPException:
                    return
                e = discord.Embed(title="Missing Giveaway Requirement",
                                  description=f"You do not have the `{req.name}` role which is required for [this]({message.jump_url}) giveaway.")
                await user.send(embed=e)
