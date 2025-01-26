import asyncio
import discord
import random

from redbot.core import commands
from redbot.core.bot import Red
from typing import Optional


class TicTacToe(commands.Cog):
    """Tic Tac Toe"""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.guild_only()
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.command(aliases=["tictactoe"])
    async def ttt(self, ctx, user: discord.Member):
        """ Tic Tac Toe """
        if user == ctx.author:
            return await ctx.send("Can't play yourself")

        winner = await self.start_game(ctx.author, user, ctx.channel)
        if not winner:
            return 
        await ctx.send(f"{winner.name} won the game!")

    async def start_game(
        self, player: discord.Member, opp: discord.Member, channel: discord.TextChannel
    ) -> discord.Member:
        board = [None, None, None, None, None, None, None, None, None]

        keys = {
            "a1": 0,
            "a2": 1,
            "a3": 2,
            "b1": 3,
            "b2": 4,
            "b3": 5,
            "c1": 6,
            "c2": 7,
            "c3": 8,
            "end": None,
        }

        letters = {"O": random.choice([player, opp])}
        letters["X"] = player if letters["O"] == opp else opp

        node = "X"

        def check_winner():
            check = False
            if (board[6] == "X" and board[7] == "X" and board[8] == "X") or (
                board[6] == "O" and board[7] == "O" and board[8] == "O"
            ):
                check = True
            elif (board[6] == "X" and board[3] == "X" and board[0] == "X") or (
                board[6] == "O" and board[3] == "O" and board[0] == "O"
            ):
                check = True
            elif (board[6] == "X" and board[4] == "X" and board[2] == "X") or (
                board[6] == "O" and board[4] == "O" and board[2] == "O"
            ):
                check = True
            elif (board[3] == "X" and board[4] == "X" and board[5] == "X") or (
                board[3] == "O" and board[4] == "O" and board[5] == "O"
            ):
                check = True
            elif (board[0] == "X" and board[1] == "X" and board[2] == "X") or (
                board[0] == "O" and board[1] == "O" and board[2] == "O"
            ):
                check = True
            elif (board[0] == "X" and board[4] == "X" and board[8] == "X") or (
                board[0] == "O" and board[4] == "O" and board[8] == "O"
            ):
                check = True
            elif (board[8] == "X" and board[5] == "X" and board[2] == "X") or (
                board[8] == "O" and board[5] == "O" and board[2] == "O"
            ):
                check = True
            elif (board[1] == "X" and board[4] == "X" and board[7] == "X") or (
                board[1] == "O" and board[4] == "O" and board[7] == "O"
            ):
                check = True
            return check

        async def display_board():
            row1 = board[:3]
            row2 = board[3:6]
            row3 = board[6:9]

            result = ""

            for place in row1:
                place = str(place)
                result += (
                    place.replace("X", ":x:")
                    .replace("O", ":o:")
                    .replace("None", ":black_large_square:")
                )
            result += "\n"

            for place in row2:
                place = str(place)
                result += (
                    place.replace("X", ":x:")
                    .replace("O", ":o:")
                    .replace("None", ":black_large_square:")
                )
            result += "\n"

            for place in row3:
                place = str(place)
                result += (
                    place.replace("X", ":x:")
                    .replace("O", ":o:")
                    .replace("None", ":black_large_square:")
                )
            result += "\n"

            e = discord.Embed(
                title="Tic Tac Toe", color=discord.Color.green(), description=result
            )
            await channel.send(embed=e)

        for i in range(9):
            await channel.send(
                f"{letters[node].mention}: Please pick a move. Your choices are in the following format\na1 a2 a3\nb1 b2 b3\nc1 c2 c3"
            )
            def player_check(m: discord.Message):
                return m.author == letters[node] and m.content.lower() in keys.keys()
            try:
                choice = await self.bot.wait_for(
                    "message", check=player_check, timeout=60
                )
            except asyncio.TimeoutError:
                await channel.send("The game has ended due to invalid choices.")
                return player if letters[node] == opp else opp
            
            if choice.content.lower() == "end":
                return player if letters[node] == opp else opp

            if board[keys[choice.content.lower()]] is not None:
                await channel.send("This spot has been taken")
                continue

            board[keys[choice.content.lower()]] = node

            if check_winner():
                return letters[node]
            node = "X" if node == "O" else "O"
            await display_board()

        await channel.send("The game has tied")
