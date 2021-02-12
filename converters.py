from typing import Union
import discord
from rapidfuzz import process
from discord.ext.commands.converter import Converter
from redbot.core import commands
from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import inline

class FuzzyItem(Converter):
    """
    This will accept role ID's, mentions, and perform a fuzzy search for
    roles within the guild and return a list of role objects
    matching partial names
    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        items = [
            "cursor",
            "grandma",
            "megaclicker",
            "superclicker",
            "epicclicker",
            "factory",
            "ultraclicker",
            "godclicker",
            "spamclicker",
            "holyclicker",
            "memeclicker",
            "cookietrophy",
            "blob",
            "andycookie",
        ]

        result = []
        for r in process.extract(
            argument,
            items,
            limit=None,
            score_cutoff=75,
        ):
            result.append(r[0])

        if not result:
            raise BadArgument(f'Shop "{argument}" not found.' if self.response else None)

        sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
        return sorted_result[0]