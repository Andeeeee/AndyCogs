import discord
import re

from datetime import datetime
from redbot.core import commands, Config
from redbot.core.bot import Red
from typing import Optional

SHOP_REGEX = r"\*\*__LIGHTNING SALE__\*\* \(resets in (?P<time>[0-9,]+)m\) :[a-zA-Z0-9_]{2,32}: \*\*(?P<item>.*[a-zA-Z0-9_]{2,32})\*\* ─ \[(?P<price>[0-9,]+)\]  \(\[\*\*\*(?P<percent>[0-9,]+)% OFF!\*\*\*\]\)\*(?P<description>\w.*)\*"
WEBHOOK_REGEX = r"\*\*(?P<item>.*[a-zA-Z0-9_]{2,32})\*\* ─ \[(?P<price>[0-9,]+)\]  \(\[\*\*\*(?P<percent>[0-9,]+)% OFF!\*\*\*\]\)\*(?P<description>\w.*)\*"

class DankSales(commands.Cog):
    """Post sales and view stats about dankmemer item sales"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 160805014090190130501014, True)

        default_guild = {
            "channel": None,
            "pingrole": None,
            "rate": 50,
        }

        default_global = {
            "nextsale": None,
            "lastitem": None,
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        item_dict = {
            "Alcohol": 818709704762851339,
        }

    def sub(self, match):
        return f":{match.group('name')}:"

    @commands.group(aliases=["danksales"])
    @commands.mod_or_permissions(manage_guild=True)
    async def danksale(self, ctx: commands.Context):
        """Set server settings for dankmemer shop sales"""
        pass

    @danksale.command()
    async def channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set the channel to send shop sales to"""
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Cleared the channel")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(f"Now sending dankmemer shop sales to {channel.mention}")

    @danksale.command(aliases=["role"])
    async def pingrole(
        self, ctx: commands.Context, role: Optional[discord.Role] = None
    ):
        """Set the role to ping if the rate is over the configured rate"""
        if not role:
            await self.config.guild(ctx.guild).pingrole.clear()
            await ctx.send("No longer using a pingrole")
        else:
            await self.config.guild(ctx.guild).pingrole.set(role.id)
            await ctx.send(f"I will now ping `{role.name}` for shop sales")

    @danksale.command()
    async def rate(self, ctx: commands.Context, rate: int):
        """Set the rate for the bot to ping the pingrole for sales"""
        if rate <= 0 or rate >= 90:
            return await ctx.send("The rate should be above 1 and less than 90")
        await self.config.guild(ctx.guild).rate.set(rate)
        await ctx.send("Updated the rate")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if not message.author.id == 270904126974590976 and message.webhook_id is None:
            return "not dank"
        if not message.embeds:
            return "no embeds"
        try:
            if not "LIGHTNING SALE" in str(message.embeds[0].description):
                if message.webhook_id is None:
                    return "Ligthing sale not in description"
        except (IndexError, TypeError):
            return "indexerror"

        nextsale = await self.config.nextsale()
        if not nextsale:
            pass
        elif (datetime.utcnow() - datetime.fromtimestamp(nextsale)).total_seconds() < 0:
            return "next sale isn't there"

        replace_list = [
            "⏣ ",
            "(https://www.youtube.com/watch?v=_BD140nCDps)",
            "(https://www.youtube.com/watch?v=WPkMUU9tUqk)",
            "\n",
        ]

        filtered_message = str(message.embeds[0].description)
        for item in replace_list:
            filtered_message = filtered_message.replace(item, "")

        filtered_message = re.sub(
            "<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
            self.sub,
            filtered_message,
        )
        filtered_message = filtered_message.strip()

        if message.webhook_id is None:
            match = re.match(SHOP_REGEX, filtered_message)
        else:
            match = re.match(WEBHOOK_REGEX, filtered_message)
            
        if not match:
            return "no match"

        all_guilds = await self.config.all_guilds()
        for guild_id, data in all_guilds.items():
            if data["channel"]:
                e = discord.Embed(
                    title="LIGHTNING SALE",
                    color=discord.Color.blurple(),
                    description=f"**{match.group('item')}** ─ [⏣ {match.group('price')}](https://www.youtube.com/watch?v=_BD140nCDps)\n",
                )
                e.description += match.group("description")
                channel = self.bot.get_channel(data["channel"])
                content = ""
                if int(match.group("percent")) >= data["rate"]:
                    role = data["pingrole"]
                    if not role:
                        pass
                    else:
                        guild = self.bot.get_guild(int(guild_id))
                        if not guild:
                            pass 
                        else:
                            role = guild.get_role(data["pingrole"])
                            if not role:
                                pass
                            else:
                                content += f"{role.mention}: "

                content += f"**{match.group('item')}** is on sale at **{match.group('percent')}%** off"
                allowed_mentions = discord.AllowedMentions(roles=True)
                try:
                    message = await channel.send(
                        content=content, embed=e, allowed_mentions=allowed_mentions
                    )
                except (discord.errors.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
                else:
                    try:
                        await message.publish()
                    except (discord.Forbidden, discord.HTTPException):
                        pass 

        nextsale = datetime.utcnow().timestamp() + int(match.group("time")) * 60
        await self.config.nextsale.set(nextsale)
        await self.config.lastitem.set(match.group("item"))
