import asyncio
import argparse
from datetime import datetime, timedelta
import discord
from discord.ext import tasks
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
        raise BadArgument(message)


async def is_manager(ctx):
    if ctx.channel.permissions_for(ctx.author).administrator or ctx.channel.permissions_for(ctx.author).manage_guild:
        return True
    if (await ctx.bot.is_owner(ctx.author)):
        return True

    cog = ctx.bot.get_cog("Giveaways")

    role = await cog.config.guild(ctx.guild).manager()

    if ctx.guild is None:
        return False
    for r in role:
        if r in [role.id for role in ctx.author.roles]:
            return True


class Giveaways(commands.Cog):
    """A fun cog for giveaways"""

    def __init__(self, bot):
        self.bot = bot
        self.giveaway_task = bot.loop.create_task(self.giveaway_loop())
        self.config = Config.get_conf(
            self,
            identifier=160805014090190130501014,
            force_registration=True
        )

        default_guild = {
            "manager": [],
            "pingrole": None,
            "blacklist": [],
            "delete": False,
            "default_req": None,
            "giveaways": {},
            "dmwin": False,
            "dmhost": False,
            "startHeader": "**{giveawayEmoji}   GIVEAWAY   {giveawayEmoji}**",
            "endHeader": "**{giveawayEmoji}   GIVEAWAY ENDED   {giveawayEmoji}**",
            "description": "React with {emoji} to enter",
            "bypassrole": [],
            "winmessage": "You won the giveaway for [{prize}]({url}) in {guild}!",
            "hostmessage": "Your giveaway for [{prize}]({url}) in {guild} has ended. The winners were {winners}",
            "emoji": "🎉",
        }

        default_member = {
            "hosted": 0,
            "donated": 0,
            "notes": [],
        }

        default_global = {
            "secretblacklist": []
        }

        self.message_cache = {}
        self.giveaway_cache = {}

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.config.register_global(**default_global)


# -------------------------------------Functions---------------------------------

    def convert_time(self, time: str):
        conversions = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

        conversion = time[-1]

        if conversion not in conversions:
            try:
                return int(time)
            except ValueError:
                return 5

        return int(time[:-1]) * conversions[time[-1]]
    
    def comma_format(self, number: int):
        return "{:,}".format(number)

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

    async def giveaway_loop(self):
        await self.bot.wait_until_ready()
        self.tasks = []

        for guild, data in (await self.config.all_guilds()).items():
            for messageid, info in data["giveaways"].items():
                if info["Ongoing"]:
                    self.tasks.append(asyncio.create_task(
                        self.start_giveaway(int(messageid), info)))

    async def can_join(self, user: discord.Member, info):
        data = await self.config.guild(user.guild).all()
        secretblacklist = await self.config.secretblacklist()
        if user.id in secretblacklist:
            return False
        if len(data["bypassrole"]) == 0:
            pass
        else:
            for r in data["bypassrole"]:
                if r in [r.id for r in user.roles]:
                    return True
        if len(data["blacklist"]) == 0:
            pass
        else:
            for r in data["blacklist"]:
                if r in [r.id for r in user.roles]:
                    return False
        if not info["requirement"] or len(info["requirement"]) == 0:
           return True
        for r in info["requirement"]:
            if r in [role.id for role in user.roles]:
                continue
            return False

        return True

    def get_color(self, timeleft: int):
        if timeleft <= 30:
           return discord.Color(value=0xFF0000)
        elif timeleft <= 240:
           return discord.Color.orange()
        elif timeleft <= 600:
            return discord.Color(value=0xFFFF00)
        return discord.Color.green()

    async def start_giveaway(self, messageid: int, info):
        channel = self.bot.get_channel(info["channel"])
        self.bot._connection._get_message(int(messageid))
        if not channel:
            return

        message = self.message_cache.get(
            str(messageid), self.bot._connection._get_message(int(messageid)))

        if not message:
            try:
                message = await channel.fetch_message(messageid)
            except discord.NotFound:
                return

        self.message_cache[str(messageid)] = message

        bypassrole = await self.config.guild(message.guild).bypassrole()
        data = await self.config.guild(message.guild).all()

        while True:
            remaining = info["endtime"] - datetime.utcnow().timestamp()
            gaws = await self.config.guild(message.guild).giveaways()
            if str(messageid) not in gaws:
                return 
            elif not gaws[str(messageid)]["Ongoing"]:
                return

            elif remaining <= 0:
                self.message_cache[str(messageid)] = await channel.fetch_message(messageid)
                await self.end_giveaway(int(messageid), info)
                return


            remaining = datetime.fromtimestamp(
                info["endtime"]) - datetime.utcnow()
            pretty_time = self.display_time(round(remaining.total_seconds()))

            host = message.guild.get_member(info["host"])

            if not host:
                host = "Host Not Found"
            else:
                host = host.mention

            color = self.get_color(remaining.total_seconds())

            e = discord.Embed(
                title=info["title"], description=data["description"].replace("{emoji}", data["emoji"]), color=color)
            e.description += f"\nTime Left: {pretty_time} \n"
            e.description += f"Host: {host}"

            if info["donor"]:
                e.add_field(
                    name="Donor", value="<@{0}>".format(info["donor"]), inline=False)

            if info["requirement"]:
                requirements = []
                for r in info["requirement"]:
                    requirements.append(f"<@&{r}>")
                e.add_field(name="Requirement", value=", ".join(
                    requirements), inline=False)

            if bypassrole:
                roles = []
                for r in bypassrole:
                    roles.append("<@&{0}>".format(r))
                e.add_field(name="Bypassrole", value=", ".join(roles))

            e.timestamp = datetime.fromtimestamp(info["endtime"])
            e.set_footer(
                text="Winners: {0} | Ends at".format(info["winners"]))

            try:
                await message.edit(embed=e, content=data["startHeader"].replace("{giveawayEmoji}", data["emoji"]))
            except discord.NotFound:
                return

            emoji = data["emoji"]
            await message.add_reaction(emoji)
            self.message_cache[str(messageid)] = message

            await asyncio.sleep(round(remaining.total_seconds()/6))

    async def end_giveaway(self, messageid: int, info, reroll: int = -1):
        channel = self.bot.get_channel(info["channel"])

        if not channel:
            return

        message = self.bot._connection._get_message(int(messageid))

        if not message:
            try:
                message = await channel.fetch_message(messageid)
            except discord.NotFound:
                giveaways = await self.config.guild(channel.guild).giveaways()
                giveaways.pop(str(messageid))
                await self.config.guild(channel.guild).giveaways.set(giveaways)
                return 

        giveaways = await self.config.guild(message.guild).giveaways()
        giveaways[str(messageid)]["Ongoing"] = False
        self.giveaway_cache[str(messageid)] = False
        await self.config.guild(message.guild).giveaways.set(giveaways)

        winners_list = []

        users = []
        data = await self.config.guild(message.guild).all()
        for i, r in enumerate(message.reactions):
            if str(r) == data["emoji"]:
                users = await message.reactions[i].users().flatten()
                break
    
        if users == [None]:
            return 
            
        bypassrole = await self.config.guild(message.guild).bypassrole()

        for user in users:
            if user.mention in winners_list:
                continue
            if user.bot:
                continue
            if (await self.can_join(user, info)):
                winners_list.append(user.mention)

        final_list = []

        if reroll == -1:
            winners = info["winners"]
        else:
            winners = reroll

        for i in range(winners):
            if len(winners_list) == 0:
                continue
            count = 0
            win = choice(winners_list)
            x = False
            while win in final_list:
                win = choice(winners_list)
                count += 1
                if count >= 6:
                    x = True
                    break  # for when it runs out of reactions etc.
            if x:
                continue 
            final_list.append(win)

        if len(final_list) == 0:
            host = info["host"] if message.guild.get_member(info["host"]) is not None else "Host Not Found"
            e = discord.Embed(
                title=info["title"], description=f"Host: <@{host}> \n Winners: None")
            if info["requirement"]:
                requirements = []
                for r in info["requirement"]:
                    role = message.guild.get_role(r)
                    if not role:
                        continue
                    requirements.append(role.mention)
                e.add_field(name="Requirement", value=", ".join(
                    requirements), inline=False)

            if info["donor"]:
                donor = message.guild.get_member(info["donor"])
            if not info["donor"]:
                pass
            else:
                e.add_field(name="Donor", value=donor.mention, inline=False)

            if bypassrole:
                roles = []
                for r in bypassrole:
                    roles.append("<@&{0}>".format(r))
                e.add_field(name="Bypassrole", value=", ".join(roles))

            await channel.send(f"There were no valid entries for the **{info['title']}** giveaway \n{message.jump_url}")
            await message.edit(content=data["endHeader"].replace("{giveawayEmoji}", data["emoji"]), embed=e)

        else:
            winners = ", ".join(final_list)
            host = info["host"] if message.guild.get_member(
                info["host"]) is not None else "Unknown Host"

            e = discord.Embed(
                title=info["title"],
                description=f"Winner(s): {winners}\nHost: <@{host}>",
            )

            if info["requirement"]:
                requirements = []
                for r in info["requirement"]:
                    role = message.guild.get_role(r)
                    if not role:
                        continue
                    requirements.append(role.mention)
                e.add_field(name="Requirement", value=", ".join(
                    requirements), inline=False)
            if info["donor"]:
                donor = message.guild.get_member(info["donor"])
                if not donor:
                    pass
                else:
                    e.add_field(
                        name="Donor", value=donor.mention, inline=False)

            if bypassrole:
                roles = []
                for r in bypassrole:
                    r = message.guild.get_role(int(r))
                    if not r:
                        continue
                    roles.append(r.mention)
                e.add_field(name="Bypass Role(s)", value=", ".join(roles), inline=False)

            await message.edit(content=data["endHeader"].replace("{giveawayEmoji}", data["emoji"]), embed=e)
            await message.channel.send(f"The winners for the **{info['title']}** giveaway are \n{winners}\n{message.jump_url}")

            dmhost = await self.config.guild(message.guild).dmhost()
            dmwin = await self.config.guild(message.guild).dmwin()
            if dmhost:
                host = message.guild.get_member(int(host))
                if not host:
                    pass
                else:
                    hostmessage = await self.config.guild(message.guild).hostmessage()
                    e = discord.Embed(
                        title=f"Your giveaway has ended",
                        description=hostmessage.replace("{prize}", str(info["title"])).replace(
                            "{winners}", winners).replace("{guild}", message.guild.name).replace("{url}", message.jump_url)
                    )
                    try:
                        await host.send(embed=e)
                    except discord.errors.Forbidden:
                        pass 
            if dmwin:
                winmessage = await self.config.guild(message.guild).winmessage()
                for mention in final_list:
                    mention = message.guild.get_member(
                        int(mention.lstrip("<@!").lstrip("<@").rstrip(">")))
                    if not mention:
                        continue

                    e = discord.Embed(
                        title=f"You won a giveaway!",
                        description=winmessage.replace("{prize}", str(info["title"])).replace(
                            "{host}", f"<@{info['host']}>").replace("{guild}", message.guild.name).replace("{url}", message.jump_url)
                    )
                    try:
                        await mention.send(embed=e)
                    except discord.errors.Forbidden:
                        pass 

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

        await ctx.send(final_message, allowed_mentions=allowed_mentions)

    async def setnote(self, user: discord.Member, note: list):
        notes = await self.config.member(user).notes()
        notes.append(" ".join(note))
        await self.config.member(user).notes.set(notes)

    async def add_amount(self, user: discord.Member, amt: int):
        previous = await self.config.member(user).donated()
        previous += amt
        await self.config.member(user).donated.set(previous)
# -------------------------------------gset---------------------------------

    @commands.group(name="giveawayset", aliases=["gset"])
    @commands.guild_only()
    async def giveawayset(self, ctx):
        """Set your server settings for giveaways"""
        pass

    @giveawayset.group(name="manager")
    @commands.admin_or_permissions(administrator=True)
    async def manager(self, ctx):
        """Set the role that cant join any giveaways"""
        pass

    @manager.command(name="add")
    async def manager_add(self, ctx, role: discord.Role):
        """Add a role to the manager list"""
        roles = await self.config.guild(ctx.guild).manager()
        if role.id in roles:
            return await ctx.send("This role is already a manager")
        roles.append(role.id)
        await self.config.guild(ctx.guild).manager.set(roles)
        await ctx.send("Added to the manager roles")

    @manager.command(name="remove")
    async def manager_remove(self, ctx, role: discord.Role):
        """Remove a role from your manager roles"""
        roles = await self.config.guild(ctx.guild).manager()
        if role.id not in roles:
            return await ctx.send("This role is not a manager")
        roles.remove(role.id)
        await self.config.guild(ctx.guild).manager.set(roles)
        await ctx.send("Removed from the manager roles")

    @giveawayset.command(name="pingrole")
    @commands.admin_or_permissions(administrator=True)
    async def cmd_pingrole(self, ctx, role: discord.Role):
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
    @commands.admin_or_permissions(administrator=True)
    async def dmhost(self, ctx, dmhost: Optional[bool] = True):
        """Toggle whether to DM the host when the giveaway ends"""
        if not dmhost:
            await self.config.guild(ctx.guild).dmhost.set(False)
            await ctx.send("I will no longer dm hosts")
        else:
            await self.config.guild(ctx.guild).dmhost.set(True)
            await ctx.send("I will now dm hosts")

    @giveawayset.command(name="dmwin")
    @commands.admin_or_permissions(administrator=True)
    async def dmwin(self, ctx, dmwin: Optional[bool] = True):
        """Toggles whether to DM the winners of the giveaway"""
        if not dmwin:
            await self.config.guild(ctx.guild).dmwin.set(False)
            await ctx.send("I will no longer dm winners")
        else:
            await self.config.guild(ctx.guild).dmwin.set(True)
            await ctx.send("I will now dm winners")

    @giveawayset.group(name="bypassrole", aliases=["aarole", "bprole", "alwaysallowedrole"])
    @commands.admin_or_permissions(administrator=True)
    async def bypassrole(self, ctx):
        """Set the role that can bypass all giveaway requirements (or remove it)"""
        pass

    @bypassrole.command(name="add")
    async def bypassrole_add(self, ctx, role: discord.Role):
        """Add a bypass role"""
        roles = await self.config.guild(ctx.guild).bypassrole()
        if role.id in roles:
            return await ctx.send("This role already bypasses giveaway requirements")
        roles.append(role.id)
        await self.config.guild(ctx.guild).bypassrole.set(roles)
        await ctx.send("Added to the bypass roles")

    @bypassrole.command(name="remove")
    async def bypassrole_remove(self, ctx, role: discord.Role):
        """Remove a bypass role"""
        roles = await self.config.guild(ctx.guild).bypassrole()
        if role.id not in roles:
            return await ctx.send("This role does not bypass requirements")
        roles.remove(role.id)
        await self.config.guild(ctx.guild).bypassrole.set(roles)
        await ctx.send("Removed from the bypass roles")

    @giveawayset.group(name="blacklistrole", aliases=["blrole"])
    @commands.admin_or_permissions(administrator=True)
    async def blacklistrole(self, ctx):
        """Set the role that cant join any giveaways"""
        pass

    @blacklistrole.command(name="add")
    @commands.admin_or_permissions(administrator=True)
    async def cmd_add(self, ctx, role: discord.Role):
        """Add a role to blacklist"""
        roles = await self.config.guild(ctx.guild).blacklist()
        if role.id in roles:
            return await ctx.send("This role is already blacklisted")
        roles.append(role.id)
        await self.config.guild(ctx.guild).blacklist.set(roles)
        await ctx.send("Added to the blacklisted roles")

    @blacklistrole.command(name="remove")
    @commands.admin_or_permissions(administrator=True)
    async def cmd_remove(self, ctx, role: discord.Role):
        """Remove a role from your blacklisted roles"""
        roles = await self.config.guild(ctx.guild).blacklist()
        if role.id not in roles:
            return await ctx.send("This role is not blacklisted")
        roles.remove(role.id)
        await self.config.guild(ctx.guild).blacklist.set(roles)
        await ctx.send("Removed from the blacklisted roles")


    @giveawayset.command(name="settings", aliases=["showsettings", "stats"])
    async def settings(self, ctx):
        """View server settings"""
        data=await self.config.guild(ctx.guild).all()
        bprole = data["bypassrole"]
        if len(bprole) == 0:
            bypass_roles = "None"
        else:
            bypass_roles = []
            for r in bprole:
                bypass_roles.append(f"<@&{r}>")
            bypass_roles = ", ".join(bypass_roles)

        blacklisted_roles = data["blacklist"]
        if len(blacklisted_roles) == 0:
            blacklisted_roles = "None"
        else:
            blacklisted = []
            for r in blacklisted_roles:
                blacklisted.append(f"<@&{r}>")
                blacklisted_roles = ", ".join(blacklisted)
        
        if len(data["manager"]) == 0:
            data["manager"] = "Not Set"
        else:
            managers = []
            for m in data["manager"]:
                managers.append(f"<@&{m}>")
            data["manager"] = ", ".join(managers)

        e=discord.Embed(
            title=f"Giveaway Settings for {ctx.guild.name}",
            color=discord.Color.blurple(),
        )
        e.add_field(name="Manager Role", value="{0}".format(data["manager"]))
        e.add_field(name="Bypass Roles", value=bypass_roles)
        e.add_field(name="Blacklisted Roles", value=blacklisted_roles)
        e.add_field(name="Default Requirement",value="{0}".format(f"<@&{data['default_req']}>" if data["default_req"] is not None else "None"))
        e.add_field(name="Total Giveaways",value=len(data["giveaways"].keys()))
        e.add_field(name="DM on win", value=data["dmwin"])
        e.add_field(name="DM host", value=data["dmhost"])
        e.add_field(name="Autodelete invocation messages",
                    value=data["delete"])
        e.add_field(name="Pingrole", value="{0}".format(f"<@&{data['pingrole']}>" if data["pingrole"] is not None else "None"))
        e.add_field(name="Host Message", value="```\n{0}```".format(
            data["hostmessage"]), inline=False)
        e.add_field(name="Win Message", value="```\n{0}```".format(
            data["winmessage"]), inline=False)
        e.add_field(name="Start Header", value="```\n{0}```".format(
            data["startHeader"]), inline=False)
        e.add_field(name="End Header", value="```\n{0}```".format(
            data["endHeader"]), inline=False)
        e.add_field(name="Description", value="```\n{0}```".format(
            data["description"]), inline=False)
        e.add_field(name="Emoji", value=data["emoji"])
        

        await ctx.send(embed=e)

    @giveawayset.command(name="hostmessage")
    @commands.admin_or_permissions(administrator=True)
    async def hostmessage(self, ctx, * , message: str=None):
        """Set the message sent to the host when the giveaway ends. If there are no winners, it won't be sent.
       Your dmhost settings need to be toggled for this to work.
       Variables: {guild}: Server Name
       {winners}: Winners of the giveaway
       {prize}: The prize/title of the giveaway
       {url}: The jump url
       """
        if not message:
            await self.config.guild(ctx.guild).hostmessage.clear()
            await ctx.send("I've reset your servers host message")
        else:
            await self.config.guild(ctx.guild).hostmessage.set(message)
            await ctx.send(f"Your message is now `{message}`")

    @giveawayset.command(name="winmessage")
    @commands.admin_or_permissions(administrator=True)
    async def winmessage(self, ctx, * , message: str=None):
        """Set the message sent to the winner(s) when the giveaway ends. If there are no winners, it won't be sent.
       Your dmwin settings need to be toggled for this to work.
       Variables
       {guild}: Your server name 
       {host}: The host of the giveaway
       {prize}: The title/prize of the giveaway
       {url}: The jump url"""
        if not message:
            await self.config.guild(ctx.guild).winmessage.clear()
            await ctx.send("I've reset your servers win message")
        else:
            await self.config.guild(ctx.guild).winmessage.set(message)
            await ctx.send(f"Your message is now `{message}`")

    @giveawayset.command(name="startheader")
    @commands.admin_or_permissions(administrator=True)
    async def startheader(self, ctx, * , message: str=None):
        """Set the content for the giveaway message, not the embed. See gset description for that
        Variables
        {giveawayEmoji}: Your servers giveaway emoji, defaults to :tada: if you haven't set one"""
        if not message:
            await self.config.guild(ctx.guild).startHeader.clear()
            await ctx.send("I've reset your servers startheader")
        else:
            await self.config.guild(ctx.guild).startHeader.set(message)
            await ctx.send(f"Your startheader is now `{message}`")

    @giveawayset.command(name="endheader")
    @commands.admin_or_permissions(administrator=True)
    async def endheader(self, ctx, * , message: str=None):
        """Set the content for the giveaway message after it ends.
        Variables
        {giveawayEmoji}: Your servers giveaway emoji, defaults to :tada: if you haven't set one"""
        if not message:
            await self.config.guild(ctx.guild).endHeader.clear()
            await ctx.send("I've reset your servers endheader")
        else:
            await self.config.guild(ctx.guild).endHeader.set(message)
            await ctx.send(f"Your endheader is now `{message}`")
    
    @giveawayset.command(name="description")
    @commands.admin_or_permissions(administrator=True)
    async def description(self, ctx, * , message: str=None):
        """Set the content for the giveaway message after it ends.
        Variables:
        {emoji}: The emoji you use for giveaways"""
        if not message:
            await self.config.guild(ctx.guild).description.clear()
            await ctx.send("I've reset your servers embed description")
        else:
            await self.config.guild(ctx.guild).description.set(message)
            await ctx.send(f"Your embed description is now `{message}`")
    
    @giveawayset.command(name="emoji")
    @commands.admin_or_permissions(administrator=True)
    async def emoji(self, ctx, emoji: Union[discord.Emoji, discord.PartialEmoji, None]):
        """Set the custom emoji to use for giveaways"""
        if not emoji:
            await self.config.guild(ctx.guild).emoji.clear()
            await ctx.send("I will no longer use custom emojis.")
        else:
            await self.config.guild(ctx.guild).emoji.set(str(emoji))
            await ctx.send(f"Your emoji is now {str(emoji)}")

# -------------------------------------giveaways---------------------------------
    @commands.group(name="giveaway", aliases=["g"])
    @commands.guild_only()
    async def giveaway(self, ctx):
        """Start, end, reroll giveaways and more!"""
        pass

    @giveaway.group(name="secretblacklist")
    @commands.is_owner()
    async def secretblacklist(self, ctx):
        """Secretly blacklist people from winning ANY giveaways"""
        pass 

    @secretblacklist.command(name="add")
    async def secretblacklist_add(self, ctx, user: int):
        bl = await self.config.secretblacklist()
        if user in bl:
            return await ctx.send("This user is already blacklisted...")
        bl.append(user)
        await self.config.secretblacklist.set(bl)
        await ctx.send("Added to the blacklist")
    
    @secretblacklist.command(name="remove")
    async def secretblacklist_remove(self, ctx, user: int):
        bl = await self.config.secretblacklist()
        if user not in bl:
            return await ctx.send("This user is not blacklisted...")
        bl.remove(user)
        await self.config.secretblacklist.set(bl)
        await ctx.send("Removed from the blacklist")

    @giveaway.command(name="clearended")
    @commands.admin_or_permissions(manage_guild=True)
    async def clearended(self, ctx, *dontclear):
        """Clear the giveaways that have already ended in your server. Put all the message ids you dont want to clear after this to not clear them"""
        gaws=await self.config.guild(ctx.guild).giveaways()
        to_delete=[]
        for messageid, info in gaws.items():
            if str(messageid) in dontclear:
                continue
            if not info["Ongoing"]:
                to_delete.append(str(messageid))

        for messageid in to_delete:
            gaws.pop(messageid)
        await self.config.guild(ctx.guild).giveaways.set(gaws)
        await ctx.send(f"Successfully cleared {len(to_delete)} inactive giveaways")

    @giveaway.command(name="help")
    async def g_help(self, ctx):
        """Explanation on how to start a giveaway"""
        e=discord.Embed(
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
        --ping: Use this flag to ping the set pingrole for your server

        Specify `none` to the requirement to remove fuzzyrole converters and not have a role requirement
        Multiple requirements need to be split with `;;` or `|`, spaces should not be included


        Example:
        `.g start 10m 1w Contributor --donor @Andee#8552 --amt 50000 --note COINS ARE YUMMY`
        `.g start 10m 1 @Owners lots of yummy coins --ping --msg I will eat these coins --donor @Andee`
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
        winners: str="1",
        requirements: Optional[FuzzyRole]=None,
        *,
        title="Giveaway!",

    ):
        """Start a giveaway in your server. Flags and Arguments are explained with .giveaway help
        """
        title=title.split("--")
        title=title[0]
        flags=ctx.message.content
        winners=winners.rstrip("w")

        if not winners.isdigit():
            return await ctx.send(f"I could not get an amount of winners from {winners}")
        winners=int(winners)
        if winners < 0:
            return await ctx.send("Can've have less than 1 winner")


        parser=NoExitParser(description="argparse", add_help=False)

        parser.add_argument("--ping", action="store_true", default=False)
        parser.add_argument("--msg", nargs='*', type=str, default=None)
        parser.add_argument("--donor", nargs='?', type=str, default=None)
        parser.add_argument("--amt", nargs='?', type=int, default=0)
        parser.add_argument("--note", nargs='*', type=str, default=None)
        parser.add_argument("--mee6", nargs="?", type=int, default=None)

        try:
            flags=vars(parser.parse_known_args(flags.split())[0])

            if flags["donor"]:
                donor=flags["donor"].lstrip("<@!").lstrip("<@").rstrip(">")
                if donor.isdigit():
                    donor=ctx.guild.get_member(int(donor))
                else:
                    donor=discord.utils.get(ctx.guild.members, name=donor)
                if not donor:
                    return await ctx.send("The donor provided is not valid")
                flags["donor"]=donor.id

        except Exception as exc:
            return await ctx.send(str(exc))

        guild=ctx.guild
        data=await self.config.guild(guild).all()

        gaws=await self.config.guild(guild).giveaways()


        if not requirements:
            role=data["default_req"]
            if not role or role == [None]:
                roleid=None
            else:
                role=ctx.guild.get_role(role)
                roleid= [role.id]
        else:
            roleid=[r.id for r in requirements]

        e=discord.Embed(
            title=title,
            description=f"Hosted By: {ctx.author.mention}",
            timestamp=datetime.utcnow(),
            color=discord.Color.green(),
        )

        e.set_footer(text="Ending at")

        time=self.convert_time(time)
        ending_time=datetime.utcnow().timestamp() + float(time)
        ending_time=datetime.fromtimestamp(ending_time)
        pretty_time=self.display_time(time)

        e.description += f"\n Time Left: {pretty_time}"
        e.timestamp=ending_time

        gaw_msg=await ctx.send(embed=e)

        msg=str(gaw_msg.id)

        gaws[msg]={}
        gaws[msg]["host"]=ctx.author.id
        gaws[msg]["Ongoing"]=True
        gaws[msg]["requirement"]=roleid
        gaws[msg]["winners"]=winners
        gaws[msg]["title"]=title
        gaws[msg]["endtime"]=datetime.utcnow().timestamp() + float(time)
        gaws[msg]["channel"]=ctx.channel.id
        gaws[msg]["donor"]=flags["donor"]

        await self.config.guild(guild).giveaways.set(gaws)

        delete=await self.config.guild(ctx.guild).delete()

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
            hosted=await self.config.member(ctx.guild.get_member(flags["donor"])).hosted()
            hosted += 1
            await self.config.member(ctx.guild.get_member(flags["donor"])).hosted.set(hosted)
        else:
            prev=await self.config.member(ctx.author).hosted()
            prev += 1
            await self.config.member(ctx.author).hosted.set(prev)

        self.message_cache[str(msg)]=gaw_msg

        await self.start_giveaway(int(msg), gaws[msg])

    @giveaway.command(name="end")
    @commands.check(is_manager)
    async def end(self, ctx, messageid: Optional[IntOrLink]=None):
        """End a giveaway"""
        gaws=await self.config.guild(ctx.guild).giveaways()
        if messageid is None:
            for messageid, info in list(gaws.items())[::-1]:
                if info["channel"] == ctx.channel.id and info["Ongoing"]:
                    await self.end_giveaway(messageid, info)
                    return
            return await ctx.send("There aren't any giveaways in this channel, specify a message id/link to end another channels giveaways")
        gaws=await self.config.guild(ctx.guild).giveaways()
        if str(messageid) not in gaws:
            return await ctx.send("This isn't a giveaway.")
        elif gaws[str(messageid)]["Ongoing"] == False:
            return await ctx.send(f"This giveaway has ended. You can reroll it with `{ctx.prefix}g reroll {messageid}`")
        else:
            await self.end_giveaway(messageid, gaws[str(messageid)])

    @giveaway.command(name="reroll")
    @commands.check(is_manager)
    async def reroll(self, ctx, messageid: Optional[IntOrLink], winners: Optional[int]=1):
        """Reroll a giveaway"""
        gaws=await self.config.guild(ctx.guild).giveaways()
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
    async def g_ping(self, ctx, *, message: str=None):
        """Ping the pingrole for your server with an optional message, it wont send anything if there isn't a pingrole"""
        m=discord.AllowedMentions(roles=True, everyone=False)
        await ctx.message.delete()
        pingrole=await self.config.guild(ctx.guild).pingrole()
        if not pingrole:
            try:
                return await ctx.send(message, allowed_mentions=m)
            except discord.HTTPException:
                return
        role=ctx.guild.get_role(pingrole)
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
    async def cache(self, ctx, active: Optional[bool] = True, cacheglobal: str = None):
        """Owner Utility to force a cache on a server in case something broke or you reloaded the cog and need it needs to be cached"""
        e = discord.Embed(title="Cached Giveaways", description="Cached Servers\n")
        async with ctx.typing():
            counter = 0
            if cacheglobal == "--global":
                all_guilds = await self.config.all_guilds()
                for guild_id, data in all_guilds.items():
                    counter = 0
                    giveaways = data["giveaways"]
                    for messageid, info in giveaways.items():
                        if active:
                            if not info["Ongoing"]:
                                continue 
                        
                        if str(messageid) in self.message_cache:
                            continue 
                        message = self.bot._connection._get_message(int(messageid))
                        channel = self.bot.get_channel(info["channel"])
                        if not channel:
                            continue 
                        if not message:
                            try:
                                message = await channel.fetch_message(int(messageid))
                            except discord.NotFound:
                                continue 
                        self.message_cache[messageid] = message 
                        counter += 1
                        

                    guild = self.bot.get_guild(int(guild_id))
                    e.description += f"Cached {counter} messages in {guild.name}\n"
            else:
                for messageid, info in (await self.config.guild(ctx.guild).giveaways()).items():
                    if active:
                        if not info["Ongoing"]:
                            continue 
                    
                    if str(messageid) in self.message_cache:
                        continue 
                    message = self.bot._connection._get_message(int(messageid))
                    channel = self.bot.get_channel(info["channel"])
                    if not channel:
                        continue 
                    if not message:
                        try:
                            message = await channel.fetch_message(int(messageid))
                        except discord.NotFound:
                            continue 
                        self.message_cache[messageid] = message
                        counter += 1
                
                e.description += f"Cached {counter} messages in {ctx.guild.name}"

        await ctx.send(embed=e)            


    @giveaway.command(name="list")
    @commands.cooldown(1, 30, commands.BucketType.member)
    @commands.max_concurrency(2, commands.BucketType.user)
    async def g_list(self, ctx, can_join: bool=False):
        """List the giveways in the server. Specify True for can_join paramater to only list the ones you can join"""
        async with ctx.typing():
            giveaway_list=[]
            bypassrole=await self.config.guild(ctx.guild).bypassrole()
            counter=0
            gaws=await self.config.guild(ctx.guild).giveaways()
            startmessage=await ctx.send("0 giveaways gathered")
            for messageid, info in gaws.items():
                messageid=str(messageid)
                try:
                    if counter % 20 == 0:
                        await startmessage.edit(content=f"{counter} messages out of {len(gaws.values())} messages gathered")
                except ZeroDivisionError:
                    pass
                counter += 1
                if not info["Ongoing"]:
                    continue
                if not can_join:
                    jump_url = f"https://discord.com/channels/{ctx.guild.id}/{info['channel']}/{messageid}"

                    
                    header=f"[{info['title']}]({jump_url})"
                    header += " | Winners: {0} | Host: <@{1}>".format(info["winners"], info["host"])
                    header += " | Channel: <#{0}> | ID: {1}".format(info["channel"], messageid)
                    if (await self.can_join(ctx.author, info)):
                        header += " :white_check_mark: You can join this giveaway\n"
                        giveaway_list.append(header)
                        continue
                    header += " :octagonal_sign: You cannot join this giveaway\n"

                    giveaway_list.append(header)
                else:
                    jump_url = f"https://discord.com/channels/{ctx.guild.id}/{info['channel']}/{messageid}`"
                    header=f"[{info['title']}]({jump_url})"
                    header += " | Winners: {0} | Host: <@{1}>".format(info["winners"], info["host"])
                    header += " | Channel: <#{0}> | ID: {1}".format(info["channel"], messageid)
                    if (await self.can_join(ctx.author, info)):
                        header += " :white_check_mark: You can join this giveaway\n"
                        giveaway_list.append(header)
                    
            
        await startmessage.delete()

        formatted_giveaways="\n".join(giveaway_list)
        if len(formatted_giveaways) > 2048:
            pages=list(pagify(formatted_giveaways))
            embeds=[]

            for i, page in enumerate(pages, start=1):
                e=discord.Embed(
                    title=f"Giveaways Page {i}/{len(pages)}",
                    description=page,
                    color=discord.Color.green()
                )
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e=discord.Embed(
                title="Giveaway Page 1",
                description=formatted_giveaways,
                color=discord.Color.green()
            )
            await ctx.send(embed=e)
              

    @giveaway.command(name="cancel")
    @commands.check(is_manager)
    async def cancel(self, ctx, giveaway: Optional[IntOrLink]=None):
        """Cancel a giveaway"""
        gaws=await self.config.guild(ctx.guild).giveaways()
        if not giveaway:
            for messageid, info in list(gaws.items())[::-1]:
                if info["Ongoing"] and info["channel"] == ctx.channel.id:
                    chan=self.bot.get_channel(info["channel"])
                    if not chan:
                        continue
                    try:
                        m=self.message_cache.get(giveaway, await chan.fetch_message(int(messageid)))
                    except discord.NotFound:
                        continue

                    e=discord.Embed(
                        title=info["title"],
                        description=f"Giveaway Cancelled\n",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    e.description += "Hosted By: <@{0}>\nCancelled By: {1}".format(
                        info["host"], ctx.author.mention)
                    e.set_footer(text="Cancelled at")

                    try:
                        await m.edit(content="Giveaway Cancelled", embed=e)
                    except discord.NotFound:
                        continue
                    info["Ongoing"]=False
                    gaws[messageid]=info
                    await self.config.guild(ctx.guild).giveaways.set(gaws)
                    return await ctx.send("Cancelled the giveaway for **{0}**".format(info["title"]))

            return await ctx.send("There are no active giveaways in this channel to be cancelled, specify a message id/link after this in another channel to cancel one")
        giveaway=str(giveaway)
        if giveaway not in gaws.keys():
            return await ctx.send("This giveaway does not exist")
        if not gaws[giveaway]["Ongoing"]:
            return await ctx.send("This giveaway has ended")

        data=gaws[giveaway]
        chan=self.bot.get_channel(data["channel"])
        if not chan:
            return await ctx.send("This message is no longer available")
        try:
            m=self.message_cache.get(giveaway, await chan.fetch_message(int(giveaway)))
        except discord.NotFound:
            return await ctx.send("Couldn't find this giveaway")

        gaws[giveaway]["Ongoing"]=False
        await self.config.guild(ctx.guild).giveaways.set(gaws)

        e=discord.Embed(
            title=data["title"],
            description=f"Giveaway Cancelled\n",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        e.description += "Hosted By: <@{0}>\nCancelled By: {1}".format(
            data["host"], ctx.author.mention)
        e.set_footer(text="Cancelled at")
        try:
            await m.edit(content="Giveaway Cancelled", embed=e)
        except discord.NotFound:
            return await ctx.send("I couldn't find this giveaway")
        gaws[giveaway]["Ongoing"]=False
        await self.config.guild(ctx.guild).gaws.set(gaws)
        await ctx.send("Cancelled the giveaway for **{0}**").format(data["title"])
    


# -------------------------------------gprofile---------------------------------

    @commands.group(name="giveawayprofile", aliases=["gprofile"], invoke_without_command=True)
    @commands.guild_only()
    async def giveawayprofile(self, ctx, member: Optional[discord.Member]=None):
        """View your giveaway donations and notes"""
        if not ctx.invoked_subcommand:
            if not member:
                pass
            else:
                ctx.author=member
            donated=await self.config.member(ctx.author).donated()
            format_donated="{:,}".format(donated)
            notes=await self.config.member(ctx.author).notes()
            hosted=await self.config.member(ctx.author).hosted()
            try:
                average_donated="{:,}".format(round(donated/hosted))
            except ZeroDivisionError:
                average_donated=0

            e=discord.Embed(
                title="Donated", description=f"Giveaways Hosted: {hosted} \n", color=ctx.author.color)
            e.description += f"Amount Donated: {format_donated} \n"
            e.description += f"Average Donation Value: {average_donated}"

            if len(notes) == 0:
                pass
            else:
                e.set_footer(text=f"{len(notes)} notes")

            await ctx.send(embed=e)
    
    @giveawayprofile.command(name="top", aliases=["leaderboard", "lb"])
    async def top(self, ctx, amt: int = 10):
        """View the top donators"""
        if amt < 1:
            return await ctx.send("no")
        member_data = await self.config.all_members(ctx.guild)
        sorted_data = [(member, data["donated"]) for member, data in member_data.items() if data["donated"] > 0 and ctx.guild.get_member(int(member)) is not None]
        ordered_data = sorted(sorted_data[:amt], key = lambda m: m[1], reverse=True)
        
        if len(ordered_data) == 0:
            return await ctx.send("I have no data for your server")
        
        formatted_string = ""

        for i, data in enumerate(ordered_data, start=1):
            formatted_string += f"{i}. <@{data[0]}>: {self.comma_format(data[1])}\n"
        
        if len(formatted_string) >= 2048:
            embeds = []
            pages = list(pagify(formatted_string))
            for page in pages:
                e = discord.Embed(title="Donation Leaderboard", description=page, color=ctx.author.color)
                embeds.append(e)
            
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send(embed=discord.Embed(title="Donation Leaderboard", description=formatted_string, color=ctx.author.color))
            
    @giveawayprofile.command(name="notes")
    async def gprofile_notes(self, ctx, member: Optional[discord.Member]=None):
        """View your giveaway notes"""
        if member:
            ctx.author=member
        notes=await self.config.member(ctx.author).notes()
        if len(notes) == 0:
            return await ctx.send("You have no notes")

        formatted_notes=[]

        for i, note in enumerate(notes, start=1):
            formatted_notes.append(f"{i}. {note}")

        formatted_notes="\n\n".join(formatted_notes)

        if len(formatted_notes) >= 2048:
            embeds=[]
            pages=list(pagify(formatted_notes))
            for i, page in enumerate(pages, start=1):
                e=discord.Embed(
                    title="Notes",
                    description=page,
                    color=ctx.author.color
                )
                e.set_footer(text=f"{i} out of {len(pages)} pages.")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e=discord.Embed(
                title="Notes",
                description=formatted_notes,
                color=ctx.author.color
            )
            await ctx.send(embed=e)

# -------------------------------------gstore---------------------------------

    @commands.group(name="giveawaystore", aliases=["gstore"])
    @commands.check(is_manager)
    async def giveawaystore(self, ctx):
        """Manage donation and note tracking for members"""
        pass

    @giveawaystore.command(name="clear")
    async def gstore_clear(self, ctx, member: Optional[discord.Member]=None):
        """Clear everything for a member"""
        if not member:
            return await ctx.send("A member needs to be specified after this")
        else:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            await ctx.send(f"Are you sure? This will clear all of **{member.name}'s** data. Type `YES I WANT TO DO THIS` exact below if you are sure")
            try:
                msg=await self.bot.wait_for("message", check=check, timeout=20)
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
    async def donate_add(self, ctx, member: Optional[discord.Member]=None, amt: str=None):
        """Add an amount to a users donations"""
        if not member:
            return await ctx.send("A member needs to be specified after this")
        if not amt:
            return await ctx.send("You need to specify an amount to donate")
        amt=amt.replace(",", "")

        if not str(amt).isdigit():
            return await ctx.send("This isn't a number.")

        previous_amount=await self.config.member(member).donated()
        new_amount=int(amt) + previous_amount
        await self.config.member(member).donated.set(new_amount)
        await ctx.send("Done.")

    @donate.command(name="remove")
    async def donate_remove(self, ctx, member: Optional[discord.Member]=None, amt: str=None):
        """Remove a certain amount from a members donation amount"""
        if not member:
            return await ctx.send("A member needs to be specified after this")
        if not amt:
            return await ctx.send("You need to specify an amount to donate")
        amt=amt.replace(",", "")

        if not str(amt).isdigit():
            return await ctx.send("This isn't a number.")

        previous_amount=await self.config.member(member).donated()
        new_amount=previous_amount - int(amt)
        if new_amount < 0:
            return await ctx.send("You can't go below 0")
        await self.config.member(member).donated.set(new_amount)
        await ctx.send("Done.")

    @giveawaystore.group(name="note")
    async def note(self, ctx):
        """A group for managing giveaway notes"""
        pass

    @note.command(name="add")
    async def note_add(self, ctx, member: Optional[discord.Member]=None, *, note: str=None):
        """Add a note to a member"""
        if not member:
            return await ctx.send("A member needs to be specified.")
        if not note:
            return await ctx.send("A note needs to be specified.")

        notes=await self.config.member(member).notes()
        notes.append(note)
        await self.config.member(member).notes.set(notes)
        await ctx.send("Added a note.")

    @note.command(name="remove")
    async def note_remove(self, ctx, member: Optional[discord.Member]=None, note: Optional[int]=None):
        """Remove a note from a member, you can do `[p]gprofile notes @member` to find the note ID, and specify that for the note param"""
        if not member:
            return await ctx.send("A member needs to be specified.")
        if not note:
            return await ctx.send("A note ID needs to be specified.")

        notes=await self.config.member(member).notes()
        if note > len(notes):
            return await ctx.send("This note does not exist")
        else:
            notes.pop(note-1)
        await self.config.member(member).notes.set(notes)
        await ctx.send("Removed a note.")



    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel=self.bot.get_channel(payload.channel_id)
        user=channel.guild.get_member(payload.user_id)
        if user.bot:
            return
        data = await self.config.guild(channel.guild).all()
        gaws = data["giveaways"]
        if str(payload.message_id) not in gaws:
            return
        elif gaws[str(payload.message_id)]["Ongoing"] == False:
            return

        if not channel.permissions_for(channel.guild.me).manage_messages:
            return

        if str(payload.emoji) != data["emoji"]:
            return

        bypassrole = data["bypassrole"]
        if bypassrole in [r.id for r in user.roles]:
            return 
        if not (await self.can_join(user, gaws[str(payload.message_id)])):
            message = self.bot._connection._get_message(payload.message_id)
            if not message:
                if hasattr(channel, "get_partial_message"): #reds pinned version of dpydoesn't have this feature
                    message = channel.get_partial_message(payload.message_id)
                    await message.remove_reaction(str(payload.emoji), user)
                else:
                    try:
                        message = await channel.fetch_message(payload.message_id)
                    except discord.NotFound:
                        return 
                    await message.remove_reaction(str(payload.emoji), user)
            self.message_cache[str(payload.message_id)] = message
            e = discord.Embed(title="Missing Giveaway Requirement", description=f"You do not meet the requirement which is required for [this]({message.jump_url}) giveaway or you have a blacklisted role. You can check gset settings to see if you have the blacklisted role")
            await user.send(embed=e)
            for r in message.reactions:
                if str(r) == data["emoji"]:
                    await r.remove(user)
                    return 
