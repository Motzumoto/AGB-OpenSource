### IMPORTANT ANNOUNCEMENT ###
#
# All additions to AGB will now cease.
# AGB's management will be limited to the following:
# - Optimization
# - Bug Fixes
# - Basic Maintenance
#
# DO NOT ADD ANY NEW FEATURES TO AGB
# ALL NEW FEATURES WILL BE RESERVED FOR MEKU
#
### IMPORTANT ANNOUNCEMENT ###

import random

from discord import Embed
from discord.ext import commands
from index import EMBED_COLOUR

# bot = None
# url_regex =
# re.compile(r"(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?")

# motz git pull check


def setup(bot):
    # This module isn't actually a cog - but it is a place
    # we can call "a trash fire"
    bot.add_cog(Utils(bot))
    # global bot
    # bot = bot_start


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def error_embed(title, description):
    return Embed(title=title, description=description, color=0xFF0000)


def success_embed(title, description):
    return Embed(title=title, description=description, color=EMBED_COLOUR)


def maxInt(val: int = 0):
    return random.randint(0, val)
