import aiohttp
import discordlists
from discord.ext import commands, tasks
from index import EMBED_COLOUR, Invite, Server, Vote, config, cursor, mydb
from utils import default


class Tasks(commands.Cog, name='task'):
    def __init__(self, bot):
        self.bot = bot
        self.fear_apiUrl = 'https://fearvps.tk/api/users/edit'
        self.fear_api.start()
        self.config = default.get("config.json")
        self.api = discordlists.Client(self.bot)
        self.api.set_auth(
            "top.gg", self.config.topgg2)
        self.api.set_auth(
            "fateslist.xyz", self.config.fates)
        self.api.set_auth("blist.xyz", self.config.blist)
        self.api.start_loop()
        
    async def post_fear(self):
        headers = { 'Content-Type': 'application/json' }
        data = {
            "user": "motz",
            "bot_users": len(self.bot.users),
            "bot_servers": len(self.bot.guilds)
        };
        async with aiohttp.ClientSession() as f:
            async with f.post(self.fear_apiUrl, json=data, headers=headers) as r:
                # print("Posted stats to Fear API")
                pass

    @tasks.loop(seconds=1)
    async def fear_api(self):
        await self.bot.wait_until_ready()
        await self.post_fear()
        
    def cog_unload(self):
        self.fear_api.close()


def setup(bot):
    bot.add_cog(Tasks(bot))
