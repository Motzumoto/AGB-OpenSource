import random
from typing import Union

import aiohttp
import discord
import nekos
from discord.ext import commands, tasks
from index import EMBED_COLOUR, config, cursor, mydb
from utils import default

hap = 0


class autoposting(commands.Cog, name="ap"):
    def __init__(self, bot):
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

    async def get_hentai_img(self):
        if random.randint(1, 2) == 1:
            url = nekos.img(random.choice(self.modules))
        else:
            other_stuff = ["bondage", "hentai", "thighs"]
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://shiro.gg/api/images/nsfw/{random.choice(other_stuff)}"
                ) as r:
                    j = await r.json()
                    url = j["url"]
        return url

    async def send_from_webhook(self, webhook: discord.Webhook, embed: discord.Embed):
        await webhook.send(embed=embed, avatar_url=self.bot.user.avatar_url)

    @tasks.loop(count=None, minutes=3)
    async def autoh(self):
        await self.bot.wait_until_ready()
        me = self.bot.get_user(101118549958877184)
        hap_update = hap
        hap_update += 1
        print(f"{default.date()} | Autoposting - Posted Batch")
        embed = discord.Embed(
            title="Enjoy your poggers porn lmao",
            description=f"Posting can be slow, please take into consideration how many servers this bot is in and how many are using auto posting. Please be patient. If I completely stop posting, please rerun the command or join the support server.\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            colour=EMBED_COLOUR,
        )

        cursor.execute(
            f"SELECT DISTINCT hentai_channel FROM guilds WHERE hentai_channel IS NOT NULL"
        )
        try:
            embed.set_image(url=(await self.get_hentai_img()))
        except nekos.errors.NothingFound:
            print(
                f"{default.date()} | [ERR] AutoPosting - No image found.\nTrying again..."
            )
            await me.send(
                "Attempt 1 at finding an image for autoposting failed... We're trying again."
            )
            try:
                embed.set_image(url=(await self.get_hentai_img()))
            except:
                print(
                    f"{default.date()} |[ERR] I still could not get an image to post with... so we're just not gonna do anything lmao"
                )
                await me.send("Attempt 2 at finding an image for autoposting failed.")
                return
        except Exception as e:
            print(f"{default.date()} | Error:", e)
            return
        else:
            for row in cursor.fetchall():
                if row[0] == None:
                    return
                else:
                    channel = self.bot.get_channel(int(row[0]))
                    # guild = await self.bot.fetch_guild(int(row[0]))
                    if channel is None:
                        # remove the channel from the database
                        print(
                            f"{default.date()} | [ERR] AutoPosting - Channel not found. Removing from database."
                        )
                        cursor.execute(
                            f"UPDATE guilds SET hentai_channel = NULL WHERE hentai_channel = {row[0]}"
                        )  # NEW
                        # cursor.execute(f"UPDATE guilds SET hentai_channel = NULL WHERE hentai_channel = {row[0]}") # OLD
                    if channel != None:
                        if not channel.is_nsfw():
                            try:
                                # Remove hentai channel from db
                                cursor.execute(
                                    f"UPDATE guilds SET hentai_channel = NULL WHERE guildId = {channel.guild.id}"
                                )
                                mydb.commit()
                                print(
                                    f"{default.date()} | {channel.guild.id} has removed the NSFW tag | Deleting from database..."
                                )
                            except:
                                pass
                        else:
                            try:
                                webhooks = await channel.webhooks()
                                webhook = discord.utils.get(
                                    webhooks, name="AGB Autoposting", user=self.bot.user
                                )
                                if webhook is None:
                                    webhook = await channel.create_webhook(
                                        name="AGB Autoposting"
                                    )
                            except discord.Forbidden:
                                webhook = None
                            except Exception as e:
                                print(
                                    f"{default.date()} | Wasn't able to get webhook because of error: {e}"
                                )
                                webhook = None
                            final_messagable: Union[
                                discord.Webhook, discord.TextChannel
                            ] = (channel if webhook is None else webhook)
                            try:
                                if isinstance(final_messagable, discord.TextChannel):
                                    await final_messagable.send(embed=embed)
                                else:
                                    await self.send_from_webhook(
                                        final_messagable, embed
                                    )
                            except Exception as e:
                                cursor.execute(
                                    f"UPDATE guilds SET hentai_channel = NULL WHERE guildId = {channel.guild.id}"
                                )
                                mydb.commit()


def setup(bot):
    bot.add_cog(autoposting(bot))
