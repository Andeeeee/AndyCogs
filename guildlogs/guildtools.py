import discord 
from redbot.core import commands
from redbot.core import Config 
from typing import Optional
from datetime import datetime, timedelta
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

class GuildTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True)


        default_global = {
            "logchannel": None,
            "blacklist": [],
        }

        self.config.register_global(**default_global)

        await self.check_for_downtime_sneakers()
    
    async def fetch_guild(self, guild):
        if str(guild).isdigit():
            return self.bot.get_guild(int(guild))
        else:
            return discord.utils.get(self.bot.guilds, name=guild)
    
    async def check_for_downtime_sneakers(self):
        bl = await self.config.blacklist()
        for guild in self.bot.guilds:
            if guild.id in bl:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send("Fuckers tried to sneak me in while I was offline eh? Fuck off losers")
                        await guild.leave()
                await guild.leave()
            
    
    @commands.group(name="guildtools")
    @commands.is_owner()
    async def guildtools(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send_help("guildlog")
    
    @guildtools.command(name="channel")
    async def channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        if not channel:
            await ctx.send_help("guildtools channel")
            return 
        await self.config.logchannel.set(channel.id)
        await ctx.send("Done.")
    
    @guildtools.command(name="blacklist", aliases=["bl"])
    async def guildtool_blacklist(self, ctx, guild: int):
        bl = await self.config.blacklist()
        bl.append(guild)
        await self.config.blacklist.set(bl)
    

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild):
        try:
            logchannel = await self.config.logchannel()
            logchannel = self.bot.get_channel(logchannel)

            if guild.id in await self.config.blacklist():
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send("Your blacklisted.")
                        await guild.leave()
                        return 

                await guild.leave()

            if not logchannel:
                return 

            datetime = guild.created_at

            past_time = (datetime.utcnow() - datetime).days

            bots = 0
            humans = 0
            vc = 0 
            tc = 0

            afk = guild.afk_channel
            if afk is None:
                afk = "Not Set"

            feature_list = ""

            for feature in guild.features:
                feature_list += f"✅ {feature} \n"

            if len(feature_list) == 0:
                feature_list = "None"

            for member in guild.members:
                if member.bot:
                    bots += 1 
                else:
                    humans += 1
            
            for channel in guild.channels:
                if channel.type is discord.ChannelType.text:
                    tc += 1 
                elif channel.type is discord.ChannelType.voice:
                    vc += 1

            
            total_guilds = len(self.bot.guilds)
            total_members = 0

            for server in self.bot.guilds:
                total_members += len(server.members)

            e = discord.Embed(title="The Bot has joined a Guild!", 
            description=f"The bot is now in {total_guilds} guilds and has {total_members} members. ",
            color=discord.Color.green())

            e.description += f"The guild was created at **{guild.created_at}**, that's about **{past_time}** days ago!"
            e.add_field(name="Members", value=f"Total Users: **{len(guild.members)}** \n Humans: **{humans}** • Bots: **{bots}**")
            e.add_field(name="Channels", value=f"Text Channels: **{tc}** \n Voice Channels: **{vc}**")
            e.add_field(name="Utilities", value=f"Owner Mention: **{guild.owner.mention}** \n Owner Name & Tag: **{guild.owner}** \n Owner ID: **{guild.owner.id}** \n Verification Level: **{guild.verification_level}** \n Server ID: **{guild.id}**. \n Region: **{guild.region}**")
            e.add_field(name="Misc", value=f"AFK Channel: **{afk}** \n AFK Timeout: **{guild.afk_timeout}** \n Custom Emojis: **{len(guild.emojis)}** \n Roles: **{len(guild.roles)}**")
            e.add_field(name="Features", value=feature_list)

            await logchannel.send(embed=e)
        except(Exception) as e:
            await logchannel.send(e)
    
    @commands.Cog.listener("on_guild_remove")
    async def on_guild_remove(self, guild):
        try:
            logchannel = await self.config.logchannel()
            logchannel = self.bot.get_channel(logchannel)
            if not logchannel:
                return 

            datetime = guild.created_at

            past_time = (datetime.utcnow() - datetime).days

            bots = 0
            humans = 0
            vc = 0 
            tc = 0

            afk = guild.afk_channel
            if afk is None:
                afk = "Not Set"

            feature_list = ""

            for feature in guild.features:
                feature_list += f"✅ {feature} \n"

            if len(feature_list) == 0:
                feature_list = "None"

            for member in guild.members:
                if member.bot:
                    bots += 1 
                else:
                    humans += 1
            
            for channel in guild.channels:
                if channel.type is discord.ChannelType.text:
                    tc += 1 
                elif channel.type is discord.ChannelType.voice:
                    vc += 1

            
            total_guilds = len(self.bot.guilds)
            total_members = 0

            for server in self.bot.guilds:
                total_members += len(server.members)

            e = discord.Embed(title="The Bot has left a Guild :(", 
            description=f"The bot is now in {total_guilds} guilds and has {total_members} members. ",
            color=discord.Color.green())

            e.description += f"The guild was created at **{guild.created_at}**, that's about **{past_time}** days ago!"
            e.add_field(name="Members", value=f"Total Users: **{len(guild.members)}** \n Humans: **{humans}** • Bots: **{bots}**")
            e.add_field(name="Channels", value=f"Text Channels: **{tc}** \n Voice Channels: **{vc}**")
            e.add_field(name="Utilities", value=f"Owner Mention: **{guild.owner.mention}** \n Owner Name & Tag: **{guild.owner}** \n Owner ID: **{guild.owner.id}** \n Verification Level: **{guild.verification_level}** \n Server ID: **{guild.id}**. \n Region: **{guild.region}**")
            e.add_field(name="Misc", value=f"AFK Channel: **{afk}** \n AFK Timeout: **{guild.afk_timeout}** \n Custom Emojis: **{len(guild.emojis)}** \n Roles: **{len(guild.roles)}**")
            e.add_field(name="Features", value=feature_list)

            await logchannel.send(embed=e)
        except(Exception) as e:
            await logchannel.send(e)
    
    @commands.command(name="getguild")
    @commands.is_owner()
    async def getguild(self, ctx, * , guild):
        try:
            guild = await self.fetch_guild(guild)

            if guild is None:
                await ctx.send("I could not find this guild")
                await ctx.send(guild)
                return

            created_at = guild.created_at

            joined_at = guild.me.joined_at

            past_time = (datetime.utcnow() - created_at).days
            past_time_me = (datetime.utcnow() - joined_at).days

            bots = 0
            humans = 0
            vc = 0 
            tc = 0

            afk = guild.afk_channel
            if afk is None:
                afk = "Not Set"

            feature_list = ""

            for feature in guild.features:
                feature_list += f"✅ {feature} \n"

            if len(feature_list) == 0:
                feature_list = "None"

            for member in guild.members:
                if member.bot:
                    bots += 1 
                else:
                    humans += 1
                
            for channel in guild.channels:
                if channel.type is discord.ChannelType.text:
                    tc += 1 
                elif channel.type is discord.ChannelType.voice:
                    vc += 1

                
            total_guilds = len(self.bot.guilds)
            total_members = 0

            for server in self.bot.guilds:
                total_members += len(server.members)

            e = discord.Embed(title=guild.name, description=f"The guild was created on **{created_at}**, thats about **{past_time}** days ago! ")
            e.description += f"I joined this guild on **{joined_at}**, thats about **{past_time_me}** days ago!"

            e.add_field(name="Members", value=f"Total Users: **{len(guild.members)}** \n Humans: **{humans}** • Bots: **{bots}**")
            e.add_field(name="Channels", value=f"Text Channels: **{tc}** \n Voice Channels: **{vc}**")
            e.add_field(name="Utilities", value=f"Owner Mention: **{guild.owner.mention}** \n Owner Name & Tag: **{guild.owner}** \n Owner ID: **{guild.owner.id}** \n Verification Level: **{guild.verification_level}** \n Server ID: **{guild.id}**. \n Region: **{guild.region}**")
            e.add_field(name="Misc", value=f"AFK Channel: **{afk}** \n AFK Timeout: **{guild.afk_timeout}** \n Custom Emojis: **{len(guild.emojis)}** \n Roles: **{len(guild.roles)}**")
            e.add_field(name="Features", value=feature_list)

            await ctx.send(embed=e)
        except(Exception) as e:
            await ctx.send(e)
        
    @commands.command(name="listguilds")
    @commands.is_owner()
    async def listguilds(self, ctx):
        guilds = self.bot.guilds 
        guildstring = ""
        for guild in guilds:
            guildstring += guild.name 
            guildstring += f" `{guild.id}` \n"

        embeds = []
        guild_pages = list(pagify(guildstring))
        for index, page in enumerate(guild_pages, start=1):
            embed = discord.Embed(color=discord.Color.green(), title="Servers", description=page)
            embed.set_footer(text=f"{index}/{len(guild_pages)}")
            embeds.append(embed)

        await menu(ctx, embeds, DEFAULT_CONTROLS)
        

    

    