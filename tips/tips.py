import discord 
from redbot.core import commands
from redbot.core import Config
from random import choice, randrange


#Docs are really nice, copypaste the instructions and edit them to your fitting. 

#Idea taken from the bot Dank Memer. Not sure if they have a github and can't find it so https://dankmemer.lol

class Tips(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, identifier=160805014090190130501014,
        force_registration=True)

        default_global = {
            "tiplist": {}
        }

        default_user = {
            "tips": True
        }

        self.config.register_user(**default_user)
        self.config.register_global(**default_global)

    @commands.group(name="tips")
    async def tips(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help("tips")

    @tips.command(name="on")
    async def on(self, ctx):
        await self.config.user(ctx.author).tips.set(True)
        await ctx.send("I will now send tips randomly")
    
    @tips.command(name="off")
    async def off(self, ctx):
        await self.config.user(ctx.author).tips.set(False)
        await ctx.send("I will no longer send tips.")

    @commands.Cog.listener('on_command')
    async def on_command(self, ctx):
        send_tips = randrange(10, 100)
        tips = await self.config.user(ctx.author).tips()

        if not tips:
            return
    
        tiplist = await self.config.tiplist()

        tipchoice = choice(list(tiplist.values()))

        if send_tips < 10:
            await ctx.send(f"{tipchoice} \n You can disable these with `{ctx.prefix}tips off` anytime!")
    
    @commands.is_owner()
    @commands.command(name="addtip")
    async def addtip(self, ctx, * , tip: str):
        tiplist = await self.config.tiplist()
        number = str(len(tiplist))

        tiplist[number] = tip

        await self.config.tiplist.set(tiplist)

        await ctx.send(f"Added tip #{number} with the content `{tip}`")

    @commands.is_owner()
    @commands.command(name="removetips")
    async def removetips(self, ctx, * , tip: str):
        tips = await self.config.tiplist()
        tips.pop(tip)
        await self.config.tiplist.set(tips)
        await ctx.send(f"Removed tip #{tip}")

    @commands.is_owner()
    @commands.command(name="viewtips")
    async def viewtips(self, ctx):
        tips = await self.config.tiplist()

        e = discord.Embed(title="All Tips", color=discord.Color.green())

        for number, tip in tips.items():
            e.add_field(name=number, value=tip, inline=False)
        await ctx.send(embed=e)
