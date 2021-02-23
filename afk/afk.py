import discord
from redbot.core import commands
from redbot.core import Config
from datetime import datetime
from typing import Optional 
from redbot.core.utils.chat_formatting import pagify
import re

class Afk(commands.Cog):
    """A cog for being afk and responding when idiots ping you"""
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True)

        default_member = {
            "afk": None, #None becuase its gonna be replaced with a timestamp
            "sticky": False, #sets if afk goes away when they type or if they manually toggle it.
            "message": "{author} has been afk since {time}, please be paitent and wait till he comes online."
        }

        self.config.register_member(**default_member)
    
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
    
    @commands.group(name="afk")
    @commands.guild_only()
    async def afk(self, ctx):
        """A group for settings custom responses when being pinged."""
        pass #just realized the bot sends help automatically if there isn't a subcmd invoked.

    @afk.command(name="on")
    async def afk_on(self, ctx, * , message="{author} has been afk since {time}, please be paitent and wait till he comes online."):
        """Responds when people ping you. Set {time} for the time you've been afk and {author} for your mention. (You won't actually be pinged)."""

        afk = await self.config.member(ctx.author).afk()
        
        if afk is not None:
            return await ctx.send("You are already AFK")

        date = datetime.utcnow().timestamp()
        await self.config.member(ctx.author).afk.set(date)
        await self.config.member(ctx.author).message.set(message)
        
        await ctx.send("I have set you as afk. People who ping you will now receive a message")

        if ctx.channel.permissions_for(ctx.me).manage_nicknames:
            try:
                await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
            except discord.errors.Forbidden:
                pass #hericahy
    
    @afk.command(name="off")
    async def afk_off(self, ctx):
        """Turn off afk mode."""
        await self.config.member(ctx.author).afk.clear()
        await ctx.send("I removed your afk status.")

        if ctx.channel.permissions_for(ctx.me).manage_nicknames:
            name = ctx.author.display_name
            name = name.replace("[AFK]", "")
            if len(name) < 2:
                return
            elif len(name) > 32:
                return 
            try:
                await ctx.author.edit(nick=name)
            except discord.errors.Forbidden:
                pass #hiercahy
    
    @afk.command(name="sticky")
    async def sticky(self, ctx, sticky: Optional[bool] = None):
        """Sets whether afk should go away when you send a message in the corresponding server."""
        if not sticky:
            await self.config.member(ctx.author).sticky.set(False)
            await ctx.send("I will now remove your afk status on messages.")
        else:
            await self.config.member(ctx.author).sticky.set(True)
            await ctx.send(f"I will no longer remove your afk status on message. You will have to manually run {ctx.prefix}afk off to turn this off.")
    
    
    @commands.Cog.listener("on_message_without_command")
    async def on_message_without_command(self, message):
        if not message.guild:
            return 
        
        guild = message.guild

        if message.author.bot:
            return 
        
        afk = await self.config.member(message.author).afk()
        sticky = await self.config.member(message.author).sticky()

        if sticky:
            pass 
        elif not afk:
            pass
        elif "afk on" in message.content:
            pass 
        else:
            await message.channel.send(f"Welcome back {message.author.mention}, I've removed your afk.")
            await self.config.member(message.author).afk.clear()
            try:
                await message.author.edit(nick=message.author.nick.replace("[AFK]", ""))
            except discord.errors.Forbidden:
                pass
        
        final_message = []
        
        mentions = message.mentions
        
        if not mentions:
            return 


        for m in mentions:
            if m == message.author:
                continue 
                
            afk = await self.config.member(m).afk()
            msg = await self.config.member(m).message()

            if not afk:
                continue 
                    
            afk = datetime.utcnow() - datetime.fromtimestamp(afk)
            afk = self.display_time(round(afk.total_seconds()))

            final_message.append(msg.replace("{author}", m.mention).replace("{time}", str(afk)))

        
        if len(final_message) == 0:
            return
        
        final_message = "\n".join(final_message)
        final_message = list(pagify(final_message)) 

        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=False)

        for msg in final_message:
            await message.channel.send(msg, allowed_mentions=allowed_mentions)
            
