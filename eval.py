import ast
import discord
import asyncio
from discord.ext import commands

botowners = ['721922636745146418', '623684866369781760']

#For some reason the cmd works but errors Cannot Send Empty Message so if you know feel free to tell me why.


class Eval(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
      """ Owner only commands globally. Some are broken kek """
      return str(ctx.author.id) in botowners #Not @commands.is_owner() becuase I use alts to test sometimes


    @commands.command(name="eval")
    async def eval(self, ctx, *, cmd): 
        name = "eval_expression"

        command = cmd.strip("` ")

        command = "\n".join(f"    {i}" for i in cmd.splitlines())

        body = f"async def {name}():\n{command}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__
        }

        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = (await eval(f"{name}()", env))
        await ctx.send(result)
 