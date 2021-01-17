import discord 
from redbot.core import commands 
from redbot.core import Config 
from redbot.core.commands import BucketType
from typing import Optional 

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.config = Config.get_conf(self, identifier=160805014090190130501014, force_registration=True) #e

        default_guild = {
            "channel": None,
            "decision_channel": None,
            "blacklist": [],
            "edit": False,
            "dm": True,
            "suggestions": {},
            "anon": False,
        }

        self.config.register_guild(**default_guild)
    
    @commands.group(name="suggestions", aliases=["suggestset"])
    @commands.guild_only()
    async def suggestions(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send_help("suggestions")
    
    @suggestions.command(name="channel", aliases=["submissionchannel"])
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestions_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """The channel where suggestions are logged to"""
        if not channel:
            await self.config.guild(ctx.guild).channel.set(None)
            await ctx.send("Suggestions have been closed.")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(f"I will now send suggestions to <#{channel.id}>")

    @suggestions.command(name="decision", aliases=["decisionchannel"])
    @commands.admin_or_permissions(manage_guild=True)
    async def decision(self, ctx, channel: Optional[discord.TextChannel] = None):
        """The channel where decisions are sent"""
        if not channel:
            await self.config.guild(ctx.guild).decision_channel.set(None)
            await ctx.send("I will now post suggestion decisions in the submission channel")
        else:
            await self.config.guild(ctx.guild).decision_channel.set(channel.id)
            await ctx.send(f"I will now post suggestion decisions in <#{channel.id}>")

    @suggestions.command(name="directmessage", aliases=["dm"])
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestions_directmessage(self, ctx, dm: Optional[bool] = None):
        """Toggles whether to DM the user whos suggestion was rejected or approved"""
        if dm is None:
            await ctx.send("You need to specify either True or False after this command.")
        else:
            await self.config.guild(ctx.guild).dm.set(dm)
            if dm:
                await ctx.send("I will now directmessage users on suggestion decisions.")
            else:
                await ctx.send("I will no longer directmessage users on suggestion decisions.")
    
    @suggestions.command(name="edit")
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestions_edit(self, ctx, edit: Optional[bool] = None):
        """Edits suggestions instead of reposting them, still sends in decision channel though"""
        if edit is None:
            await ctx.send("You need to specify either True or False after this command.")
        else:
            await self.config.guild(ctx.guild).edit.set(edit)
            if edit:
                await ctx.send("I will now edit messages instead of reposting them (Still send in decision channel if there is one).")
            else:
                await ctx.send("I will no longer edit messages and instead repost them.")

    @suggestions.command(name="blacklist", aliases=["bl"])
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestions_blacklist(self, ctx, member: Optional[discord.Member] = None):
        if not member:
            await ctx.send("Please specify a valid member to blacklist!")
        else:
            current_blacklist = await self.config.guild(ctx.guild).blacklist()
            current_blacklist.append(member.id)
            await self.config.guild(ctx.guild).blacklist.set(current_blacklist)

            await ctx.send(f"**{member.name}** has been blacklisted from making suggestions in this server.")

    @suggestions.command(name="anonymous", aliases=["anon"])
    @commands.admin_or_permissions(manage_guild=True)
    async def anonymous(self, ctx, anon: Optional[bool] = None):
        if anon is None:
            await ctx.send("You need to specify either True or False after this.")
        else:
            await self.config.guild(ctx.guild).anon.set(anon)
            if anon:
                await ctx.send("Suggestion authors will no longer show up on suggestions.")
            else:
                await ctx.send("Suggestion authors will now show up on suggestions.")
    
    @suggestions.command(name="who")
    @commands.mod_or_permissions(manage_guild=True)
    async def who(self, ctx, number: Optional[int] = None):
        """A way to find the user for anonymous suggestions."""
        number = str(number)
        suggestions = await self.config.guild(ctx.guild).suggestions()

        if number not in suggestions:
            await ctx.send("This suggestion does not exist.")
            return 
        else:
            suggestion = suggestions[number]
            author = suggestion["user"]
            content = suggestion["content"]
            author = ctx.guild.get_member(author)
            await ctx.send(f"**{author.name}** made suggestion {number}, the content was `{content}`")
        


    @commands.command(name="suggest")
    @commands.guild_only()
    @commands.cooldown(20, 1, BucketType.member)
    async def suggest(self, ctx, * , content = None):
        blacklist = await self.config.guild(ctx.guild).blacklist()

        if ctx.author.id in blacklist:
            await ctx.send("You are blacklisted from making suggestions in this server")
            return 
        
        if not content:
            await ctx.send("You need to suggest something for this to work")
        
        channel = await self.config.guild(ctx.guild).channel()
        if not channel:
            await ctx.send("The suggestion channel has not been setup yet.")
            return 
        
        suggestions = await self.config.guild(ctx.guild).suggestions()
        
        if len(suggestions) == 0:
            total = 1 
        else:
            total = len(suggestions)
            total += 1
        
        total = str(total)
        suggestions[total] = {}
        suggestions[total]["user"] = ctx.author.id
        suggestions[total]["content"] = content
        
        channel = self.bot.get_channel(channel)

        if not channel.permissions_for(ctx.me).send_messages:
            await ctx.send("Uh oh, I do not have permissions to send messages in the suggestion channel.")
            return 
        
        anon = await self.config.guild(ctx.guild).anon()
        if anon:
            author = "Anonymous"
            author_url = "https://images-ext-1.discordapp.net/external/goXavQ0zzaSkv9RaOMTZEOa7Gs4a8LfOA8oGcE9XWmw/https/i.imgur.com/y43mMnP.png"
            footer = "Anonymous"
        else:
            author = ctx.author 
            author_url = ctx.author.avatar_url
            footer = f"ID: {ctx.author.id}"
        
        e = discord.Embed(title=f"Suggestion #{total}", color=discord.Color.green(), description=content)
        e.set_author(name=author, url=author_url)
        e.set_footer(text=footer)

        message = await channel.send(embed=e)
        suggestions[total]["messageid"] = message.id
        await self.config.guild(ctx.guild).suggestions.set(suggestions)

        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await ctx.author.send(f"Your suggestion has been sent for approval. You can view it here: {message.jump_url}")

        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await ctx.message.delete()
    
    @commands.command(name="approve")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_guild=True)
    async def approve(self, ctx, number: Optional[int] = None, * , reason="No Reason Provided"):
        if not number:
            await ctx.send("This is not a valid suggestion.")
            return 

        suggestions = await self.config.guild(ctx.guild).suggestions()

        if len(suggestions) == 0:
            await ctx.send("This server has no suggestions")
            return 
        number = str(number)

        if number not in suggestions:
            await ctx.send("This suggestion does not exist.")
            return 

        suggestion = suggestions[number]
        messageid = suggestion["messageid"]
        author = suggestion["user"]
        content = suggestion["content"]

        channel = await self.config.guild(ctx.guild).channel()
        channel = self.bot.get_channel(channel)
        try:
            message = await channel.fetch_message(messageid)
        except discord.NotFound:
            await ctx.send("Uh oh, I couldn't find this message. Check if you changed your suggestion channel.")
            return 
        e = discord.Embed(title=f"Suggestion #{number} approved.", description=content, color=discord.Color.green())
        e.add_field(name=f"Approved by {ctx.author}", value=reason)
        edit = await self.config.guild(ctx.guild).edit()

        newchannel = await self.config.guild(ctx.guild).decision_channel()

        if edit:
            await message.edit(embed=e)
        else:
            if not newchannel:
                await channel.send(embed=e)
            else:
                newchannel = self.bot.get_channel(newchannel)
                await newchannel.send(embed=e)

        dm = await self.config.guild(ctx.guild).dm()
        if dm:
            await ctx.author.send("Your suggestion was approved!", embed=e)
        
    @commands.command(name="reject")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_guild=True)
    async def reject(self, ctx, number: Optional[int] = None, * , reason="No Reason Provided"):
        if not number:
            await ctx.send("This is not a valid suggestion.")
            return 

        suggestions = await self.config.guild(ctx.guild).suggestions()

        if len(suggestions) == 0:
            await ctx.send("This server has no suggestions")
            return 

        number = str(number)

        if number not in suggestions:
            await ctx.send("This suggestion does not exist.")
            return 

        suggestion = suggestions[number]
        messageid = suggestion["messageid"]
        author = suggestion["user"]
        content = suggestion["content"]

        channel = await self.config.guild(ctx.guild).channel()
        channel = self.bot.get_channel(channel)
        try:
            message = await channel.fetch_message(messageid)
        except discord.NotFound:
            await ctx.send("Uh oh, I couldn't find this message. Check if you changed your suggestion channel.")
            return 
        e = discord.Embed(title=f"Suggestion #{number} denied.", description=content, color=discord.Color.red())
        e.add_field(name=f"Denied by {ctx.author}", value=reason)
        edit = await self.config.guild(ctx.guild).edit()

        newchannel = await self.config.guild(ctx.guild).decision_channel()

        if edit:
            await message.edit(embed=e)
        else:
            if not newchannel:
                await channel.send(embed=e)
            else:
                newchannel = self.bot.get_channel(newchannel)
                await newchannel.send(embed=e)

        dm = await self.config.guild(ctx.guild).dm()
        if dm:
            author = ctx.guild.get_member(author)
            if not author:
                return 
            await author.send("Your suggestion was denied.", embed=e)
        
        

    
        