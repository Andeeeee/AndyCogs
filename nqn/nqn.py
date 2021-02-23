import aiohttp
import discord 
import re

from rapidfuzz import process
from redbot.core import commands, Config
from typing import Optional 
from unidecode import unidecode

class NotQuiteNitro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 160805014090190130501014, True) 
    
        default_guild = {
            "delete": False,
            "auto": False,
        }

        self.emoji_regex = r"(?P<left><)?a?:(?P<name>\w+):(?P<right>>)?"
        self.webhook_cache = {}
        self.session = aiohttp.ClientSession()
        self.allowed_mentions = discord.AllowedMentions(users=True, everyone=False, roles=False)

        self.config.register_guild(**default_guild)
    
    def sub(self, match):
        if match.group("left") == "<":
            return match.group(0)
        emoji = self.get_fuzzy_emoji(match.group("name"))
        if not emoji:
            return match.group(0)
        return emoji
    
    def get_fuzzy_emoji(self, name: str):
        emoji = discord.utils.get(self.bot.emojis, name=name)
        if emoji:
            return str(emoji)

        results = []

        for r in process.extract(
            name,
            {e: unidecode(e.name) for e in self.bot.emojis},
            limit=None,
            score_cutoff=75,
        ):
            results.append(r[2], r[1])
        
        if not results:
            return None

        sorted_result = sorted(results, key = lambda m: m[1], reverse=True)
        
        return str(sorted_result[0][0])
    
    async def tick(self, ctx: commands.Context) -> None:
        emoji = ctx.bot.get_emoji(813894305634713601)
        if not emoji:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction(emoji)
    
    async def webhook_send(self, ctx: commands.Context, message: str, **kwargs) -> None:
        if webhook := self.webhook_cache.get(ctx.channel.id):
            try:
                await webhook.send(
                    content = message,
                    username = ctx.author.display_name,
                    avatar_url = ctx.author.avatar_url,
                    allowed_mentions = self.allowed_mentions,
                    **kwargs
                )
            except discord.errors.Forbidden:
                await ctx.send(message)
            except (discord.InvalidArgument, discord.NotFound):
                del self.webhook_cache[ctx.channel.id]

        else:
            webhooks = await ctx.channel.webhooks()
            webhook_list = [w for w in webhooks if w.type == discord.WebhookType.incoming]
            if webhook_list:
                webhook = webhook_list[0]
            else:
                if len(webhooks) == 10:
                    await webhooks[-1].delete()
                
                webhook = await ctx.channel.create_webhook(
                    name = f"{ctx.me} Webhook",
                    reason = "For the {} command. Requested by {}".format(ctx.command.name, ctx.author.name),
                    avatar = await ctx.me.avatar_url.read(),
                )
            
            self.webhook_cache[ctx.channel.id] = webhook

            try:
                await webhook.send(
                    content = message,
                    username = ctx.author.display_name,
                    avatar_url = ctx.author.avatar_url,
                    allowed_mentions = self.allowed_mentions,
                    **kwargs
                )
            except discord.errors.Forbidden:
                await ctx.send(message)
            except (discord.InvalidArgument, discord.NotFound):
                del self.webhook_cache[ctx.channel.id]

    @commands.group(aliases=["notquitenitroset"])
    @commands.guild_only()
    async def nqnset(self, ctx):
        """A group for manaing Not Quite Nitro settings"""
        pass 
    
    @nqnset.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def auto(self, ctx, auto: Optional[bool] = None):
        """Toggle whether the bot should automatically convert emojis without commands.
        You can specify either True or False after this, also works as a toggle"""
        cur = await self.config.guild(ctx.guild).auto()

        if auto is None:
            if cur:
                auto = False 
            else:
                auto = True 
        
        await self.config.guild(ctx.guild).auto.set(auto)
        await self.tick(ctx)

    @nqnset.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def delete(self, ctx, delete: Optional[bool] = None):
        """Toggles whether Not Quite Nitro should delete Not Quite Nitro messages.. 
        You can specify either True or False after this, also works as a toggle"""
        cur = await self.config.guild(ctx.guild).delete()

        if delete is None:
            if cur:
                delete = False 
            else:
                delete = True
        
        await self.config.guild(ctx.guild).delete.set(delete)
        await self.tick(ctx)
    
    @nqnset.command(aliases=["showsettings"])
    async def settings(self, ctx):
        """Show server settings for Not Quite Nitro"""
        data = await self.config.guild(ctx.guild).all()

        e = discord.Embed(
            title = f"Not Quite Nitro settings for {ctx.guild.name}",
            color = await ctx.embed_color(),
        )

        e.add_field(name="Automatic", value=data["auto"], inline=False)
        e.add_field(name="Delete", value=data["delete"], inline=False)

        await ctx.send(embed=e)

    @commands.command(aliases=["notquitenitro"])
    async def nqn(self, ctx, * , message: str):
        new_message = re.sub(self.emoji_regex, self.sub, message)
        
        if message == new_message:
            return await ctx.send("There't nothing I can convert here :(")
            
        await self.webhook_send(ctx, message)

        if ctx.channel.permissions_for(ctx.me).manage_messages and (await self.config.guild(ctx.guild).delete()):
            try:
                await ctx.message.delete()
            except (discord.HTTPException, discord.errors.Forbidden):
                pass 

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return 
        if not message.guild:
            return 
        if not (await self.config.guild(message.guild).auto()):
            return

        new_message = re.sub(self.emoji_regex, self.sub, message.content)

        if new_message == message.content:
            return 
        
        await self.webhook_send(message, new_message)

        if (await self.config.guild(message.guild).delete()) and message.channel.permissions_for(message.guild.me).manage_messages:
            try:
                await message.delete()
            except (discord.HTTPException, discord.errors.Forbidden):
                pass 