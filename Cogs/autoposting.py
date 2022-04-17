import asyncio
import random
from typing import Union

import aiohttp
import discord
from discord.ext import commands, tasks
from index import EMBED_COLOUR, config, cursor_n, logger, mydb_n
from utils import default
from Manager.logger import formatColor

from utils.default import log

BotList_Servers = [
    336642139381301249,
    716445624517656727,
    523523486719803403,
    658262945234681856,
    608711879858192479,
    446425626988249089,
    387812458661937152,
    414429834689773578,
    645281161949741064,
    527862771014959134,
    733135938347073576,
    766993740463603712,
    724571620676599838,
    568567800910839811,
    641574644578648068,
    532372609476591626,
    374071874222686211,
    789934742128558080,
    694140006138118144,
    743348125191897098,
    110373943822540800,
    491039338659053568,
    891226286347923506,
]


class autoposting(commands.Cog, name="ap"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.autoh.start()
        self.config = default.get("config.json")
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
        self.lunar_headers = {f"{config.lunarapi.header}": f"{config.lunarapi.token}"}

    async def get_hentai_img(self):
        other_stuff = ["jpg", "gif", "yuri"]
        async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
            async with s.get(
                f"https://lunardev.group/api/nsfw/{random.choice(other_stuff)}",
                json={"user": "683530527239962627"},
            ) as r:
                j = await r.json()
                url = j["url"]

        return url

    async def send_from_webhook(self, webhook: discord.Webhook, embed: discord.Embed):
        try:
            await webhook.send(embed=embed, avatar_url=self.bot.user.avatar)
        except Exception as e:
            logger.error(f"Autoposting: webhook error | {formatColor(e), 'red'}")
            return

    @tasks.loop(count=None, minutes=random.randint(1, 5))
    async def autoh(self):
        await self.bot.wait_until_ready()
        posts = 0
        log("Starting autoposting")
        me = await self.bot.fetch_user(101118549958877184)
        if random.randint(1, 10) == 3:
            embed = discord.Embed(
                title="Enjoy your poggers porn lmao",
                description=f"Posting can be slow, please take into consideration how many servers this bot is in and how many are using auto posting. Please be patient. If I completely stop posting, please rerun the command or join the support server.\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
                colour=EMBED_COLOUR,
            )
        else:
            embed = discord.Embed(
                title="Enjoy your poggers porn lmao",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
                colour=EMBED_COLOUR,
            )
        embed.set_footer(
            text=f"lunardev.group\nPosting every 1-5 minutes", icon_url=me.avatar
        )

        cursor_n.execute(
            'SELECT DISTINCT "hentaichannel" FROM public.guilds WHERE "hentaichannel" IS NOT NULL'
        )
        try:
            embed.set_image(url=(await self.get_hentai_img()))
        except Exception as e:
            logger.error(f"AutoPosting Error | {formatColor(e), 'red'}")
            try:
                embed.set_image(url=(await self.get_hentai_img()))
            except Exception as e:
                logger.error(f"AutoPosting Error | {formatColor(e), 'red'}")
            # check if the embed image is None
            if embed.image is None:
                try:
                    embed.set_image(url=(await self.get_hentai_img()))
                except Exception as e:
                    logger.error(f"AutoPosting Error | {formatColor(e), 'red'}")
                else:
                    pass
        else:
            for row in cursor_n.fetchall():
                if row[0] is None:
                    continue
                else:
                    channel = self.bot.get_channel(int(row[0]))
                    if channel is None:
                        continue
                    # if not channel.guild.chunked:
                    #     await channel.guild.chunk()
                    #     if channel.guild.member_count < 15:
                    #         # remove that channel
                    #         cursor_n.execute(
                    #             f"UPDATE public.guilds SET hentaichannel = NULL WHERE guildId = '{channel.guild.id}'"
                    #         )
                    #         log(
                    #             f"Removed hentaichannel from {channel.guild.name}: {channel.guild.member_count} members"
                    #         )
                    #         continue
                    if channel is not None:
                        if channel.guild.id == BotList_Servers:
                            continue
                        else:
                            if not channel.is_nsfw():
                                if channel.guild.id in BotList_Servers:
                                    continue
                                else:
                                    # Remove hentai channel from db
                                    cursor_n.execute(
                                        f"UPDATE public.guilds SET hentaichannel = NULL WHERE guildId = '{channel.guild.id}'"
                                    )
                                    mydb_n.commit()
                                    logger.warning(
                                        f"{channel.guild.id} is no longer NSFW, so I have removed the channel from the database."
                                    )
                                    continue
                            else:
                                try:
                                    webhooks = await channel.webhooks()
                                    webhook = discord.utils.get(
                                        webhooks,
                                        name="AGB Autoposting",
                                        user=self.bot.user,
                                    )
                                    if webhook is None:
                                        # check all the channels webhooks for AGB Autoposting
                                        for w in webhooks:
                                            if w.name == "AGB Autoposting":
                                                # check if there are more than one webhooks
                                                await w.delete()
                                        webhook = await channel.create_webhook(
                                            name="AGB Autoposting"
                                        )
                                except discord.errors.Forbidden:
                                    webhook = None
                                except Exception:
                                    webhook = None
                                final_messagable: Union[
                                    discord.Webhook, discord.TextChannel
                                ] = (channel if webhook is None else webhook)
                                posts += 1
                                try:
                                    if isinstance(
                                        final_messagable, discord.TextChannel
                                    ):
                                        await final_messagable.send(embed=embed)
                                        await asyncio.sleep(0.5)
                                    else:
                                        await self.send_from_webhook(
                                            final_messagable, embed
                                        )
                                        await asyncio.sleep(0.5)
                                except discord.Forbidden as e:
                                    ## error is more likely to be a 404, check the logs regardless
                                    logger.error(
                                        f"Autoposting error | {channel.guild.id} / {channel.guild.name} / {channel.id}"
                                    )
                                    logger.error(f"Autoposting error | {e}")
                                    logger.error(
                                        f"Autoposting error | {e.__traceback__}"
                                    )
                                    log(
                                        "Autoposting info | Removing hentai channel from database"
                                    )
                                    # this is probably an awful idea but its the only way to remove the channel if the bot is not allowed to post in it
                                    # lets hope discord doesnt fuck up and the webhook is actually there
                                    cursor_n.execute(
                                        f"UPDATE public.guilds SET hentaichannel = NULL WHERE guildId = '{channel.guild.id}'"
                                    )
                                    # subtarct 1 from the posts
                                    posts -= 1
            log(f"Autoposting - Posted Batch: {formatColor(str(posts), 'green')}")

    async def cog_unload(self):
        self.autoh.stop()
        log("Autoposting - Stopped")

    async def cog_relaod(self):
        self.autoh.stop()
        log("Autoposting - Reloaded")


async def setup(bot):
    await bot.add_cog(autoposting(bot))
