import aiohttp
import discordlists
from discord.ext import commands, tasks
from utils import default
import nekos
import random


class Tasks(commands.Cog, name="task"):
    def __init__(self, bot):
        self.bot = bot
        self.modules = [
            "nsfw_neko_gif",
            "anal",
            "les",
            "hentai",
            "bj",
            "cum_jpg",
            "tits",
            "pussy_jpg",
            "pwankg",
            "classic",
            "spank",
            "boobs",
            "random_hentai_gif",
        ]
        # self.fear_apiUrl = "https://fearvps.tk/api/users/edit"
        # self.fear_api.start()
        self.config = default.get("config.json")
        self.api = discordlists.Client(self.bot)
        self.api.set_auth("top.gg", self.config.topgg)
        self.api.set_auth("fateslist.xyz", self.config.fates)
        self.api.set_auth("blist.xyz", self.config.blist)
        self.api.set_auth("discordlist.space", self.config.discordlist)
        self.api.set_auth("discord.bots.gg", self.config.discordbots)
        self.api.set_auth("bots.discordlabs.org", self.config.discordlabs)
        self.api.start_loop()
        self.start_chunking.start()

    async def get_hentai_img(self):
        if random.randint(1, 2) == 1:
            url = nekos.img(random.choice(self.modules))
        else:
            other_stuff = [
                "ass",
                "hentai",
                "thighs",
                "gif",
                "panties",
                "boobs",
                "ahegao",
                "yuri",
                "cum",
                "jpg",
            ]
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://api.dbot.dev/images/nsfw/{random.choice(other_stuff)}"
                ) as r:
                    j = await r.json()
                    url = j["url"]
        return url

    @tasks.loop(count=None, minutes=20)
    async def start_chunking(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            if not guild.chunked:
                await guild.chunk()

    async def cog_unload(self):
        # self.fear_api.stop()
        self.api.stop()
        self.start_chunking.stop()


async def setup(bot):
    await bot.add_cog(Tasks(bot))
