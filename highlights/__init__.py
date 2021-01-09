from .highlight import Highlight

#I should add end_user_statements

def setup(bot):
    bot.add_cog(Highlight(bot))
