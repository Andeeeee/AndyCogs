from .guildtools import GuildTools 

def setup(bot):
    bot.add_cog(GuildTools(bot))