from .danksales import DankSales


def setup(bot):
    bot.add_cog(DankSales(bot))
