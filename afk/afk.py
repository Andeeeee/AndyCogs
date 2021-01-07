import discord
from redbot.core import commands
from redbot.core import Config
from datetime import datetime
from typing import Optional 
from redbot.core.utils.chat_formatting import pagify
import re

mention_re = re.compile(r'(<@(|!|)\d*>)')

class Afk(commands.Cog):
    """A cog for being afk and responding when idiots ping you"""
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True)

        default_member = {
            "afk": None, #None becuase its gonna be replaced with a timestamp
            "sticky": True, #sets if afk goes away when they type or if they manually toggle it.
            "message": "{author} has been afk since {time}, please be paitent and wait till he comes online."
        }

        self.config.register_member(**default_member)
    
    @commands.group(name="afk")
    async def afk(self, ctx):
        pass #just realized the bot sends help automatically if there isn't a subcmd invoked.

    @afk.command(name="on")
    async def afk_on(self, ctx, * , message="{author} has been afk since {time}, please be paitent and wait till he comes online."):
        """Responds when people ping you"""

        date = datetime.utcnow().timestamp()
        await self.config.member(ctx.author).afk.set(date)
        await self.config.member(ctx.author).message.set(message)
        
        await ctx.send("I have set you as afk. People who ping you will now receive a message")

        if ctx.channel.permissions_for(ctx.me).manage_nicknames:
            await ctx.author.edit(nick=f"[afk] {member.display_name}"
    
    @afk.command(name="off")
    async def afk_off(self, ctx):
        """Turn off afk mode"""
        await self.config.member(ctx.author).afk.clear()
        await ctx.send("I removed your afk status.")
    
    @afk.command(name="sticky")
    async def sticky(self, ctx, sticky: Optional[bool] = None):
        """Sets whether afk should go away when you send a message in the corresponding server."""
        if not sticky:
            await self.config.member(ctx.author).sticky.set(False)
            await ctx.send("I will now remove your afk status on messages.")
        else:
            await self.config.member(ctx.author).sticky.set(True)
            await ctx.send(f"I will no longer remove your afk status on message. You will have to manually run {ctx.prefix}afk off to turn this off.")
    
    
    @commands.Cog.listener("on_message")
    async def on_message(self, message):
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
        else:
            await message.channel.send(f"Welcome back {message.author.mention}, I've removed your afk.")
        
        final_message = []
        
        mentions = re.findall(mention_re, message.content)
        
        if not mentions:
            return 

        if len(mentions) == 0:
            return 

        for mention in mentions[0]:
            userid = int(mention.lstrip("<@!").lstrip("<@").rstrip(">"))
            user = guild.get_member(userid)
            if not user:
                continue 
            
            afk = await self.config.member(user).afk()
            msg = await self.config.member(user).message()

            if not afk:
                continue 
                
            afk = datetime.utcnow().timestamp() - afk

            final_message.append(msg.replace("{author}", message.author.mention).replace("{time}", str(afk)))
        
        if len(final_message) == 0:
            return 
        final_message = "\n".join(final_message)
        final_message = list(pagify(final_message)) 

        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=False)

        for message in final_message:
            await message.channel.send(message, allowed_mentions=allowed_mentions)
            
