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
            "rules": [
                "No Invite Links",
                "NSFW connections must be marked by passing `True` to the nsfw paramater while running the userphone command",
                "No False Reports",
                "Abide by Discord ToS",
            ],
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
    async def reportchannel(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
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
    @commands.guild_only()
    @commands.check(not_blacklisted)
    async def userphone(self, ctx: commands.Context, nsfw: bool = False):
        """Start a userphone connection!"""
        if not self._connections:
            data = {"other_channel": None, "nsfw": nsfw, "participants": []}
            self._connections[ctx.channel.id] = data
            await ctx.send(":telephone: **Calling on userphone...**")
        elif ctx.channel.id in self._connections:
            if not ctx.author.id in self._connections[ctx.channel.id]["participants"]:
                return await ctx.send("You haven't participated in this conversation, you can't hang up!")
            other_channel = self._connections[ctx.channel.id]["other_channel"]
            del self._connections[ctx.channel.id]
            await ctx.send(":telephone: **You hung up the userphone.**")
            try:
                await other_channel.send(":telephone: **The other party hung up the userphone.**")
            except (
                discord.NotFound,
                discord.errors.Forbidden,
                discord.HTTPException,
                AttributeError,
            ):
                return
        else:
            for channel_id, data in self._connections.items():
                if data["other_channel"] is not None:
                    continue 
                if ctx.channel == data["other_channel"]:
                    if not ctx.author.id in data["participants"]:
                        return await ctx.send("You haven't participated in this conversation, you can't hang up!")
                    await ctx.send(":telephone: **You hung up the userphone.**")
                    other_channel = self.bot.get_channel(channel_id)
                    del self._connections[channel_id]
                    try:
                        await other_channel.send(":telephone: **The other party hung up the userphone.**")
                    except (
                        discord.NotFound,
                        discord.errors.Forbidden,
                        discord.HTTPException,
                        AttributeError,
                    ):
                        pass
                    return 
                if data["nsfw"] != nsfw:
                    continue

                data["other_channel"] = ctx.channel
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue 
                await ctx.send(":telephone: **Calling on userphone...**")
                await ctx.send(":telephone: **The other party has picked up the userphone!**")
                await channel.send(":telephone: **The other party has picked up the userphone!**")

    @userphone.command()
    async def rules(self, ctx: commands.Context):
        """View userphone rules"""
        rules = await self.config.rules()

        if not rules:
            await ctx.send(
                "There aren't any rules, but make sure to follow Discord ToS"
            )
        else:
            e = discord.Embed(
                title="Userphone Rules",
                color=await ctx.embed_color(),
                description="\n\n".join(rules),
            )
            await ctx.send(embed=e)

    @userphone.command()
    @commands.cooldown(1, 30, BucketType.user)
    async def report(
        self,
        ctx: commands.Context,
        user: Union[discord.Member, discord.User, int],
        nsfw: Optional[bool] = False,
        *,
        reason: str,
    ):
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

        e = discord.Embed(title="Userphone Report", color=await ctx.embed_color())
        e.add_field(
            name="Context and Info",
            value=f"Report sent by: {ctx.author} ({ctx.author.id})\nReported from the guild: {ctx.guild.name} ({ctx.guild.id})\nNSFW: {nsfw}",
        )
        e.add_field(name="Reported User", value=f"{user} ({user.id})")
        e.add_field(name="Reason", value=reason)

        try:
            await channel.send(embed=e)
        except discord.errors.Forbidden:
            await ctx.send(
                "I dont have permissions to send messages in the reportchannel"
            )

    @userphone.group()
    @commands.is_owner()
    async def blacklist(self, ctx: commands.Context):
        """Manage blacklist settings"""
        pass

    @blacklist.command(name="add")
    async def _add(
        self, ctx: commands.Context, user: Union[discord.Member, discord.User, int]
    ):
        """Adds a user to the blacklist"""
        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except discord.NotFound:
                return await ctx.send("This user doesn't exist wyd")

        if await self.bot.is_owner(user):
            return await ctx.send("You can't blacklist owners :rage:")

        blacklisted = await self.config.blacklist()
        if user.id in blacklisted:
            return await ctx.send("You can't blacklist a blacklisted user :thinking:")
        blacklisted.append(user.id)
        await self.config.blacklist.set(blacklisted)
        await ctx.send(f"Added **{user.name}** to the blacklist")

    @blacklist.command(name="remove")
    async def _remove(
        self, ctx: commands.Context, user: Union[discord.Member, discord.User, int]
    ):
        """Removes a user from the blacklist"""
        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except discord.NotFound:
                return await ctx.send("This isn't a user wyd")

        blacklisted = await self.config.blacklist()
        try:
            blacklisted.remove(user.id)
        except ValueError:
            return await ctx.send("This user isn't blacklisted :thinking:")
        await self.config.blacklist.set(blacklisted)
        await ctx.send(f"Removed **{user.name}** to the blacklist")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        other_channel = None

        for channel_id, data in self._connections.items():
            if channel_id == message.channel.id:
                other_channel = data["other_channel"]
                break 
            elif data["other_channel"].id == message.channel.id:
                other_channel = self.bot.get_channel(channel_id)
                break

        if not other_channel:
            return
        try:
            await other_channel.send(f"**{message.author}:** {message.content}", allowed_mentions=discord.AllowedMentions(users=False, everyone=False, roles=False))
        except (
            discord.errors.Forbidden,
            discord.HTTPException,
            discord.NotFound,
            AttributeError,
        ):
            pass 
        else:
            self._connections[channel_id]["participants"].append(message.author.id)
