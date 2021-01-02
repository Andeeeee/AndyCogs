import discord
import aiohttp
from discord.ext import commands
import asyncio

#Webhook send_to_channel, get_webhook, and webhook_link_send taken from Phen-Cogs. https://github.com/phenom4n4n/phen-cogs

async def delete_quietly(ctx: commands.Context):
    if ctx.channel.permissions_for(ctx.me).manage_messages:
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

class InvalidWebhook(Exception):
    pass


class Webhook(commands.Cog):
    """A cog for webhooks"""

    cache = {}

    async def get_webhook(
        self,
        *,
        channel: discord.TextChannel = None,
        me: discord.Member = None,
        author: discord.Member = None,
        reason: str = None,
        ctx: commands.Context = None,
    ):
        if ctx:
            channel = channel or ctx.channel
            me = me or ctx.me
            author = author or ctx.author
            reason = (reason or f"For the {ctx.command.qualified_name} command",)

        link = self.cache.get(channel.id)
        if link:
            return link
        if channel.permissions_for(me).manage_webhooks:
            chan_hooks = await channel.webhooks()
            webhook_list = [
                w for w in chan_hooks if w.type == discord.WebhookType.incoming
            ]
            if webhook_list:
                webhook = webhook_list[0]
            else:
                creation_reason = f"Webhook creation requested by {author} ({author.id})"
                if reason:
                    creation_reason += f" Reason: {reason}"
                if len(chan_hooks) == 10:
                    await chan_hooks[-1].delete()
                webhook = await channel.create_webhook(
                    name=f"{me.name} Webhook",
                    reason=creation_reason,
                    avatar=await me.avatar_url.read(),
                )
            self.cache[channel.id] = webhook.url
            return webhook.url
        else:
            raise discord.Forbidden(
                "Missing Permissions",
                f"I need permissions to `manage_webhooks` in #{channel.name}.",
            )
    async def webhook_link_send(
        self,
        link: str,
        username: str,
        avatar_url: str,
        *,
        allowed_mentions: discord.AllowedMentions = discord.AllowedMentions(
            users=False, everyone=False, roles=False
        ),
        **kwargs,
    ):
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(
                    link, adapter=discord.AsyncWebhookAdapter(session)
                )
                await webhook.send(
                    username=username,
                    avatar_url=avatar_url,
                    allowed_mentions=allowed_mentions,
                    **kwargs,
                )
                return True
        except (Exception):
            return "Invalid Link"

    async def send_to_channel(
        self,
        channel: discord.TextChannel,
        me: discord.Member,
        author: discord.Member,
        *,
        reason: str = None,
        ctx: commands.Context = None,
        allowed_mentions: discord.AllowedMentions = discord.AllowedMentions(
            users=False, everyone=False, roles=False
        ),
        **kwargs,
    ):
        while True:
            webhook = await self.get_webhook(
                channel=channel, me=me, author=author, reason=reason, ctx=ctx
            )
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(
                    webhook, adapter=discord.AsyncWebhookAdapter(session))
        
                    await webhook.send(allowed_mentions=allowed_mentions, **kwargs)
            except (discord.InvalidArgument, discord.NotFound):
                del self.cache[channel.id]
            else:
                return True

    



def setup(bot):
    bot.add_cog(Webhook(bot))
