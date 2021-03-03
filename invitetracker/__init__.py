from .invitertracker import InviteTracker


def setup(bot):
    if not bot.intents.members:
        raise RuntimeError(
            "You should have the members intent enabled for this to work"
        )
    bot.add_cog(InviteTracker(bot))
