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

from datetime import datetime

import aiohttp
import discordlists
from discord.ext import commands, tasks
from index import logger
from utils import default
import requests
import os
import nekos
import random


class Tasks(commands.Cog, name="task"):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")
        self.api = discordlists.Client(self.bot)
        self.api.set_auth("top.gg", self.config.topgg)
        self.api.set_auth("fateslist.xyz", self.config.fates)
        self.api.set_auth("blist.xyz", self.config.blist)
        self.api.set_auth("discordlist.space", self.config.discordlist)
        self.api.set_auth("discord.bots.gg", self.config.discordbots)
        self.api.set_auth("bots.discordlabs.org", self.config.discordlabs)
        self.api.start_loop()
        self.happy_birthday.start()

    @tasks.loop(count=None, minutes=2)
    async def happy_birthday(self):
        await self.bot.wait_until_ready()
        if datetime.today().month == 10 and datetime.today().day == 3:
            me = self.bot.get_user(101118549958877184)
            await me.send("Happy Birthday :D")

    @tasks.loop(minutes=1)
    async def fear_api(self):
        await self.bot.wait_until_ready()
        await self.post_fear()


    def cog_unload(self):
        self.fear_api.stop()
        self.hentai_steal.stop()
        self.happy_birthday.stop()
        self.api.stop()


def setup(bot):
    bot.add_cog(Tasks(bot))
