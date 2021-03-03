import asyncio
import discord

from datetime import datetime
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from typing import Optional, Union

INVITE_MESSAGE_USAGE = """
Sets your servers join/leave message. Variables:
{inviter}: Mentions the inviter
{inviter.name}: The inviters display name
{inviter.discriminator}: The 4 digit discriminator the inviter has
{inviter.invites}: The current amount of invites the user has
{guild}: Server Name
{guild.members}: Amount of members in the server
{user}: User Mention
{user.name}: Name of the user
{user.discriminator}: The 4 digit discriminator the user has
{user.created_at}: The date the user was created at
{user.created_at_days}: How many days ago the user was created from now
{invite}: https://discord.gg/code, where code is the invite code
{invite.code}: The raw invite code
"""


class InviteTracker(commands.Cog):
    """A cog for tracking who invited who"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 160805014090190130501014, True)

        default_guild = {
            "invites": {},
            "joinchannel": None,
            "leavechannel": None,
            "leavemessage": "{member.name} left {guild.name}. They were invited by {inviter.name} who now has {inviter.invites} invites",
            "joinmessage": "{member.name} joined {guild.name}! They were invited by {inviter.name} who now has {inviter.invites} invites",
        }

        default_member = {
            "invites": 0,
            "inviter": None,
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        self.invite_task = asyncio.create_task(self.invite_loop())

    async def invite_loop(self):
        """Check every 5 minutes for updates to the invite links"""
        await self.bot.wait_until_ready()
        for guild_id, data in (await self.config.all_guilds()).items():
            if not data["enabled"]:
                return
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            await self.save_invite_links(guild)
        await asyncio.sleep(300)

    async def save_invite_links(self, guild: discord.Guild) -> bool:
        """Saves invite links to config"""
        invites = {}
        if not guild.me.guild_permissions.manage_guild:
            return False
        for invite in await guild.invites():
            try:
                created_at = getattr(invite, "created_at", datetime.utcnow())
                channel = getattr(invite, "channel", discord.Object(id=0))
                inviter = getattr(invite, "inviter", discord.Object(id=0))
                invites[invite.code] = {
                    "uses": getattr(invite, "uses", 0),
                    "max_age": getattr(invite, "max_age", None),
                    "created_at": created_at.timestamp(),
                    "max_uses": getattr(invite, "max_uses", None),
                    "temporary": getattr(invite, "temporary", False),
                    "inviter": getattr(inviter, "id", "Unknown"),
                    "channel": channel.id,
                }
            except Exception as e:
                return False
        await self.config.guild(guild).invites.set(invites)
        return True

    async def get_inviter(self, member: discord.Member) -> str:
        """Attempt to get the inviter of a user"""
        invites = await self.config.guild(member.guild).invites()
        inviter = None
        code = None
        if invites and member.guild.me.guild_permissions.manage_guild:
            guild_invites = await member.guild.invites()
            for invite in guild_invites:
                if invite.code in invites:
                    uses = invites[invite.code]["uses"]
                    if invite.uses > uses:
                        inviter = invite.inviter
                        code = invite.code

        if not inviter:
            for code, data in invites.items():
                try:
                    invite = await self.bot.fetch_invite(code)
                except (
                    discord.errors.NotFound,
                    discord.errors.HTTPException,
                ):
                    invite = None
                else:
                    inviter = invite.inviter
                    code = invite.code

                if not invite:
                    if (data["max_uses"] - data["uses"]) == 1:
                        try:
                            inviter = await self.bot.fetch_user(data["inviter"])
                            code = data["code"]
                        except (discord.errors.NotFound, discord.errors.Forbidden):
                            inviter = None

        await self.save_invite_links(member.guild)

        if (
            member.guild.me.guild_permissions.manage_guild
            and member.guild.me.guild_permissions.view_audit_log
        ) and not inviter:
            valid_action = discord.AuditLogAction.invite_create
            async for log in member.guild.audit_logs(action=valid_action):
                if log.target.code not in invites:
                    inviter = log.target.inviter
                    break
        return inviter, code

    def cog_unload(self):
        self._unload()

    def _unload(self):
        if self.invite_task:
            self.invite_task.cancel()

    @commands.group()
    async def invitetrackerset(self, ctx):
        """Set server settings for invite tracking"""
        pass

    @invitetrackerset.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def joinchannel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Sets the channel join messages are sent to"""
        if not channel:
            await self.config.guild(ctx.guild).joinchannel.clear()
            await ctx.send("No longer sending invite messages to a channel")
        else:
            await self.config.guild(ctx.guild).joinchannel.set(channel.id)
            await ctx.send(f"Now logging member invite messages to {channel.mention}")

    @invitetrackerset.command(aliases=["joinmsg"], usage=INVITE_MESSAGE_USAGE)
    @commands.admin_or_permissions(manage_guild=True)
    async def joinmessage(self, ctx, *, message=None):
        """Set the message when a user joins the server"""
        if not message:
            await self.config.guild(ctx.guild).joinmessage.clear()
            await ctx.send("The message has been reset")
        else:
            await self.config.guild(ctx.guild).joinmessage.set(message)
            await ctx.send("The message has been set")

    @invitetrackerset.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def leavechannel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Sets the channel leave messages are sent to"""
        if not channel:
            await self.config.guild(ctx.guild).leavechannel.clear()
            await ctx.send("No longer sending invite messages to a channel")
        else:
            await self.config.guild(ctx.guild).leavechannel.set(channel.id)
            await ctx.send(f"Now logging member invite messages to {channel.mention}")

    @invitetrackerset.command(aliases=["leavemsg"], usage=INVITE_MESSAGE_USAGE)
    @commands.admin_or_permissions(manage_guild=True)
    async def leavemessage(self, ctx, *, message=None):
        """Set the message when a user leaves the server"""
        if not message:
            await self.config.guild(ctx.guild).leavemessage.clear()
            await ctx.send("The message has been reset")
        else:
            await self.config.guild(ctx.guild).leavemessage.set(message)
            await ctx.send("The message has been set")

    @invitetrackerset.command(aliases=["showsettings"])
    async def settings(self, ctx):
        """View server settings for invite tracking"""
        data = await self.config.guild(ctx.guild).all()
        e = discord.Embed(
            title=f"Invite Settings for {ctx.guild.name}", color=await ctx.embed_color()
        )
        e.add_field(
            name="Join Channel",
            value=f"<#{data['joinchannel']}>"
            if data["joinchannel"] is not None
            else "Not Set",
        )
        e.add_field(
            name="Leave Channel",
            value=f"<#{data['leavechannel']}>"
            if data["leavechannel"] is not None
            else "Not Set",
        )
        e.add_field(name="Join Message", value=box(data["joinmessage"]), inline=False)
        e.add_field(name="Leave Message", value=box(data["leavemessage"]), inline=False)
        await ctx.send(embed=e)

    @commands.group(invoke_without_command=True)
    async def invites(self, ctx, user: Optional[discord.Member] = None):
        """View your own/ a users invites in this server"""
        if not ctx.invoked_subcommand:
            if not user:
                user = ctx.author
            invites = await self.config.member(user).invites()
            await ctx.send(f"**{user.name}** has **{invites}** invites")

    @invites.command()
    async def who(self, ctx, user: Optional[discord.Member] = None):
        """View the person that invited you or another member"""
        if not user:
            user = ctx.author
        inviter = await self.config.member(user).inviter()
        if not inviter:
            return await ctx.send(
                f"**{user}** either joined from a vanity invite or I couldn't track this"
            )
        elif ctx.guild.get_member(inviter) is None:
            return await ctx.send(
                f"**{user}**'s inviter seems to have left the server, the id is {inviter}"
            )
        else:
            inviter = ctx.guild.get_member(inviter)
            await ctx.send(f"**<@{inviter.display_name}>** invited **{user}**")

    @invites.command()
    async def top(
        self, ctx, amount: Optional[int] = 10, top_to_bottom: Optional[bool] = True
    ):
        """View the top/bottom inviters"""
        all_members = await self.config.all_members(ctx.guild)
        member_data = [
            (member, data["invites"])
            for member, data in all_members
            if data["count"] > 0 and ctx.guild.get_member(int(member)) is not None
        ]
        sorted_data = sorted(member_data, key=lambda k: k[1], reverse=top_to_bottom)[
            :amount
        ]

        leaderboard = ""

        for i, member, invites in enumerate(sorted_data, start=1):
            leaderboard += f"{i}. <@{member}>: {invites}"

        if len(leaderboard) >= 2048:
            pages = list(pagify(leaderboard))
            embeds = []
            for i, page in enumerate(pages, start=1):
                e = discord.Embed(
                    title=f"Invite Leaderboard for {ctx.guild.name}",
                    color=await ctx.embed_color(),
                    description=page,
                )
                e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
                e.set_footer(text=f"Page {i}/{len(pages)} pages")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                title=f"Invite Leaderboard for {ctx.guild.name}",
                color=await ctx.embed_color(),
                description=leaderboard,
            )
            e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            await ctx.send(embed=e)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        data = await self.config.guild(guild).all()
        time = datetime.utcnow()
        since_created = (time - member.created_at).days
        user_created = member.created_at.strftime("%d %b %Y %H:%M")

        inviter, code = await self.get_inviter(member)
        channel = self.bot.get_channel(data["joinchannel"])
        if not channel:
            await self.config.guild(member.guild).joinchannel.clear()
        if not inviter:
            if not channel:
                return
            else:
                await channel.send(
                    f"I couldn't figure out how **{member.display_name}** joined"
                )
        else:
            await self.config.member(member).inviter.set(inviter.id)
            invites = await self.config.member_from_ids(guild.id, inviter.id).invites()
            invites += 1
            await self.config.member_from_ids(guild.id, inviter.id).invites.set(invites)
            if not channel:
                return
            message = await self.config.guild(member.guild).joinmessage()
            replace_dict = {
                "{inviter}": inviter.mention,
                "{inviter.name}": inviter.display_name,
                "{inviter.mention}": inviter.mention,
                "{inviter.invites}": invites,
                "{inviter.discriminator}": str(inviter).split("#")[1],
                "{guild}": member.guild.name,
                "{guild.members}": len(member.guild.members),
                "{user}": member.mention,
                "{user.name}": member.display_name,
                "{user.mention}": member.mention,
                "{user.discriminator}": str(member).split("#")[1],
                "{user.created_at}": user_created,
                "{user.created_at_days}": since_created,
                "{invite}": f"https://discord.gg/{code}" if code is not None else "UNKNOWN LINK",
                "{invite.code}": code if code is not None else "UNKNOWN CODE",
            }
            for word, replacement in replace_dict.items():
                message.replace(word, str(replacement))
            await channel.send(message)

    @commands.Cog.listener()
    async def on_member_leave(self, member: discord.Member):
        guild = member.guild
        data = await self.config.guild(guild).all()
        time = datetime.utcnow()
        since_created = (time - member.created_at).days
        user_created = member.created_at.strftime("%d %b %Y %H:%M")

        inviter = await self.config.member(member).inviter()
        channel = self.bot.get_channel(data["leavechannel"])
        if not channel:
            await self.config.guild(guild).leavechannel.clear()
        if not inviter:
            if not channel:
                return
            else:
                await channel.send(
                    f"I couldn't figure out who inivited **{member.name}**"
                )
        else:
            invites = await self.config.member_from_ids(guild.id, inviter).invites()
            invites += 1
            await self.config.member_from_ids(guild.id, inviter).invites.set(invites)
            if not channel:
                return
            message = await self.config.guild(member.guild).leavemessage()
            inviter = guild.get_member(inviter)
            replace_dict = {
                "{inviter}": inviter.mention,
                "{inviter.name}": inviter.display_name,
                "{inviter.mention}": inviter.mention,
                "{inviter.invites}": invites,
                "{inviter.discriminator}": str(inviter).split("#")[1],
                "{guild}": member.guild.name,
                "{guild.members}": len(member.guild.members),
                "{user}": member.mention,
                "{user.name}": member.display_name,
                "{user.mention}": member.mention,
                "{user.discriminator}": str(member).split("#")[1],
                "{user.created_at}": user_created,
                "{user.created_at_days}": since_created,
            }
            for word, replacement in replace_dict.items():
                message.replace(word, str(replacement))
            await channel.send(message)
