import discord 
from redbot.core import commands
from typing import Optional 
from redbot.core import Config

#the check_emoji and convert_emoji functions are fucked becuase I don't like regex personally. Laugh if you want.

class NotQuiteNitro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=160805014090190130501014,
        force_registration=True) #I have no idea what the fuck force_registration but a lot of cogs have it so I'll put it here.
    
        default_guild = {
            "delete": False,
            "auto": False
        }
        self.config.register_guild(**default_guild)

    def check_emoji(self, oldemoji: str):
        if not oldemoji.startswith(":") or not oldemoji.endswith(":"):
            return False 
        return True        

    async def convert_emojis(self, oldemoji: str):
        #idk how async functions work. It seems to work fine so lets keep it this way
        emoji = discord.utils.get(self.bot.emojis, name=oldemoji.strip(":"))
        if not emoji:
            return oldemoji
        return str(emoji)

        

    @commands.group(name="nqnset", aliases=["notquitenitroset"])
    async def nqnset(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send_help("nqnset")
    
    @nqnset.command(name="auto")
    @commands.admin_or_permissions(manage_guild=True)
    async def nqnset_auto(self, ctx, auto: Optional[bool] = None):
        if auto is None:
            await ctx.send("Please specify true or false after this!")
            return 

        await self.config.guild(ctx.guild).auto.set(auto)
        
        if auto:
            await ctx.send("I will now automatically try to convert failed emojis into emojis.")
        else:
            await ctx.send("I will no longer automatically try to convert failed emojis into emojis")

    @nqnset.command(name="delete")
    @commands.admin_or_permissions(mangage_guild=True)
    async def nqnset_delete(self, ctx, delete: Optional[bool] = None):
        if delete is None:
            await ctx.send("Please specify true or false after this!")
            return

        await self.config.guild(ctx.guild).delete.set(delete)

        if delete:
            await ctx.send("I will now delete messages when converting emojis")
        else:
            await ctx.send("I will no longer delete messages when converting emojis.")

    @commands.command(name="nqn", aliases=["notquitenitro"])
    async def nqn(self, ctx, * , message: str):
        messages = message.split()
        x = ""
        
        for message in messages:
            if not self.check_emoji(message):
                x += f" {message}"
            else:
                emoji = await self.convert_emojis(message)
                x += f" {emoji}"
            
        cog = self.bot.get_cog("Webhook")
        #webhook send_to_channel logic taken from https://github.com/phenom4n4n/phen-cogs. Thank you.
        try:
            await cog.send_to_channel(
                channel=ctx.channel,
                me=ctx.me,
                author=ctx.author,
                reason="For the NotQuiteNitro command",
                ctx=ctx,
                content=x,
                avatar_url=ctx.author.avatar_url,
                username=ctx.author.display_name
            )
        except(Exception) as e:
            await ctx.send(x)
        await ctx.message.delete()

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        #I don't use regex so its not good when you have two emojis together without spaces.

        auto = await self.config.guild(message.guild).auto()
        delete = await self.config.guild(message.guild).delete()

        if not auto:
            return

        messages = message.content.split()
        counter = 0
        
        x = ""

        for msg in messages:
            if not self.check_emoji(msg):
                x += f" {msg}"
            else:
                emoji = await self.convert_emojis(msg)

                if emoji == msg:
                    x += f" {emoji}"
                else:
                    x += f" {emoji}"
                    counter += 1
                
        if counter == 0:
            return 
            
        try:
            cog = self.bot.get_cog("Webhook")
            await cog.send_to_channel(
                channel=message.channel,
                me=message.guild.me,
                author=message.author,
                reason="Automatic NQN converter",
                content=x,
                avatar_url=message.author.avatar_url,
                username=message.author.display_name
            )

        except(Exception) as e:
            #Sending a message through the bot
            await message.channel.send(x)

        if delete:
            if message.channel.permissions_for(message.guild.me).manage_messages:
                await message.delete() 
            else:
                pass