from .freeloadermode import FreeLoaderMode


def setup(bot):
    bot.add_cog(FreeLoaderMode(bot))
