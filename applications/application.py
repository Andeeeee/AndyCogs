import discord 
from redbot.core import commands 
from redbot.core import Config 
from typing import Optional
import asyncio

class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True)

        default_guild = {
            "questions" : [],
            "channel": None,
            "resultchannel": None,
            "acceptrole": None,
            "dm": True
        }

        default_member = {
            "answers": [],
            "current_questions": [],
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
    
    def convert_role(self, guild, role):
        guild = self.bot.get_guild(int(guild))
        
        role = guild.get_role(int(role))

        if not role:
            pass 
        else:
            return role
        
        role = discord.utils.get(guild.roles, name=role)
        if not role:
            pass 
        else:
            return role 
        
        role = discord.utils.get(guild.roles, name=role[3:-1])
        if not role:
            pass 
        else:
            return role 
        
        return None
    

    
    @commands.group(name="appset", aliases=["application", "applicationset"])
    @commands.guild_only()
    async def appset(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send_help("appset")
            
    @appset.command(name="channel", aliases=["submissionchannel"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def appset_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        if not channel:
            await self.config.guild(ctx.guild).channel.set(None)
            await ctx.send("Applications have been closed.")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(f"I will now send applications to <#{channel.id}>")
    
    @appset.command(name="resultchannel")
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def resultchannel(self, ctx, channel: Optional[discord.TextChannel] = None):
        if not channel:
            await self.config.guild(ctx.guild).resultchannel.set(None)
            await ctx.send("I will no longer post results.")
        else:
            await self.config.guild(ctx.guild).set(channel.id)
            await ctx.send(f"I will now post application results to <#{channel.id}>")

    @appset.command(name="dm", aliases=["pm", "directmessage", "privatemessage"])
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def appset_dm(self, ctx, dm: Optional[bool] = None):
        if dm is None:
            await ctx.send("You need to specify either True or False.")
        else:
            await self.config.guild(ctx.guild).dm.set(dm)

            if dm:
                await ctx.send("I will now send users the results of their application.")
            else:
                await ctx.send("I will no longer send users the results of their application.")
                
    @appset.command(name="acceptrole", aliases=["role"])
    @commands.guild_only()
    async def acceptrole(self, ctx, role: Optional[discord.Role] = None):
        if ctx.author.id != ctx.guild.owner.id:
            return 
        if role is None:
            await self.config.guild(ctx.guild).acceptrole.set(None)
            await ctx.send("No users can accept members for roles")
        else:
            await self.config.guild(ctx.guild).acceptrole.set(role.id)
            await ctx.send(f"Members with the role **{role.name}** can now accept members.")
    
    @appset.command(name="reset")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def appset_reset(self, ctx):
        try:
            await ctx.send("Are you sure? Type `YES I WANT TO RESET` in the chat in the next 30 seconds (Caps Count)")
            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        
        except asyncio.TimeoutError:
            await ctx.send("Looks like we won't reset your servers data today :/")
            return

        if not msg.content == "YES I WANT TO RESET":
            await ctx.send("Looks like we won't reset your servers data today :/")
        else:
            await self.config.clear_all()
            await ctx.send("I've cleared your guilds channels, resultchannels, DM settings, acceptroles, and currently logged member applications.")

    @commands.command(name="apply")
    @commands.guild_only()
    async def apply(self, ctx):
        channel = await self.config.guild(ctx.guild).channel()
        if not channel:
            await ctx.send("Uh oh, looks like the application channel for this server isn't set. Please ask an admin or above to set one.")
            return 
        questions = await self.config.guild(ctx.guild).questions()

        if len(questions) == 0:
            questions = [
                "What name do you prefer to go by?",
                "What age are you?",
                "What time zone are you in?",
                "Which position/role are you applying for?",
                "Do you have any previous experience with this position or role? If so, please describe.",
                "What bots are you most familiar and experienced with?",
                "What makes you special? Why should we pick you for this role",
                "Which hours can you be active daily?",
                "How many days of the week can you be online?",
                "Any final comments or things that we should be aware of?",
            ]
        await ctx.send("Started the application process in DM's")
        await ctx.author.send("You've started the application process. You have a total of 3 minutes PER QUESTION.")

        answers = []

        for question in questions:
            await ctx.author.send(question)
            try:
                def check(message):
                    return message.author == ctx.author and message.guild is None
                msg = await self.bot.wait_for("message", check=check, timeout=180)
                answers.append(msg.content)
            except asyncio.TimeoutError:
                await ctx.send("Uh oh, you've exceeded the time limit of 3 minutes per question.")
                return 
        try:
            channel = self.bot.get_channel(channel)
            if not ctx.channel.permissions_for(ctx.me).send_messages:
                await ctx.send("Uh oh, I couldn't send messages in the application channel.")
                return 
            
            e = discord.Embed(title="New Application", color=discord.Color.green(),
            description=f"User ID: {ctx.author.id}\nUser Name and Tag: {ctx.author}")

            for i in range(len(questions)):
                e.add_field(name=questions[i], value=answers[i])
            await self.config.member(ctx.author).answers.set(answers)
            await self.config.member(ctx.author).current_questions.set(questions)
            await channel.send(embed=e)
            await ctx.author.send(f"Your application has been successfully sent to **{ctx.guild.name}**")
        except(Exception) as e:
            await ctx.author.send(f"Uh oh, something borked. The error was \n {e}")

    @commands.command(name="accept")
    @commands.guild_only()
    async def accept(self, ctx, member: Optional[discord.Member] = None):
        role = await self.config.guild(ctx.guild).acceptrole()
        role = ctx.guild.get_role(role)

        if role not in ctx.author.roles:
            return
        if not member:
            await ctx.send("Uh oh, please specify a member to accept")
            return
        
        member = ctx.guild.get_member(member.id)
        member_data = await self.config.member(member).answers()

        if len(member_data) == 0:
            await ctx.send("This member hasn't applied for anything yet.")
            return 
            
        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            await ctx.send("Specify the role you would like to accept them here.")
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            
        except asyncio.TimeoutError:
            await ctx.send("You've exceeded the 1 minute time limit.")
        
        role = self.convert_role(ctx.guild.id, msg.content)
        
        if role is None:
            await ctx.send("Uh oh, I couldn't find this role, try again?")
            return 
        
        try:
            def check1(m):
                return m.author == ctx.author and m.channel == ctx.channel
            await ctx.send("Please specify the reason here.")
            msg1 = await self.bot.wait_for("message", check=check1, timeout=60)

        except asyncio.TimeoutError:
            await ctx.send("Uh oh, you've exceeded the 1 minute time limit.")

        my_pos = ctx.me.top_role
        my_pos = my_pos.id 

        author_pos = ctx.author.top_role 
        author_pos = author_pos.id

        if role.position >= my_pos:
            await ctx.send("Uh oh, I cannot assign roles higher than or equal to my position.")
            return 
        elif role.position >= author_pos:
            await ctx.send("You can't assign roles that are higher than you. :rage:")
            return 
        
        channel = await self.config.guild(ctx.guild).resultchannel()
        if not channel:
            pass 
        else:
            await channel.send(f"{member.name} was accepted as {role.name} by {ctx.author.name} with the reason {msg1.content}.")
