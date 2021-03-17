from .userphone import UserPhone


def setup(bot):
    bot.add_cog(UserPhone(bot))
