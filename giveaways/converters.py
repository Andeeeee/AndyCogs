#Originally from Phen-Cogs https://github.com/phenom4n4n/phen-cogs/blob/master/lock/converters.py

from typing import Union

import discord
from unidecode import unidecode
from rapidfuzz import process
from discord.ext.commands.converter import RoleConverter
from redbot.core import commands
from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import inline




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
        final_results = []
        argument = argument.split(";;")
        guild = ctx.guild
        result = []
        for arg in argument:
            if arg.isdigit():
                role = guild.get_role(int(arg))
                if role is not None:
                    final_results.append(role)
            for r in process.extract(
                argument,
                {r: unidecode(r.name) for r in guild.roles},
                limit=None,
                score_cutoff=75,
            ):
                result.append((r[2], r[1]))
                return result, r
            sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
            final_results.append(sorted_result[0][0])
        
        return final_results