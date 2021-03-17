"""
MIT License

Copyright (c) 2021 Andy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import discord
import redbot 

from redbot.core import commands, Config 
from redbot.core.bot import Red
from redbot.core.commands import BucketType
from typing import Optional, Union

async def not_blacklisted(ctx: commands.Context):
    cog = ctx.bot.get_cog("UserPhone")
    blacklisted = await cog.config.blacklist()
    return ctx.author.id not in blacklisted

class UserPhone(commands.Cog):
    """A cog to chat with other users that happen to pick up the phone"""

    def __init__(self, bot: Red):
        self.bot = bot 

        self.config = Config.get_conf(
            self, identifier=160805014090190130501014, force_registration=True
        )

        default_global = {
            "reportchannel": None,
            "rules": ["No Invite Links", "NSFW connections must be marked by passing `True` to the nsfw paramater while running the userphone command", "No False Reports", "Abide by Discord ToS"],
            "blacklist": [],
        }

        self.config.register_global(**default_global) 

        self._connections = {}
    
    @commands.group()
    @commands.is_owner()
    async def userphoneset(self, ctx: commands.Context):
        """Set global settings for userphone, such as reportchannel."""
        pass 
    
    @userphoneset.command()
    async def reportchannel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set the channel to log user reports to"""
        if not channel:
            await self.config.reportchannel.clear()
            await ctx.send("I will no longer send reports to a channel")
        else:
            await self.config.reportchannel.set(channel.id)
            await ctx.send(f"Now sending reports to {channel.mention}")

    @userphoneset.command(name="add-rule")
    async def add_rule(self, ctx: commands.Context, *, rule: str):
        """Add a rule to the userphone rule list"""
        rules = await self.config.rules()
        rules.append(rule)
        await self.config.rules.set(rules)
        await ctx.send("Added on to the rules list")
    
    @userphoneset.command(name="remove_rule")
    async def remove_rule(self, ctx: commands.Context, *, num: int):
        """Remove a rule from the list of rules. Should be its position in the list. Starts from one"""
        rules = await self.config.rules()

        if num > len(rules):
            return await ctx.send("This rule doesn't exist...")
        
        try:
            rules.pop(num - 1)
        except IndexError:
            return await ctx.send("This rule doesn't exist...")

        await self.config.rules.set(rules)
        await ctx.send("Removed from the list of rules")
    
    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 6, BucketType.user)
    @commands.max_concurrency(1, BucketType.channel)
    @commands.guild_only()
    @commands.check(not_blacklisted)
    async def userphone(self, ctx: commands.Context, nsfw: bool = False):
        """Start a userphone connection!"""
        if not self._connections:
            data = {"other_channel": None, "nsfw": nsfw}
            self._connections[ctx.channel.id] = data
            await ctx.send("Connection Created!")
        elif ctx.channel.id in self._connections:
            del self._connections[ctx.channel.id]
            await ctx.send("Connection Closed")
        else:
            for channel_id, data in self._connections:
                if channel_id == ctx.channel.id:
                    continue 
                elif data["other_channel"] is not None:
                    continue 
                data["other_channel"] = ctx.channel 
                await ctx.send("Connection created!")


    @userphone.command()
    async def rules(self, ctx: commands.Context):
        """View userphone rules"""
        rules = await self.config.rules()

        if not rules:
            await ctx.send("There aren't any rules, but make sure to follow Discord ToS")
        else:
            e = discord.Embed(title = "Userphone Rules", color = await ctx.embed_color(), description="\n\n".join(rules))
            await ctx.send(embed=e)
    
    @userphone.command()
    @commands.cooldown(1, 30, BucketType.user)
    async def report(self, ctx: commands.Context, user: Union[discord.Member, discord.User, int], *, reason: str):
        """Report a user to the bot owner(s)"""
        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except discord.NotFound:
                return await ctx.send("This isn't a valid user wyd")
        
        channel = await self.config.reportchannel()

        if not channel:
            return await ctx.send("My owner has not setup a reportchannel.")
        channel = self.bot.get_channel(channel)
        if not channel:
            await self.config.reportchannel.clear()
            await ctx.send("I couldn't find the reportchannel")
        
        e = discord.Embed(title = "Userphone Report", color = await ctx.embed_color())
        e.add_field(name="Context and Info", value=f"Report sent by: {ctx.author} ({ctx.author.id})\nReported from the guild: {ctx.guild.name} ({ctx.guild.id})")
        e.add_field(name="Reported User", value=f"{user} ({user.id})")
        e.add_field(name="Reason", value=reason)

        try:
            await channel.send(embed=e)
        except discord.errors.Forbidden:
            await ctx.send("I dont have permissions to send messages in the reportchannel")
    
    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return 
        other_channel = None

        for channel_id, data in self._connections:
            if channel_id == message.channel.id:
                other_channel = data["channel"]
            elif data["other_channel"].id == message.author.id:
                other_channel = self.bot.get_channel(channel_id)
        
        if not other_channel:
            return 
        try:
            await other_channel.send(f"{message.author}: {message.content}")
        except (discord.errors.Forbidden, discord.HTTPException, discord.NotFound, AttributeError):
            return 

    
