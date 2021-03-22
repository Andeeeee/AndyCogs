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

import asyncio
import argparse
import discord
import redbot

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.commands import BucketType
from typing import Optional, Union
from .words import random_word

class ParserButBetter(argparse.ArgumentParser):
    def error(self, message):
        raise commands.BadArgument(message)

class Tea(commands.Cog):
    """Fun guessing word games"""

    def __init__(self, bot: Red):
        self.bot = bot

        self.config = Config.get_conf(
            self, identifier=160805014090190130501014, force_registration=True
        )

        self._sessions = {}
    
    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.bot_has_permissions(add_reactions=True)
    async def blacktea(self, ctx: commands.Context, lives: Optional[int] = 1, *flags):
        """Start a game of blacktea. Specify an integer after this for lives, and use the `--timeout` flag to set the timeout"""
        if lives <= 0:
            return await ctx.send("Sorry, you need to have at least 1 life to start with")
        
        parser = ParserButBetter()
        parser.add_argument("--timeout", nargs="*", default=10)
        try:
            args = vars(parser.parse_args(flags))
        except commands.BadArgument:
            timeout = 10 
        else:
            try:
                timeout = args["timeout"]
            except KeyError:
                timeout = 10

        sessions = self._sessions

        message = await ctx.send("React with :tea: to enter!")
        data = {}
        data["waiting"] = True 
        data["players"] = []
        data["message"] = message 
        sessions[ctx.channel.id] = data
        self._sessions = sessions
        await message.add_reaction(":tea:")
        await asyncio.sleep(60)
        sessions = self._sessions
        sessions[ctx.channel.id]["waiting"] = False 
        self._sessions = sessions

        await self.start_blacktea(ctx, lives, timeout)
    
    async def start_blacktea(self, ctx: commands.Context, lives: int, timeout: int):
        data = self._sessions[ctx.channel.id]
        player_objects = [ctx.guild.get_member(player_id) for player_id in data["players"]]
        players = list(filter(None, player_objects))
        to_remove = []

        player_lives = {p: 0 for p in data["players"]}

        if len(players) <= 1:
            return await ctx.send("Not enough people were gathered to join the game. Try again next time")
        
        while True:
            if not to_remove:
                pass 
            else:
                for user_id in to_remove:
                    del data["players"][user_id]
            player_objects = [ctx.guild.get_member(player_id) for player_id in data["players"]]
            players = list(filter(None, player_objects))
            to_remove = []
            word = random_word()
            segment = word[:len(word)/2]
            for player in players:
                def player_check(m: discord.Message):
                    return m.author == player and m.channel == ctx.channel

                await ctx.send(f"{player.mention}: Please enter a word containing {segment}")
                try:
                    resp = await self.bot.wait_for("message", check=player_check, timeout=timeout)
                except asyncio.TimeoutError:
                    player_lives[player.id] -= 1
                    message = ""
                    if player_lives[player.id] <= 0:
                        to_remove.append(player.id)
                        message = "You ran out of lives, so you have been eliminated from the game"
                    await ctx.send(f"You ran out of time!{message}")
                    valid_players = [user for user in players if player_lives[player.id] > 0]
                    if len(valid_players) == 1:
                        winner = valid_players[0]
                        await ctx.send(f"{winner.mention} won the game!")
                    continue 
                else:
                    if segment not in resp.content.lower():
                        player_lives[player.id] -= 1
                        message = ""
                        if player_lives[player.id] <= 0:
                            to_remove.append(player.id)
                            message = "You ran out of lives, so you have been eliminated from the game"
                        await ctx.send(f"Wrong answer!{message}")
                        valid_players = [user for user in players if player_lives[player.id] > 0]
                        if len(valid_players) == 1:
                            winner = valid_players[0]
                            await ctx.send(f"{winner.mention} won the game!")
                        continue 
                    else:
                        await ctx.send("Thats correct!")
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]):
        if isinstance(user, discord.User) or user.bot:
            return 
        if reaction.emoji != "🍵":
            return 

        sessions = self._sessions

        message: discord.Message = reaction.message 

        if message.channel.id not in sessions or sessions["waiting"] == False:
            return 
        
        if user.id in sessions["players"]:
            return 
        sessions["players"].append(user.id)
        self._sessions = sessions

        
    

