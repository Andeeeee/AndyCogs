from .danklogs import DankLogs 

def setup(bot):
    bot.add_cog(DankLogs(bot))