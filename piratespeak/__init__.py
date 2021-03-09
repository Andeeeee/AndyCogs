from .piratespeak import PirateSpeak

def setup(bot):
    cog = PirateSpeak(bot)
    bot.add_cog(cog)
    cog.initialize()