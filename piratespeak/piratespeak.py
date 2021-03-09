#This cog is still in an early stage, feel free to suggest/pr more replacements

import discord 
import functools

from redbot.core import commands, Config 
from redbot.core.bot import Red
from typing import Optional

real_send = commands.Context.send

REPLACEMENTS = {
    "you": "ye",
}

@functools.wraps(real_send)
async def send(self, content=None, **kwargs):
    content = str(content) if content is not None else None
    cog = self.bot.get_cog("PirateSpeak")
    if await cog.config.user(self.author).enabled():
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)
    return await real_send(self, content, **kwargs)

class PirateSpeak(commands.Cog):
    """A cog that replaces every message that you invoke with pirate speak"""
    def __init__(self, bot: Red):
        self.bot = bot 
        self.config = Config.get_conf(self, 160805014090190130501014, True)

        default_user = {
            "enabled": False,
        }

        self.config.register_user(**default_user)
    
    def initialize(self) -> None:
        setattr(commands.Context, "send", send)
    
    @commands.group()
    async def piratespeak(self, ctx: commands.Context):
        """Manage options for piratespeak"""
        pass 

    @piratespeak.command()
    async def enabled(self, ctx: commands.Context, state: Optional[bool] = None):
        """Set whether piratespeak is enabled, this also works as a toggle"""
        if state is None:
            previous_state = await self.config.user(ctx.author).enabled()
            state = False if previous_state else True 
        
        await self.config.user(ctx.author).enabled.set(state)
        message = "Enabled piratespeak" if state else "Disabled Pirate Speak"
        await ctx.send(message)