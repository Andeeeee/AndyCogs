import asyncio
import discord
import re

from datetime import datetime
from rapidfuzz import process
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from typing import Optional
from unidecode import unidecode

gift_regex = re.compile(
    r"You gave (?P<user>.+[a-zA-Z0-9_])?  ?\*\*(?P<amount>[0-9,]+)\*\* ?(?:(?P<item>[a-zA-Z0-9_]{2,32}))?"
)


class DankLogs(commands.Cog):
    """Track things for dankmemer"""

    __author__ = "Andy"
    __version__ = "1.0.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 160805014090190130501014, True)

        default_guild = {
            "channel": None,
            "itemvalues": {
                "alcohol": 5000,
                "banknote": 225000,
                "blob": 900000000,
                "bread": 30000,
                "candy": 3000,
                "cheese": 0,
                "chillpill": 0,
                "cookie": 0,
                "cupidsbigtoe": 100000,
                "cutters": 300000,
                "dank": 200000,
                "deer": 40000,
                "dragon": 60000,
                "exoticfish": 10000,
                "fakeid": 700,
                "fish": 250,
                "fishingpole": 7500,
                "huntingrifle": 7500,
                "jacky": 5000000,
                "landmine": 2500,
                "laptop": 1000,
                "legendaryfish": 25000,
                "lifesaver": 4000,
                "meme": 100000,
                "normie": 80000,
                "padlock": 1500,
                "pepe": 95000,
                "pepecoin": 900000,
                "pepemedal": 8500000,
                "pepetrophy": 45000000,
                "phone": 750,
                "pinkphallicobject": 5,
                "pizza": 100000,
                "rabbit": 350,
                "rarefish": 2500,
                "santashat": 150000,
                "skunk": 250,
                "spinner": 7000,
                "tidepod": 15000,
                "wishlist": 15000,
            },
        }

        default_member = {
            "shared": 0,
            "gifted": {},
            "received": 0,
            "receiveditems": {},
            "giftedusers": {},
            "sharedusers": {},
            "logs": [],
        }

        default_channel = {
            "ignored": False,
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.config.register_channel(**default_channel)

    def comma_format(self, number: int):
        return "{:,}".format(int(number))

    async def get_last_message(self, message):
        async for m in message.channel.history(before=message, limit=5):
            if m.author.bot:
                pass
            else:
                return m

    def get_fuzzy_member(self, ctx, name):
        return discord.utils.get(ctx.guild.members, name=name)

    @commands.group(aliases=["dls"])
    @commands.mod_or_permissions(manage_guild=True)
    async def danklogset(self, ctx):
        """Set server settings for dank logs"""
        pass

    @danklogset.command()
    async def channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set the channel to log actions to"""
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("I will no longer have a channel")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(f"I will now log actions to {channel.mention}")

    @danklogset.command(aliases=["itemprice"])
    async def itemvalue(self, ctx, item: str, price: int):
        item_values = await self.config.guild(ctx.guild).itemvalues()
        if item not in item_values:
            return await ctx.send("This item does not exist")
        item_values[item] = price
        await self.config.guild(ctx.guild).itemvalues.set(item_values)
        await ctx.send(f"Done. The price for **{item}** is now **{price}**")

    @commands.group(aliases=["dankstats"], invoke_without_command=True)
    async def dankinfo(self, ctx, user: Optional[discord.Member] = None):
        """View info for yourself or a user from dankmemer"""
        if not ctx.invoked_subcommand:
            if not user:
                user = ctx.author

            data = await self.config.member(user).all()

            e = discord.Embed(
                title=f"Dank Memer Gift & Share Stats for {user}",
                color=await ctx.embed_color(),
                description="Shared Money: {}\nTotal Shared Items: {}\nTotal Shared Users: {}\nTotal Gifted Users: {}".format(
                    data["shared"],
                    len(data["gifted"]),
                    len(data["sharedusers"]),
                    len(data["giftedusers"]),
                ),
            )
            await ctx.send(embed=e)

    @dankinfo.command()
    async def shared(self, ctx, user: Optional[discord.Member] = None):
        """View the amount you or a user has shared"""
        if not user:
            user = ctx.author

        shared = await self.config.member(user).shared()

        await ctx.send(
            f"**{user}** has shared a total of **{self.comma_format(shared)}** coins in this server"
        )

    @dankinfo.command()
    async def gifted(self, ctx, user: Optional[discord.Member] = None):
        """View the amount a user has gifted (only shows items)"""
        if not user:
            user = ctx.author

        gifted = await self.config.member(user).gifted()
        gifted = sorted(gifted.items(), key=lambda m: m[1], reverse=True)

        e = discord.Embed(title=f"{user}'s gifted items")

        formatted_gifted = ""

        for item, amount in gifted:
            formatted_gifted += "{}: {}\n".format(item, amount)

        if len(formatted_gifted) == 0 or formatted_gifted == "":
            return await ctx.send("This user has not gifted anything yet")

        if len(formatted_gifted) >= 2048:
            pages = list(pagify(formatted_gifted))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Gifted Items for {user}",
                    description=p,
                    color=await ctx.embed_color(),
                )
                e.set_footer(text=f"Page {i} out of {len(pages)} pages")
                embeds.append(e)

            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Gifted Items for {user}",
                description=formatted_gifted,
                color=await ctx.embed_color(),
            )
            await ctx.send(embed=e)

    @dankinfo.command()
    async def itemvalues(self, ctx):
        """View the values of the items set for your server. You can change them with `[p]danklogset itemvalue <item> <price>`"""
        item_values = await self.config.guild(ctx.guild).itemvalues()
        formatted_items = ""

        for item, price in item_values.items():
            formatted_items += f"{item}: {price}"
        e = discord.Embed(
            title="Item Values",
            color=await ctx.embed_color(),
            description=formatted_items,
        )
        await ctx.send(embed=e)

    @dankinfo.command()
    async def received(self, ctx, user: Optional[discord.Member] = None):
        """View the items a user has received"""
        if not user:
            user = ctx.author

        received = await self.config.member(user).received()

        await ctx.send(f"**{user}** has received {self.comma_format(received)} coins")

    @dankinfo.command()
    async def sharedusers(self, ctx, user: Optional[discord.Member] = None):
        """View the users a user has shared money to"""
        if not user:
            user = ctx.author
        sharedusers = await self.config.member(user).sharedusers()
        sharedusers = sorted(sharedusers.items(), key=lambda m: m[1], reverse=True)

        formatted_shared = ""

        for member, shared in sharedusers:
            formatted_shared += f"<@{member}>: {shared}\n"

        if len(formatted_shared) == 0 or formatted_shared == "":
            return await ctx.send("This user has shared nothing")

        if len(formatted_shared) >= 2048:
            pages = list(pagify(formatted_shared))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Users {user} has shared to",
                    description=p,
                    color=await ctx.embed_color(),
                )
                embeds.append(e)

            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Users {user} has shared to",
                description=formatted_shared,
                color=await ctx.embed_color(),
            )
            await ctx.send(embed=e)

    @dankinfo.command()
    async def receivedamount(self, ctx, user: Optional[discord.Member] = None):
        """View the price of the items you have received, the list is from a custom list and can be changed using `[p]danklogset itemprice <item> <price>`"""
        total_amount = 0
        if not user:
            user = ctx.author

        item_prices = await self.config.guild(ctx.guild).itemvalues()
        received = await self.config.member(user).receiveditems()

        if not received:
            return await ctx.send("You haven't received any items")

        for item, amount in received.items():
            total_amount += amount * item_prices[item]
        return await ctx.send(
            "You have received **{}** worth of items in **{}**".format(
                self.comma_format(total_amount), ctx.guild.name
            )
        )

    @dankinfo.command()
    async def giftedamount(self, ctx, user: Optional[discord.Member] = None):
        """View the price of the items you have given, the list is from a custom list and can be changed using `[p]danklogset itemprice <item> <price>`"""
        total_amount = 0
        if not user:
            user = ctx.author

        item_prices = await self.config.guild(ctx.guild).itemvalues()
        gifted = await self.config.member(user).gifted()

        if not gifted:
            return await ctx.send("You haven't gifted out anything")

        for item, amount in gifted.items():
            total_amount += amount * item_prices[item]
        return await ctx.send(
            "You have shared **{}** worth of items in **{}**".format(
                self.comma_format(total_amount), ctx.guild.name
            )
        )

    @dankinfo.command()
    async def giftedusers(self, ctx, user: Optional[discord.Member] = None):
        """View the users a user has gifted items to"""
        if not user:
            user = ctx.author
        giftedusers = await self.config.member(user).giftedusers()
        giftedusers = sorted(giftedusers.items(), key=lambda m: m[1], reverse=True)

        formatted_shared = ""

        for member, shared in giftedusers:
            formatted_shared += f"<@{member}>: {shared}\n"

        if len(formatted_shared) == 0 or formatted_shared == "":
            return await ctx.send("This user has shared nothing")

        if len(formatted_shared) >= 2048:
            pages = list(pagify(formatted_shared))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Users {user} has gifted to",
                    description=p,
                    color=await ctx.embed_color(),
                )
                embeds.append(e)

            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Users {user} has gifted to",
                description=formatted_shared,
                color=await ctx.embed_color(),
            )
            await ctx.send(embed=e)

    @dankinfo.command()
    async def receiveditems(self, ctx, user: Optional[discord.Member] = None):
        """View the items a user has received"""
        if not user:
            user = ctx.author

        received = await self.config.member(user).receiveditems()
        received = sorted(received.items(), key=lambda m: m[1], reverse=True)

        formatted_shared = ""

        for item, amount in received:
            formatted_shared += f"{item}: {amount}\n"

        if len(formatted_shared) == 0 or formatted_shared == "":
            return await ctx.send("This user has received nothing")

        if len(formatted_shared) >= 2048:
            pages = list(pagify(formatted_shared))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Items {user} has received",
                    description=p,
                    color=await ctx.embed_color(),
                )
                embeds.append(e)

            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Items {user} has received",
                description=formatted_shared,
                color=await ctx.embed_color(),
            )
            await ctx.send(embed=e)

    @dankinfo.command()
    @commands.mod_or_permissions(manage_guild=True)
    async def logs(self, ctx, user: Optional[discord.Member] = None):
        if not user:
            user = ctx.author

        logs = await self.config.member(user).logs()

        if len(logs) == 0:
            return await ctx.send("This user has no logs to show")

        logs = "\n\n".join(logs[::-1])

        if len(logs) >= 2048:
            pages = list(pagify(logs))
            embeds = []
            for i, p in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Logs for {user}",
                    description=p,
                    color=await ctx.embed_color(),
                )
                e.set_footer(text=f"Page {i} out of {len(pages)} pages")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send(
                embed=discord.Embed(
                    title=f"Logs for {user}",
                    description=logs,
                    color=await ctx.embed_color(),
                )
            )

    @dankinfo.command(aliases=["mostshared"])
    async def topshared(self, ctx, amount: int = 10):
        """View the people in the server that have shared the most COINS"""
        member_data = await self.config.all_members(ctx.guild)
        member_list = [
            (member, data["shared"])
            for member, data in member_data.items()
            if data["shared"] > 0 and ctx.guild.get_member(int(member)) is not None
        ]
        ordered_list = sorted(member_list, key=lambda m: m[1], reverse=True)[:amount]

        if not ordered_list:
            return await ctx.send("I have no tracked data for this server")

        leaderboard = []

        for i, data in enumerate(ordered_list, start=1):
            leaderboard.append(f"{i}. <@{data[0]}>: {self.comma_format(data[1])}")

        leaderboard = "\n".join(leaderboard)

        if len(leaderboard) >= 2048:
            pages = list(pagify(leaderboard))
            embeds = []
            for i, page in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Share Leaderboard for {ctx.guild}",
                    description=page,
                    color=await ctx.embed_color(),
                )
                e.set_footer(text=f"Page {i}/{len(pages)} pages")
                embeds.append(e)

            await menu(ctx, embeds, DEFAULT_CONTROLS)

        else:
            await ctx.send(
                embed=discord.Embed(
                    title=f"Share Leaderboard for {ctx.guild}",
                    description=leaderboard,
                    color=await ctx.embed_color(),
                )
            )

    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        if not message.author.id == 270904126974590976:
            return
        if "You gave" not in message.content:
            return

        if await self.config.channel(message.channel).ignored():
            return
        last_message = await self.get_last_message(message)
        filtered_content = (
            message.content.strip()
            .lstrip(f"<@{last_message.author.id}>")
            .lstrip(f"<@!{last_message.author.id}>")
            .replace("⏣ ", "")
            .strip()
        )
        filtered_content = "".join([unidecode(elem) for elem in filtered_content])

        match = re.match(gift_regex, filtered_content)
        amount = int(match.group("amount").replace(",", ""))
        member = match.group("user")
        shared_user = self.get_fuzzy_member(message, member)
        if not shared_user:
            return

        shared_user_data = await self.config.member(shared_user).all()
        user_data = await self.config.member(last_message.author).all()

        if last_message.content.lower().startswith(
            "pls share"
        ) or last_message.content.lower().startswith("pls give"):
            if str(shared_user.id) not in user_data["sharedusers"]:
                user_data["sharedusers"][str(shared_user.id)] = 0

            user_data["sharedusers"][str(shared_user.id)] += 1
            user_data["shared"] += amount
            shared_user_data["received"] += amount
            formatted_now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")
            user_data["logs"].append(
                f"At {formatted_now}, {self.comma_format(amount)} was shared to {shared_user} (ID of {shared_user.id})"
            )
            shared_user_data["logs"].append(
                f"At {formatted_now}, {self.comma_format(amount)} was received from {message.author} (ID of {message.author.id})"
            )
            await self.config.member(shared_user).set(shared_user_data)
            await self.config.member(last_message.author).set(user_data)

            channel = await self.config.guild(message.guild).channel()
            channel = self.bot.get_channel(channel)
            if not channel:
                return
            e = discord.Embed(
                title="Dankmemer Logs",
                description=f"{last_message.author.mention} shared {self.comma_format(amount)} coins to {shared_user.mention} in {message.channel.mention}\n [JUMP]({message.jump_url})",
            )
            await channel.send(embed=e)

        else:
            if str(shared_user.id) not in user_data["giftedusers"]:
                user_data["giftedusers"][str(shared_user.id)] = 0

            user_data["giftedusers"][str(shared_user.id)] += 1
            item = match.group("item")
            if item not in user_data["gifted"]:
                user_data["gifted"][item] = 0
            user_data["gifted"][item] += amount

            if item not in shared_user_data["receiveditems"]:
                shared_user_data["receiveditems"][item] = 0
            shared_user_data["receiveditems"][item] += amount

            formatted_now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")
            shared_user_data["logs"].append(
                f"On {formatted_now}, {last_message.author} gave {self.comma_format(amount)} {item}"
            )
            user_data["logs"].append(
                f"On {formatted_now}, {self.comma_format(amount)} {item} was sent to {shared_user}"
            )

            channel = await self.config.guild(message.guild).channel()
            channel = self.bot.get_channel(channel)
            await self.config.member(shared_user).set(shared_user_data)
            await self.config.member(last_message.author).set(user_data)
            if not channel:
                return
            e = discord.Embed(
                title="Dankmemer Logs",
                description=f"{last_message.author.mention} gave {amount} {item} to {shared_user.mention} in {message.channel.mention}\n [JUMP]({message.jump_url})",
            )
            await channel.send(embed=e)
