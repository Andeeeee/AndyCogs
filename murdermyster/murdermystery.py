import discord 
import asyncio
from redbot.core import commands, Config 
from typing import Optional, Union
from random import choice

class MurderMystery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(
            self,
            identifier=160805014090190130501014,
            force_registration=True,
        )

        default_guild = {
            "rounds": {},
            "maxplayers": 69, 
            "waittime": 90,
            "roundtime": 20,
            "Session": {"Players": [], "Active": False, "detective": None, "murderer": None, "killed": []},
        }

        default_member = {
            "turn": False,
            "votes": 0,
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member) 
    
    @commands.group(name="murdermystery", aliases=["mm"])
    @commands.guild_only()
    async def murdermystery(self, ctx):
        pass 
    
    @murdermystery.command(name="players", aliases=["maxplayers"])
    @commands.admin()
    async def players(self, ctx, number: Optional[int] = None):
        """Set the player limit, can be any number greater than 1"""
        if not number:
            return await ctx.send("You need to specify a number of players")
        if number <= 0:
            return await ctx.send("Can't have less thatn 1 player")
        await self.config.guild(ctx.guild).maxplayers.set(number)
        await ctx.send(f"The player limit has been set to {number}")

    @murdermystery.command(name="waittime")
    @commands.admin()
    async def waittime(self, ctx, number: Optional[int] = None):
        """Set the wait time for murder mystery"""
        if not number:
            return await ctx.send("You need to specify a number of players")
        if number <= 10:
            return await ctx.send("Can't wait less than 10 seconds")
        await self.config.guild(ctx.guild).waittime.set(number)
        await ctx.send(f"The wait time has been set to {number}")
    
    @murdermystery.command(name="roundtime")
    @commands.admin()
    async def roundtime(self, ctx, number: Optional[int] = None):
        """Set the player time for each round."""
        if not number:
            return await ctx.send("You need to specify a round time")
        if number <= 10:
            return await ctx.send("Can't have a time less than 10 seconds")
        await self.config.guild(ctx.guild).roundtime.set(number)
        await ctx.send(f"The round time has been set to {number}")

    @commands.guild_only()
    @commands.command(name="joinmurder")
    async def joinmurder(self, ctx):
        """Start or join a game of murder mystery, there must be 1 more player than the detective and murderers added up.
        """
        settings = await self.config.guild(ctx.guild).all()
        if await self.game_check(ctx, settings):
            await self.add_player(ctx)

    async def game_check(self, ctx, settings):
        if settings["Session"]["Active"]:
            await ctx.send("You cannot join or start a game of murder mystery while one is active.")
            return False

        if ctx.author.id in settings["Session"]["Players"]:
            await ctx.send("You are already in the waiting room.")
            return False

        if len(settings["Session"]["Players"]) >= (await self.config.guild(ctx.guild).maxplayers()):
            await ctx.send("This game is full. Wait for this game to finish before joining.")
            return False
        else:
            return True

    async def add_player(self, ctx):
        async with self.config.guild(ctx.guild).Session.Players() as players:
            players.append(ctx.author.id)
            num_players = len(players)
        waittime = await self.config.guild(ctx.guild).waittime()
        if num_players == 1:
            await ctx.send(
                "{0.author.mention} is gathering players for a game of murder mystery!"
                "\nType `{0.prefix}joinmurder` to enter. "
                "The round will start in {1} seconds.".format(ctx, waittime)
            )
            await asyncio.sleep(waittime)
            await self.start_game(ctx)
        else:
            await ctx.send("{} was added to the waiting room.".format(ctx.author.mention))
    
    async def reset_game(self, ctx):
        await self.config.guild(ctx.guild).Session.clear()
    
    async def start_game(self, ctx):
        await self.config.guild(ctx.guild).Session.Active.set(True)
        data = await self.config.guild(ctx.guild).Session.all()
        players = [ctx.guild.get_member(player) for player in data["Players"]]
        filtered_players = [player for player in players if isinstance(player, discord.Member)]
        if len(filtered_players) <= 2:
            await self.reset_game(ctx)
            return await ctx.send("You need at least three players to play. One detective, one murderer, and at least one bystander")
        
        detective = choice(players)
        murderer = choice(players)

        while detective == murderer:
            murderer = choice(players)

        session = await self.config.guild(ctx.guild).Session()
        session["detective"] = detective.id
        session["murderer"] = murderer.id
        await self.config.guild(ctx.guild).Session.set(session)
        settings = await self.config.guild(ctx.guild).Session()
        await self.start_round(ctx, settings)

    async def start_round(self, ctx, settings):
        round_time = await self.config.guild(ctx.guild).roundtime()
        for player in settings["Players"]:
            player = ctx.guild.get_member(player)
            if not player:
                continue
            if player.id == settings["detective"]:
                await player.send("You are the detective!")
            elif player.id == settings["murderer"]:
                await player.send("You are the murderer")
            else:
                await player.send("You are a bystander, try to find the murderer with voting.")
        while True:
            responses = {}
            await ctx.send("A round has started! Please run your respective commands in DMs try to win! You have 2 minutes")
            for player in settings["Players"]:
                player = ctx.guild.get_member(player)
                await ctx.send(f"{player}'s turn'")
                if not player:
                    continue
                if player.id in settings["killed"]:
                    continue
                await player.send("What are you going to do for your turn, if you are the murderer, you can type `kill [userid]`, if you are the detective, you can send `detect [userid]`, if you are a bystander, you can send 'vote [userid]`, or you can type skip.")
                turn = await self.config.member(player).turn()
                try:
                    def check(m):
                        return m.author == player and not turn and (m.guild is None)
                    r = await self.bot.wait_for("message", check=check, timeout=round_time)
                    responses[str(player.id)] = r.content
                except asyncio.TimeoutError:
                    await ctx.send(f"Uh oh, {player} took to long to make a move. Let's all blame him")
                    await self.config.guild(ctx.guild).Session.clear()
                    return 

            for user, response in responses.items():
                user = ctx.guild.get_member(int(user))
                if response.startswith("kill"):
                    if user.id != settings["murderer"]:
                        await user.send("You can't do this. You just wasted a turn")
                        continue 
                    response = response.split()
                    if len(response) == 1:
                        await user.send("You need to specify someone to kill smh.")
                        continue 
                    response = response[1]
                    try:
                        killed = ctx.guild.get_member(int(response))
                    except (discord.NotFound, ValueError):
                        await user.send(f"Couldn't find that user, try again")
                        continue
                    if not killed:
                        await user.send("Couldn't find this user")
                    
                    settings["killed"].append(killed.id)
                elif response.startswith("detect"):
                    if user.id != settings["murderer"]:
                        await user.send("You can't do this. You just wasted a turn")
                        continue 
                    response = response.split()
                    if len(response) == 1:
                        await user.send("You need to specify someone to detect smh.")
                        continue 
                    response = response[1]
                    try:
                        killed = ctx.guild.get_member(int(response))
                    except (discord.NotFound, ValueError):
                        await user.send("Couldn't find that user, try again")
                        continue
                    if not killed:
                        await user.send("Couldn't find this user")
                    settings["killed"].append(killed.id)
                
                elif response.startswith("vote"):
                    response = response.split()
                    if len(response) == 1:
                        await user.send("You need to specify someone to vote smh.")
                        continue 
                    response = response[1]
                    try:
                        voteout = ctx.guild.get_member(int(response))
                    except (discord.NotFound, ValueError):
                        await user.send("Couldn't find that user, try again")
                        continue
                    if not voteout:
                        await user.send("Couldn't find this user")
                    
                    votes = await self.config.member(voteout).votes()
                    votes += 1
                    await self.config.member(voteout).votes.set(votes)
            
            await self.config.guild(ctx.guild).Session.set(settings)

            settings = await self.config.guild(ctx.guild).Session()
            detective = settings["detective"]
            murderer = settings["murderer"]
            killed = settings["killed"]
            players = settings["Players"]

            if detective in killed:
                await ctx.send("The detective has been killed! A unanimous vote must be done to vote the murderer out.")
            if murderer in killed:
                await ctx.send("The murderer has been found!")
                await ctx.send(f"The detective was: <@{detective}\nThe murderer was <@{murderer}>")
                await self.config.guild(ctx.guild).Session.clear()
                for user in players:
                    user = ctx.guild.get_member(user)
                    await self.config.member(user).votes.clear()

            for user in players:
                user = ctx.guild.get_member(user)
                votes = await self.config.member(user).votes()
                await self.config.member(user).votes.clear()
                if votes < len(players) - len(killed):
                    continue   
                else:
                    await ctx.send(f"{user.mention} has been voted out. This is sad. Wait till next round to see the results.")
                    settings["killed"].append(user.id)
                    await self.config.member(user).votes.clear()
                    
            if len(players) - len(killed) <= 2:
                await ctx.send("The game is over. There are less than 2 people left.")
                await ctx.send(f"The detective was <@{detective}> and the murderer was <@{murderer}>")
                await self.reset_game(ctx)
                return 
            
            await self.config.guild(ctx.guild).Session.set(settings)