from .application import Applications


def setup(bot):
    bot.add_cog(Applications(bot))
