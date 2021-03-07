from .lotteryreminder import LotteryReminder


def setup(bot):
    bot.add_cog(LotteryReminder(bot))
