#Originally from Phen-Cogs https://github.com/phenom4n4n/phen-cogs/blob/master/lock/converters.py

from typing import Union
import re
import discord
from unidecode import unidecode
from rapidfuzz import process
from discord.ext.commands.converter import RoleConverter, Converter
from redbot.core import commands
from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import inline


link_regex = re.compile(
    r"https?:\/\/(?:(?:ptb|canary)\.)?discord(?:app)?\.com"
    r"\/channels\/(?P<guild_id>[0-9]{15,19})\/(?P<channel_id>"
    r"[0-9]{15,19})\/(?P<message_id>[0-9]{15,19})\/?"
)

#thanks pheno


# original converter from https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/converters.py#L19

class FuzzyRole(RoleConverter):
    """
    This will accept role ID's, mentions, and perform a fuzzy search for
    roles within the guild and return a list of role objects
    matching partial names
    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """

    def __init__(self, response: bool = True):
        self.response = response
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        if argument.lower() == "none":
            return []
        final_results = []
        pattern = re.compile(r"\||;;")
        argument = pattern.split(argument)
        guild = ctx.guild
        result = []
        mee6 = None
        for arg in argument:
            mee6_split = arg.split("=="),
            if mee6_split[0] == "mee6" and len(mee6_split) >= 2:
                if guild.get_member(159985870458322944) is None:
                    raise BadArgument("Can't add MEE6 requirements without MEE6 in your server")
                try:
                    mee6 = int(mee6_split[1])
                    continue
                except ValueError:
                    continue 
            arg = arg.lstrip("<@&").rstrip(">")
            if arg.isdigit():
                role = guild.get_role(int(arg))
                if not role:
                    pass 
                else:
                    if role in final_results:
                        continue
                    final_results.append(role)
                    continue
            for r in process.extract(
                arg,
                {r: unidecode(r.name) for r in guild.roles},
                limit=None,
                score_cutoff=75,
            ):
                result.append((r[2], r[1]))

            
            sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
            if sorted_result[0][0] in final_results:
                continue
            final_results.append(sorted_result[0][0])
            result = []
        
        return final_results, mee6

class IntOrLink(Converter):
    async def convert(self, ctx, argument: str):
        if argument.isdigit():
            return argument 
        if len(argument.split("-")) == 2:
            return argument.split("-")[1]
        match = re.search(link_regex, argument)
        if not match:
            raise BadArgument("Not a valid message")
        message_id = int(match.group("message_id"))
        channel_id = int(match.group("channel_id"))
        channel = ctx.bot.get_channel(channel_id)

        if channel is None or channel.guild is None or channel.guild != ctx.guild:
            raise BadArgument("This was not recognized as a valid channel or the channel is not in the same server")
        
        message = ctx.bot._connection._get_message(message_id)
        
        if not message:
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                raise BadArgument("Message not found")
        
        return message.id
        