import asyncio
import discord 
from redbot.core import commands 
from redbot.core.commands import BucketType
from redbot.core import Config 
from typing import Optional

async def is_guild_owner(ctx):
    return ctx.author.id == ctx.guild.owner.id

class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True)

        default_guild = {
            "questions": {},
            "channel": None,
            "resultchannel": None,
            "acceptrole": None,
            "dm": True,
            "positions": [],
        }

        default_member = {
            "answers": [],
            "current_questions": [],
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
    
    def convert_role(self, guild, role):
        guild = self.bot.get_guild(int(guild))

        if role.startswith("<@&") and role.endswith(">"):
            role = role[3:-1]
            
        newrole = discord.utils.get(guild.roles, name=role)

        if newrole is None:
            pass
        else:
            return newrole 

        newrole = guild.get_role(int(role))

        if not newrole:
            pass 
        else:
            return newrole

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
        """The channel where applications show up"""
        if not channel:
            await self.config.guild(ctx.guild).channel.set(None)
            await ctx.send("Applications have been closed.")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(f"I will now send applications to <#{channel.id}>")
    
    @appset.command(name="resultchannel", aliases=["decisionchannel"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def resultchannel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """The channel where application results go"""
        if not channel:
            await self.config.guild(ctx.guild).resultchannel.set(None)
            await ctx.send("I will no longer post results.")
        else:
            await self.config.guild(ctx.guild).resultchannel.set(channel.id)
            await ctx.send(f"I will now post application results to <#{channel.id}>")

    @appset.command(name="dm", aliases=["pm", "directmessage", "privatemessage"])
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def appset_dm(self, ctx, dm: Optional[bool] = None):
        """Toggles whether to DM users on application decisions"""
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
    @commands.check(is_guild_owner)
    async def acceptrole(self, ctx, role: Optional[discord.Role] = None):
        """Sets the role that can accept members"""
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
    @commands.check(is_guild_owner)
    async def appset_reset(self, ctx):
        """Resets everything for this server (applications)"""
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
            
    @appset.command(name="settings", aliases=["showsettings", "viewsettings"])
    async def appset_settings(self, ctx):
        """View server settings for applications"""
        acceptrole = await self.config.guild(ctx.guild).acceptrole()
        channel = await self.config.guild(ctx.guild).channel()
        resultchannel = await self.config.guild(ctx.guild).resultchannel()
        dm = await self.config.guild(ctx.guild).dm()

        if not acceptrole:
            pass 
        else:
            acceptrole = ctx.guild.get_role(acceptrole)
            acceptrole = acceptrole.mention
        
        if not resultchannel:
            pass 
        else:
            resultchannel = f"<#{resultchannel}>"
        
        if not channel:
            pass 
        else:
            channel = f"<#{channel}>"

        e = discord.Embed(title=f"Application settings for {ctx.guild.name}", color=discord.Color.green())
        e.add_field(name="Acceptrole", value=acceptrole)
        e.add_field(name="Resultchannel", value=resultchannel)
        e.add_field(name="Channel", value=channel)
        e.add_field(name="DirectMessage", value=dm)

        await ctx.send(embed=e)
    
    @appset.command(name="addposition")
    @commands.admin_or_permissions(manage_guild=True)
    async def addposition(self, ctx, role: Optional[discord.Role] = None):
        """Add roles that the acceptrole can accept, they still cant accept roles higher than them"""
        if not role:
            await ctx.send("You need to specify a valid role.")
            return 
        positions = await self.config.guild(ctx.guild).positions()
        positions.append(role.id)
        await self.config.guild(ctx.guild).positions.set(positions)
        await ctx.send(f"**{role.name}** can now be accepted as a role")
    
    @appset.command(name="removeposition")
    @commands.admin_or_permissions(manage_guild=True)
    async def removeposition(self, ctx, role: Optional[discord.Role] = None):
        """Remove a position that can be accepted for"""
        if not role:
            await ctx.send("Specify the role to remove.")
            return 
        positions = await self.config.guild(ctx.guild).positions()
        if role.id not in positions:
            await ctx.send("This position is not in the position list.")
            return 
        else:
            positions.remove(role.id)
            await self.config.guild(ctx.guild).positions.set(positions)
            await ctx.send(f"Removed **{role.name}** from the position list")
    
    @appset.command(name="positions")
    async def positions(self, ctx):
        """View positions you can apply for"""
        questions = await self.config.guild(ctx.guild).questions()
        formatted_list = "\n".join([p.lower() for p in questions.keys()])
        e = discord.Embed(
            title="Available positions",
            description=formatted_list,
            color=discord.Color.blurple()
        )
        await ctx.send(embed=e)
    
    @appset.command(name="create")
    async def create(self, ctx, name: str):
        """Create a set of applications"""
        allquestions = await self.config.guild(ctx.guild).questions()
        if name.lower() in allquestions:
            return await ctx.send(f"This already exists, remove it with {ctx.prefix}appset remove {name}")
        allquestions[name.lower()] = [
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
        await self.config.guild(ctx.guild).questions.set(allquestions)
        await ctx.send(f"Done. Set the questions with {ctx.prefix}appset questions {name}")
    
    @appset.command(name="remove")
    async def remove(self, ctx, name: str):
        """Remove a set of applications"""
        allquestions = await self.config.guild(ctx.guild).questions()
        if name.lower() not in allquestions:
            return await ctx.send("This does not exist")
        del allquestions[name]
        await self.config.guild(ctx.guild).questions.set(allquestions)
        await ctx.send("Done.")
        
    @appset.command(name="questions", aliases=["custom"])
    @commands.admin_or_permissions(manage_guild=True)
    async def questions(self, ctx, questionset: str):
        """Set the custom application questions"""
        await ctx.send("Lets get started. I'll ask you for the questions, and they will be your questions, you can have up to 20 questions. Type `done` when you are done")
        questions = []
        allquestions = await self.config.guild(ctx.guild).questions()
        questionset = questionset.lower()
        if questionset not in allquestions:
            return await ctx.send(f"This position does not exist. Its case sensitive. Type {ctx.prefix}appset positions for a list of positions. ")

        for i in range(20):
            await ctx.send(f"What will be question {i + 1}?")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            answer = await self.bot.wait_for("message", check=check, timeout=60)

            if answer.content.lower() == "done":
                allquestions[questionset] = questions
                await self.config.guild(ctx.guild).questions.set(allquestions)

                e = discord.Embed(title="Custom Questions", color=discord.Color.green())

                for i in range(len(questions)):
                    e.add_field(name=f"Question {i + 1}", value=questions[i], inline=False)
                await ctx.send(f"{ctx.author.mention} your custom questions", embed=e)
                return

            questions.append(answer.content)
        allquestions[questionset] = questions
        await self.config.guild(ctx.guild).questions.set(allquestions)

        e = discord.Embed(title="Custom Questions", color=discord.Color.green())

        for i in range(20):
            e.add_field(name=f"Question {i + 1}", value=questions[i], inline=False)
        
        await ctx.send(f"{ctx.author.mention} your custom questions", embed=e)

    @commands.command(name="apply")
    @commands.cooldown(600, 1, BucketType.member)
    @commands.guild_only()
    async def apply(self, ctx, position: str):
        """Apply in your server"""
        channel = await self.config.guild(ctx.guild).channel()
        if not channel:
            await ctx.send("Uh oh, looks like the application channel for this server isn't set. Please ask an admin or above to set one.")
            return 
        questions = await self.config.guild(ctx.guild).questions()
        if position.lower() not in questions:
            return await ctx.send("This position doesn't exist...")

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

        for question in questions[position.lower()]:
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
            description=f"User ID: {ctx.author.id}\nUser Name and Tag: {ctx.author}\nPosition applying for: {position}")

            for i in range(len(questions)):
                e.add_field(name=questions[i], value=answers[i], inline=False)
            await self.config.member(ctx.author).answers.set(answers)
            await self.config.member(ctx.author).current_questions.set(questions)
            await channel.send(embed=e)
            await ctx.author.send(f"Your application has been successfully sent to **{ctx.guild.name}**")
        except(Exception) as e:
            await ctx.author.send(f"Uh oh, something borked. The error was \n {e}")

    @commands.command(name="accept")
    @commands.guild_only()
    async def accept(self, ctx, member: Optional[discord.Member] = None):
        """Accept a member for a role"""
        role = await self.config.guild(ctx.guild).acceptrole()
        if not role:
            await ctx.send("This server has no configured acceptrole.")
            return
        role = ctx.guild.get_role(role)

        if role not in ctx.author.roles:
            await ctx.send(f"You need to have the role {role.name} to be able to accept members")
            return
        if not member:
            await ctx.send("Uh oh, please specify a member to accept")
            return
        
        member = ctx.guild.get_member(member.id)
        member_data = await self.config.member(member).answers()

        if len(member_data) == 0:
            await ctx.send("This member hasn't applied for anything yet.")
            return 
        
        positions = await self.config.guild(ctx.guild).positions()
        if len(positions) == 0:
            await ctx.send("There are no positions to be accepted for.")
            return 

        e = discord.Embed(title="Available positions", color=discord.Color.green())
        
        for i in range(len(positions)):
            e.add_field(name=f"Position {i+1}", value=f"<@&{positions[i]}>")
        await ctx.send(embed=e)

            
        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and str(m.content).isdigit()
            await ctx.send("Specify the number of the role you would like to accept them for.")
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            
        except asyncio.TimeoutError:
            await ctx.send("You've exceeded the 1 minute time limit.")
            return
        
        pos = int(msg.content)
        if pos > len(positions):
            await ctx.send("This position is not valid")
            
        role = positions[pos - 1]
        role = ctx.guild.get_role(role)
        
        
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
        channel = self.bot.get_channel(channel)
        if not channel:
            pass
        else:
            await channel.send(f"{member.mention} was accepted as {role.name} by {ctx.author.mention} with the reason {msg1.content}.")

        await self.config.member(member).answers.set([])
        await self.config.member(member).current_questions.set([])
        await member.add_roles(role)
        await member.send(f"You were accepted as **{role.name}** in **{ctx.guild.name}** with the reason {msg1.content}")
        await ctx.send("Done.")

    @commands.command(name="deny")
    @commands.guild_only()
    async def deny(self, ctx, member: Optional[discord.Member] = None):
        """Deny a member for a role"""
        acceptrole = await self.config.guild(ctx.guild).acceptrole()
        if not acceptrole:
            await ctx.send("This server has no configured acceptrole")
            return 

        acceptrole = ctx.guild.get_role(acceptrole)
        if acceptrole not in ctx.author.roles:
            await ctx.send(f"You need to have the **{acceptrole.name}** role to do this!")
            return 
        
        if not member:
            await ctx.send("Please specify a valid member after this!")
            return
        
        answers = await self.config.member(member).answers()
        
        if len(answers) == 0:
            await ctx.send("This member has not applied for anything yet.")
            return
        
        try:
            await ctx.send("Specify the reason here.")
            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        
        except asyncio.TimeoutError:
            await ctx.send("You ran out of time, try again later")
            return

        channel = await self.config.guild(ctx.guild).resultchannel()
        channel = self.bot.get_channel(channel)
        if not channel:
            pass 
        else:
            await channel.send(f"{member.mention} was denied by {ctx.author.mention} with the reason {msg.content}")
            
        await self.config.member(member).answers.set([])
        await self.config.member(member).current_questions.set([])
        await member.send(f"Your application was denied **{ctx.guild.name}** with the reason {msg.content}")

    
    @commands.command(name="fetchapp", aliases=["getapp", "review"])
    @commands.guild_only()
    async def fetchapp(self, ctx, applicant: Optional[discord.Member] = None):
        acceptrole = await self.config.guild(ctx.guild).acceptrole()

        if not acceptrole:
            await ctx.send("Your server does not have an acceptrole setup.")
            return 
        

        acceptrole = ctx.guild.get_role(acceptrole)

        if acceptrole not in ctx.author.roles:
            await ctx.send(f"You need to have the **{acceptrole.name}** role to view an application.")
            return 
        
        if not applicant:
            await ctx.send("You need to specify the member after this!")
            return
        
        answers = await self.config.member(applicant).answers()
        current_questions = await self.config.member(applicant).current_questions()

        if len(answers) == 0:
            await ctx.send("This user has not applied for anything yet.")
            return 
        
        else:
            e = discord.Embed(title="Application", color=discord.Color.green(), description=
            f"User ID: {applicant.id} \n Username & Tag: {applicant}")

            for i in range(len(current_questions)):
                e.add_field(name=current_questions[i], value=answers[i], inline=False)
        
        await ctx.send(embed=e)
    
