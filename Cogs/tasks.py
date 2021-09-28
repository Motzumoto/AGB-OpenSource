import aiohttp
import discordlists
from discord.ext import commands, tasks
from index import EMBED_COLOUR, Invite, Server, Vote, config, cursor, mydb
from utils import default
from datetime import datetime


class Tasks(commands.Cog, name="task"):
    def __init__(self, bot):
        self.bot = bot
        self.fear_apiUrl = "https://fearvps.tk/api/users/edit"
        self.fear_api.start()
        self.config = default.get("config.json")
        self.api = discordlists.Client(self.bot)
        self.api.set_auth("top.gg", self.config.topgg)
        self.api.set_auth("fateslist.xyz", self.config.fates)
        self.api.set_auth("blist.xyz", self.config.blist)
        self.api.start_loop()
        self.happy_birthday.start()

    @tasks.loop(count=1)
    async def happy_birthday(self):
        await self.bot.wait_until_ready()
        if datetime.today().month == 10 and datetime.today().day == 3:
            me = self.bot.get_user(101118549958877184)
            await me.send("Happy Birthday :D")

    async def post_fear(self):
        headers = {"Content-Type": "application/json"}
        data = {
            "pass": "NotForYou",
            "user": "motz",
            "bot_users": len(self.bot.users),
            "bot_servers": len(self.bot.guilds),
            "bot_shards": len(self.bot.shards),
        }
        async with aiohttp.ClientSession() as f:
            async with f.post(self.fear_apiUrl, json=data, headers=headers) as r:
                if r.status == 200:
                    # Successful Post
                    # print(f"{await r.json()}")
                    pass
                elif r.status == 400:
                    print(f"{await r.json()}")
                    # pass
                elif r.status == 201:
                    # Successful Post
                    # print(f"{await r.json()}")
                    pass
                pass

    @tasks.loop(minutes=1)
    async def fear_api(self):
        await self.bot.wait_until_ready()
        await self.post_fear()

    def cog_unload(self):
        self.fear_api.stop()
        self.happy_birthday.stop()
        self.api.stop()


def setup(bot):
    bot.add_cog(Tasks(bot))
