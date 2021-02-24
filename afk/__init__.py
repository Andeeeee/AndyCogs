from .afk import Afk


def setup(bot):
    bot.add_cog(Afk(bot))
