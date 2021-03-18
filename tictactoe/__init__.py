from .tictactoe import TicTacToe


def setup(bot):
    bot.add_cog(TicTacToe(bot))
