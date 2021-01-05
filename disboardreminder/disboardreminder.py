#Idea from Phen-Cogs https://github.com/phenom4n4n/phen-cogs/blob/master/disboardreminder/disboardreminder.py
#Restart after cog unload code taken from https://github.com/Redjumpman/Jumper-Plugins/tree/V3/raffle
#chatchart/bumpchart logic taken from https://github.com/aikaterna/aikaterna-cogs/tree/v3/chatchart

from datetime import datetime
from io import BytesIO
import asyncio
import discord
from typing import Optional
import matplotlib
from redbot.core import Config
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from collections import Counter


matplotlib.use("agg")
import matplotlib.pyplot as plt

plt.switch_backend("agg")

class DisboardReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.load_check = self.bot.loop.create_task(self.bump_restart())
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True)
        

        default_guild = {
            "role": None, 
            "clean": False,
            "channel": None,
            "msg": "It's been 2 hours since someone bumped us on DISBOARD, could someone run !d bump here?",
            "ty": "{member} thanks for bumping our server! I'll notify you in 2 hours to bump again.",
            "nextbump": None,
            "nextweeklyreset": None, 
            "lock": False,
        }

        default_member = {
            "bumps": 0,
            "weeklybumps": 0
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
    
    @commands.group(name="bumpreminder", aliases=["bprm", "disboardreminder"])
    async def bumpreminder(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send_help("bprm")
    
    @bumpreminder.command(name="channel", aliases=["chan"])
    @commands.admin_or_permissions(manage_guild=True)
    async def bumpreminder_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Sets the channel that bumpreminders get sent to"""
        if not channel:
            await self.config.guild(ctx.guild).channel.set(None)
            await ctx.send("I will no longer send bumpreminders.")
        else:
            if not channel.permissions_for(ctx.me).send_messages:
                await ctx.send(f"I do not have permissions to send messages in <#{channel.id}>")
            else:
                await self.config.guild(ctx.guild).channel.set(channel.id)
                await ctx.send(f"I will now send bumpreminders in <#{channel.id}>")
    
    @bumpreminder.command(name="role", aliases=["pingrole"])
    @commands.admin_or_permissions(manage_guild=True)
    async def bumpreminder_role(self, ctx, role: Optional[discord.Role] = None):
        """Sets the role to ping when its time to bump"""
        if not role:
            await self.config.guild(ctx.guild).role.set(None)
            await ctx.send("I will no longer pong roles when sending bumpreminders.")
        else:
            await self.config.guild(ctx.guild).role.set(role.id)
            await ctx.send(f"I will now pong **{role.name}** for bumpreminders.")
    
    @bumpreminder.command(name="autoclean", aliases=["clean"])
    @commands.admin_or_permissions(manage_guild=True)
    async def autoclean(self, ctx, clean: Optional[bool] = None):
        """Sets whether to delete user messages and DISBOARD's failed embeds or not"""
        if clean is None:
            await self.config.guild(ctx.guild).clean.set(False)
            await ctx.send("I will no longer clean the bump channel")
        else:
            await self.config.guild(ctx.guild).clean.set(clean)

            if clean:
                await ctx.send("I will now delete user messages and fail embeds.")
            else:
                await ctx.send("I will no longer delete user messages and fail embeds.")

    @bumpreminder.command(name="autolock", aliases=["lock"])
    @commands.admin_or_permissions(manage_guild=True)
    async def autolock(self, ctx, lock: Optional[bool] = None):
        """Sets whether to lock the bump channel or not"""
        if not lock:
            await self.config.guild(ctx.guild).lock.set(False)
            await ctx.send("I will no longer lock the bump channel")
        else:
            await self.config.guild(ctx.guild).lock.set(True)
            await ctx.send("I will now lock the bump channel")
    
    @bumpreminder.command(name="message", aliases=["msg", "bumpmsg", "bumpmessage"])
    @commands.admin_or_permissions(manage_guild=True)
    async def bumpreminder_message(self, ctx, * , message = None):
        """Changes the bump message"""
        if not message:
            await self.config.guild(ctx.guild).msg.set("It's been 2 hours since someone bumped us on DISBOARD, could someone run !d bump here?")
            await ctx.send("I've cleared your message")
        else:
            await self.config.guild(ctx.guild).msg.set(message)
            await ctx.send(f"Your message is now `{message}`")
    
    @bumpreminder.command(name="tymessage", aliases=["thankyou"])
    @commands.admin_or_permissions(manage_guild=True)
    async def tymessage(self, ctx, * , message = None):
        """Changes the message sent when someone bumps. Use {member} for the member who bumped, and {guildid} or {guild.id} for your server id."""
        if not message:
            await self.config.guild(ctx.guild).ty.set("{member} thanks for bumping our server! I'll notify you in 2 hours to bump again.")
            await ctx.send("Reset this servers thank you message.")
        else:
            await self.config.guild(ctx.guild).ty.set(message)
            await ctx.send(f"Your message is now `{message}`")
        
    @bumpreminder.command(name="top")
    async def top(self, ctx, amt: Optional[int] = 30):
        """View the top bumpers of the server"""
        if amt < 1:
            await ctx.send("You can't view nothing idiot.")
            return 

        data = await self.config.all_members(ctx.guild)
        data = [(member, memberdata["bumps"]) for member, memberdata in data.items() if ctx.guild.get_member(member) is not None and memberdata["bumps"] > 0] #for when idiots leave the server and the mentions get fucky
        sorted_data = sorted(data[:amt], reverse=True, key=lambda m: m[1])

        lb = []

        for number, member in enumerate(sorted_data, start=1):
            lb.append(f"{number}. <@!{member[0]}> has {member[1]} bumps.")

        if len(lb) == 0:
            await ctx.send("It seems that this server does not have any registered bumps.")
            return 
        
        lb = "\n".join(lb)
        pages = []
        lb_pages = pagify(lb)
        lb_pages = list(lb_pages)

        total = len(lb_pages)

        for number, page in enumerate(lb_pages, start=1):
            e = discord.Embed(title="Bump Leaderboard", description=page, color=discord.Color.green())
            e.set_footer(text=f"{number} out of {total} pages.")
            pages.append(e)
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @bumpreminder.group(name="weekly")
    async def weekly(self, ctx):
        """Bumpreminders for weekly"""
        if not ctx.invoked_subcommand:
            data = await self.config.all_members(ctx.guild)
            data = [(member, memberdata["weeklybumps"]) for member, memberdata in data.items() if ctx.guild.get_member(member) is not None and memberdata["weeklybumps"] > 0]
            sorted_data = sorted(data, reverse=True, key=lambda m: m[1])

            if len(sorted_data) == 0:
                return await ctx.send("I do not have bump data for this server")

            lb = []

            for number, member in enumerate(sorted_data, start=1):
                lb.append(f"{number}. <@!{member[0]}> has {member[1]} bumps.")

            if len(lb) == 0:
                return await ctx.send("This server has no tracked weekly bumps")
            
            lb = "\n".join(lb)
            pages = []
            lb_pages = pagify(lb)
            lb_pages = list(lb_pages)

            total = len(lb_pages)

            for number, page in enumerate(lb_pages, start=1):
                e = discord.Embed(title="Bump Leaderboard", description=page, color=discord.Color.green())
                e.set_footer(text=f"{number} out of {total} pages.")
                pages.append(e)
            await menu(ctx, pages, DEFAULT_CONTROLS)
    
    @weekly.command(name="chart")
    async def weekly_chart(self, ctx):
        """Basically bumpreminder chart but for weekly bumps"""
        try:
            data = await self.config.all_members(ctx.guild)
            if not data:
                return await ctx.send("This server has no registered bumps.")
            count = Counter()

            for member, bumpdata in data.items():
                _member = ctx.guild.get_member(member)
                if _member:
                    if len(_member.display_name) >= 23:
                        whole_name = f"{_member.display_name[:20]}..."
                    else:
                        whole_name = _member.display_name
                    count[whole_name] = bumpdata["weeklybumps"]
                else:
                    #For when idiots leave the server
                    count[str(member)] = bumpdata["weeklybumps"]
            chart = self.create_chart(count)
        except Exception as e:
            await ctx.send(f"Uh oh, something borked, \n {e}")
            return 

        await ctx.send(file=discord.File(chart, "chart.png"))

    @weekly.command(name="reset")
    @commands.admin_or_permissions(manage_guild=True)
    async def weekly_reset(self, ctx):
        """Reset your weekly data early"""
        await self.reset_weekly(ctx.guild)
        await ctx.send("I've reset the weekly data. It will reset again in 1 week unless ended early.")

    @bumpreminder.command(name="chart")
    async def chart(self, ctx):
        """View the bumpers in a chart, looks better"""
        """Thanky Thanky Aikaterna for the chatchart. Code can be viewed here: https://github.com/aikaterna/aikaterna-cogs/blob/v3/chatchart/chatchart.py"""
   
        try:
            data = await self.config.all_members(ctx.guild)
            if not data:
                return await ctx.send("This server has no registered bumps.")
            count = Counter()

            for member, bumpdata in data.items():
                _member = ctx.guild.get_member(member)
                if _member:
                    if len(_member.display_name) >= 23:
                        whole_name = f"{_member.display_name[:20]}..."
                    else:
                        whole_name = _member.display_name
                    count[whole_name] = bumpdata["bumps"]
                else:
                    #For when idiots leave the server
                    count[str(member)] = bumpdata["bumps"]
            chart = self.create_chart(count)
        except Exception as e:
            await ctx.send(f"Uh oh, something borked, \n {e}")
            return 

        await ctx.send(file=discord.File(chart, "chart.png"))
    
    @bumpreminder.command(name="settings", aliases=["showsettings"])
    async def bumpreminder_settings(self, ctx):
        data = await self.config.guild(ctx.guild).all()

        if data["channel"] is not None:
            if self.bot.get_channel(data["channel"]) is not None:
                channel = data["channel"]
                channel = f"<#{channel}>"
            else:
                channel = "Channel Not Found"
        else:
            channel = "Not Set"

        if data["role"] is not None:
            if ctx.guild.get_role(data["role"]) is not None:
                role = data["role"]
                role = f"<@&{role}>"
            else:
                role = "Not Found"
        else:
            role = "Not Set"
        
        clean = data["clean"]
        msg = data["msg"]
        msg = f"```{msg}```"

        ty = data["ty"]
        ty = f"```{ty}```"
        lock = data["lock"]

        nextbump = data["nextbump"]
        nextreset = data["nextweeklyreset"]


        e = discord.Embed(title=f"Bumpreminder Settings for {ctx.guild.name}", color=discord.Color.green())
        e.add_field(name="Channel", value=channel)
        e.add_field(name="Role", value=role)
        e.add_field(name="Clean", value=clean)
        e.add_field(name="Lock", value=lock)
        e.add_field(name="Bump Message", value=msg, inline=False)
        e.add_field(name="Thank You Message", value=ty, inline=False)
        e.add_field(name="Next Bump", value=nextbump)
        if nextbump is not None:
            nextbump = datetime.fromtimestamp(nextbump)
            e.timestamp = nextbump
            e.set_footer(text="Next Bump is at")

        pages = []
        pages.append(e)

        e2 = discord.Embed(title="Bumpreminder Settings Page 2", color=discord.Color.green())
        e2.add_field(name="Next Weekly Reset", value=nextreset)
        if nextreset is not None:
            nextreset = datetime.fromtimestamp(nextreset)
            e2.timestamp = nextreset 
            e2.set_footer(text="Next Weekly reset is at")
        pages.append(e2)
        
        await menu(ctx, pages, DEFAULT_CONTROLS)
        

    @staticmethod
    def create_chart(data: Counter):
        """Thanky Thanky Aikaterna for the chatchart. Code can be viewed here: https://github.com/aikaterna/aikaterna-cogs/blob/v3/chatchart/chatchart.py"""
        plt.clf()
        most_common = data.most_common()
        total = sum(data.values())
        sizes = [(x[1] / total) * 100 for x in most_common][:20]
        labels = [f"{x[0]} {round(sizes[index], 1):g}%" for index, x in enumerate(most_common[:20])]
        title = plt.title("Top Bumpers", color="white")
        title.set_va("top")
        title.set_ha("center")
        plt.gca().axis("equal")
        colors = [
            "r",
            "darkorange",
            "gold",
            "y",
            "olivedrab",
            "green",
            "darkcyan",
            "mediumblue",
            "darkblue",
            "blueviolet",
            "indigo",
            "orchid",
            "mediumvioletred",
            "crimson",
            "chocolate",
            "yellow",
            "limegreen",
            "forestgreen",
            "dodgerblue",
            "slateblue",
            "gray",
        ]
        pie = plt.pie(sizes, colors=colors, startangle=0)
        plt.legend(
            pie[0],
            labels,
            bbox_to_anchor=(0.7, 0.5),
            loc="center",
            fontsize=10,
            bbox_transform=plt.gcf().transFigure,
            facecolor="#ffffff",
        )
        plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
        image_object = BytesIO()
        plt.savefig(image_object, format="PNG", facecolor="#36393E")
        image_object.seek(0)
        return image_object
    
    async def bump_restart(self):
        try:
            await self.bot.wait_until_ready()
            coros = []
            data = await self.config.all_guilds()
            for guildid, guilddata in data.items():
                guild = self.bot.get_guild(guildid)
                if not guild:
                    continue
                timer = guilddata["nextbump"]
                if timer:
                    now = datetime.utcnow().timestamp()
                    remaining = timer - now
                    if remaining <= 0:
                        await self.send_bumpmsg(guild)
                    else:
                        coros.append(self.start_timer(guild, timer))
            await asyncio.gather(*coros)
        except Exception as e:
            channel = self.bot.get_channel(779170774934093844)
            await channel.send(e)
        
        try:
            coros = []
            data = await self.config.all_guilds()
            for guildid, guilddata in data.items():
                guild = self.bot.get_guild(guildid)
                if not guild:
                    continue 
                timer = guilddata["nextweeklyreset"]
                if timer:
                    now = datetime.utcnow().fromtimestamp()
                    remaining = timer - now 
                    if remaining <= 0:
                        self.reset_weekly(guild)
                    else:
                        coros.append(self.weekly_timer(guild, timer))
                else:
                    coros.append(self.reset_weekly(guild))
            await asyncio.gather(*coros)
        
        except Exception as e:
            channel = self.bot.get_channel(779170774934093844)
            await channel.send(e)
    
    async def send_bumpmsg(self, guild: discord.Guild):
        data = await self.config.guild(guild).all()
        channel = guild.get_channel(data["channel"])

        if not channel or not channel.permissions_for(guild.me).send_messages:
            await self.config.guild(guild).channel.set(None)

        elif data["role"] is not None:
            role = guild.get_role(data["role"])
            if role is not None:
                message = f"{role.mention} {data['msg']}"
                allowed_mentions = discord.AllowedMentions(roles=True, everyone=False)
                await channel.send(message, allowed_mentions=allowed_mentions)
            else:
                await self.config.guild(guild).set(None)

        elif channel:
            message = data["msg"]
            allowed_mentions = discord.AllowedMentions(roles=True, everyone=False)
            try:
                await channel.send(message, allowed_mentions=allowed_mentions)
            except discord.errors.Forbidden:
                await self.config.guild(guild).channel.set(None)
        else:
            await self.config.guild(guild).channel.set(None)
            
        if data["lock"]:
            try:
                overwrites = channel.overwrites_for(guild.default_role)
                overwrites.send_messages = None
            except discord.errors.Forbidden:
                pass
        await self.config.guild(guild).nextbump.set(None)
    
    async def start_timer(self, guild: discord.Guild, remaining):
        remaining = int(remaining)
        date = datetime.fromtimestamp(remaining)
        await discord.utils.sleep_until(date)
        await self.send_bumpmsg(guild)
    
    async def weekly_timer(self, guild: discord.Guild, remaining):
        remaining = int(remaining)
        date = datetime.fromtimestamp(remaining)
        await discord.utils.sleep_until(date)
        await self.reset_weekly(guild)
    
    async def reset_weekly(self, guild: discord.Guild):
        for member in guild.members:
            await self.config.member(member).weeklybumps.clear())
        next_reset = datetime.utcnow().timestamp() + 604800
        await self.config.guild(guild).nextweeklyreset.set(next_reset)
        await self.weekly_timer(guild, next_reset)

    @commands.Cog.listener("on_message")
    async def on_message(self, message): #The real shit
        if message.guild is None:
            return 

        data = await self.config.guild(message.guild).all()

        if data["channel"] is None:
            return 
        elif self.bot.get_channel(data["channel"]) is None:
            return 
        else:
            channel = self.bot.get_channel(data["channel"])
        
        clean = data["clean"]
        ty = data["ty"]
        lock = data["lock"]

        if clean and message.author.id != message.guild.me.id and message.author.id != 302050872383242240 and message.channel.id == channel.id:
            if message.channel.permissions_for(message.guild.me).manage_messages:
                await asyncio.sleep(2)
                await message.delete() 
            else:
                pass
        
        if not message.author.id == 302050872383242240 and message.embeds:
            return
        embeds = message.embeds[0]

        if "Bump done" in embeds.description:
            last_bump = data["nextbump"]
            if last_bump:
                if not (last_bump - message.created_at.timestamp() <= 0 or last_bump - message.created_at.timestamp() >= 0):
                    return
            next_bump = message.created_at.timestamp() + 7200
            await self.config.guild(message.guild).nextbump.set(next_bump)

            words = embeds.description.split(",")
            mention = words[0]

            if mention.startswith("<@!"):
                memberid = int(mention[3:-1])
            else:
                memberid = int(mention[2:-1])
            
            try:
                await channel.send(ty.replace("{member}", mention).replace("{guild}", message.guild.name).replace("{guild.id}", str(message.guild.id)))
            except Exception as e:
                await channel.send(e)
            
            if lock and message.channel.permissions_for(message.guild.me).manage_channels:
                try:
                    overwrites = message.channel.overwrites_for(message.guild.default_role)
                    overwrites.send_messages = False
                except discord.errors.Forbidden:
                    pass  


            try:
                member = message.guild.get_member(memberid)
                bumps = await self.config.member(member).bumps()
                bumps += 1
                await self.config.member(member).bumps.set(bumps)

                weekly_bumps = await self.config.member(member).weeklybumps()
                weekly_bumps += 1
                await self.config.member(member).weeklybumps.set(weekly_bumps)

                await self.start_timer(message.guild, next_bump)
                
            except Exception as e:
                await channel.send(e)
        else:
            if clean and message.channel.permissions_for(message.guild.me).manage_messages and message.channel.id == channel.id:
                await asyncio.sleep(2)
                await message.delete()
        

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.load_check.cancel()