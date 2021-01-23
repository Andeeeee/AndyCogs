import asyncio
import discord 
from datetime import datetime
from redbot.core import commands 
from redbot.core import Config
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from typing import Optional, Union

class Highlight(commands.Cog):
    """A nice cog for receiving DMs when someone says a highlighted word"""
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True)

        default_member = {
            "highlights": [],
            "afk_time": 600, 
            "ignored": [],
            "last_message": None,
        }

        self.config.register_member(**default_member)
    
    async def generate_messages(self, m, hl):
        l = []
        async for msg in m.channel.history(limit=5):
            time = msg.created_at.strftime("%H:%M:%S")
            l.append(f"**[{time}] {msg.author.name}:** {msg.content[:200]}")
        e = discord.Embed(title=f"**{hl}**", description='\n'.join(l[::-1]), color=discord.Color.green())
        e.add_field(name="Source", value=f"[Click here]({m.jump_url})")
        return e
    
    @commands.group(name="highlight", aliases=["hl", "highlights"])
    @commands.guild_only()
    async def highlight(self, ctx):
        """Manage settings for highlights"""
        pass 

    @highlight.command(name="add")
    async def hl_add(self, ctx, phrase: str):
        """Add a word to highlight"""
        phrase = phrase.split()
        phrase = phrase[0] #Only allowing single word highlights.
        hl = await self.config.member(ctx.author).highlights()
        if phrase.lower() in hl:
            return await ctx.send(f"You are already highlighting the word `{phrase.lower()}`")
        else:
            hl.append(phrase.lower())
            await self.config.member(ctx.author).highlights.set(hl)
            await ctx.send(f"Now highlighting the phrase `{phrase.lower()}`.")
    
    @highlight.command(name="remove")
    async def hl_remove(self, ctx, phrase: str):
        """Remove a word to highlight"""
        phrase = phrase.split()
        phrase = phrase[0]
        hl = await self.config.member(ctx.author).highlights()
        if phrase.lower() not in hl:
            return await ctx.send("This phrase is not highlighted")
        else:
            hl.remove(phrase.lower())
            await self.config.member(ctx.author).highlights.set(hl)
            return await ctx.send("I will no longer highlight this word")

    @highlight.command(name="show", aliases=["list"])
    async def hl_show(self, ctx):
        """Show your highlighted words"""
        hl = await self.config.member(ctx.author).highlights()
        if len(hl) == 0:
            return await ctx.send("You have no highlights")

        hls = []
        
        for index, highlight in enumerate(hl, start=1):
            hls.append(f"{index}. {highlight}")
        
        highlights = "\n".join(hls)
        ignore = await self.config.member(ctx.author).ignored()
        ignored = []
        for i in ignore:
            ignored.append(f"<#{i}>")
        ignore = "\n".join(ignored)
        if len(ignore) == 0:
            ignore = "None"

        pages = []
        highlights = list(pagify(highlights))

        for number, page in enumerate(highlights, start=1):
            e = discord.Embed(title="Highlighted words", description=page, color=discord.Color.green())
            e.set_footer(text=f"{number} out of {len(highlights)} pages.")
            e.add_field(name="Ignored channels", value=ignore)
            pages.append(e)
        await menu(ctx, pages, DEFAULT_CONTROLS)
    
    @highlight.command(name="clear")
    async def clear(self, ctx):
        """Clear your highlights"""
        await ctx.send("You are about to clear your entire highlight list. Are you sure?")
        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content in ["yes", "no"] 
            message = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Looks like we won't be clearing your highlights today.")
        
        if message.content == "yes":
            await self.config.member(ctx.author).highlights.clear()
            await ctx.send("Cleared your highlights.")
        else:
            return await ctx.send("Looks like we won't be clearing your highlights today.")
    
    @highlight.command(name="ignore")
    async def hl_ignore(self, ctx, chan: Optional[discord.TextChannel] = None):
        """Ignore highlights from a channel"""
        if not chan:
            return await ctx.send("You need to specify a channel to block.")
        else:
            ignored = await self.config.member(ctx.author).ignored()
            if chan.id in ignored:
                return await ctx.send("This channel is already ignored.")
            else:
                ignored.append(chan.id)
                await self.config.member(ctx.author).ignored.set(ignored)
                await ctx.send("I will no longer highlight messages in this channel")
    
    @highlight.command(name="unignore")
    async def hl_unignore(self, ctx, chan: Optional[discord.TextChannel] = None):
        """Unignore highlights from a channel"""
        if not chan:
            return await ctx.send("You need to specify a channel to unblock.")
        else:
            ignored = await self.config.member(ctx.author).ignored()
            if chan.id not in ignored:
                return await ctx.send("This channel is not ignored.")
            else:
                ignored.remove(chan.id)
                await ctx.send("I will now highlight messages in this channel")
    
    @highlight.command(name="afk", aliases=["afktime"])
    async def afktime(self, ctx, time: Optional[int] = None):
        """The time you have to be afk in the server for a highlight to trigger. """
        if time is None:
            return await ctx.send("You need to specify a digit.")
        else:
            await self.config.member(ctx.author).afk_time.set(time * 60)
            await ctx.send(f"I will only highlight messages if you have been afk for longer than {time} minutes.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        await self.config.member(message.author).last_message.set(datetime.utcnow().timestamp())
        data = await self.config.all_members()
        data = data[message.guild.id]
        for memberid, highlights in data.items():
            if len(highlights["highlights"]) == 0:
                continue 
            user = message.guild.get_member(int(memberid))
            ignored = await self.config.member(user).ignored()
            if message.channel.id in ignored:
                continue
            last_seen = await self.config.member(user).last_message() or 1
            last_seen = datetime.fromtimestamp(last_seen)
            afk_time = await self.config.member(user).afk_time()
            if (datetime.utcnow() - last_seen).total_seconds() < afk_time:
                continue
            if message.author.id == user.id:
                continue
            if not message.channel.permissions_for(user).read_messages:
                continue

            for hl in highlights["highlights"]:
                if hl in message.content.lower():
                    e = await self.generate_messages(message, hl)
                    try:
                        await user.send(f"In {message.guild.name}, the highlighted word {hl} was triggered.", embed=e)
                    except discord.errors.Forbidden:
                        pass 