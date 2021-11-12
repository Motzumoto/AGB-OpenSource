import datetime
import json
import math
import os
import random
import time
from datetime import datetime, timedelta
from typing import List, Union

import aiohttp
import discord
import googletrans
import psutil
import requests
from discord.ext import commands
from index import EMBED_COLOUR, config, cursor, delay, emojis, mydb, logger
from matplotlib.pyplot import title
from utils import default, permissions
from Manager.commandManager import commandsEnabled


def list_items_in_english(l: List[str], oxford_comma: bool = True) -> str:
    """
    Produce a list of the items formatted as they would be in an English sentence.
    So one item returns just the item, passing two items returns "item1 and item2" and
    three returns "item1, item2, and item3" with an optional Oxford comma.
    """
    return ", ".join(
        l[:-2] + [((oxford_comma and len(l) != 2) * "," + " and ").join(l[-2:])]
    )


class Information(commands.Cog, name="info"):
    """Info commands for info related things"""

    def __init__(self, bot):
        """Info commands for info related things"""
        self.bot = bot
        self.trans = googletrans.Translator()
        self.config = default.get("config.json")
        # self.blist_api = blist.Blist(bot, token=self.config.blist)
        self.process = psutil.Process(os.getpid())

    def cog_unload(self):
        self.process.stop()

    def weather_message(self, data, location):
        location = location.title()
        embed = discord.Embed(
            title=f"{data['name']} Weather",
            description=f"Here is the weather data for {data['name']}.",
            color=EMBED_COLOUR,
        )
        embed.add_field(
            name=f"Temperature", value=f"{str(data['temp'])}°F", inline=False
        )
        embed.add_field(
            name=f"Minimum temperature",
            value=f"{str(data['temp_min'])}°F",
            inline=False,
        )
        embed.add_field(
            name=f"Maximum temperature",
            value=f"{str(data['temp_max'])}°F",
            inline=False,
        )
        embed.add_field(
            name=f"Feels like", value=f"{str(data['feels_like'])}°F", inline=False
        )
        return embed

    def error_message(self, location):
        location = location.title()
        return discord.Embed(
            title=f"Error caught!",
            description=f"There was an error finding weather data for {location}.",
            color=EMBED_COLOUR,
        )

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title=f"Error Caught!", color=discord.Colour.red(), description=f"{error}"
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)

    @commands.command(usage="`tp!weather location`")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def Weather(self, ctx, *, location=None):
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        async with aiohttp.ClientSession() as session:
            if location is None:
                await ctx.send("Please send a valid location.")
                return
            params = {
                "q": location.lower(),
                "appid": config.Weather,
                "units": "imperial",
            }
            async with session.get(
                "http://api.openweathermap.org/data/2.5/weather", params=params
            ) as resp:
                # await ctx.reply(type(resp))
                data = await resp.json()
                # URL = f"http://api.openweathermap.org/data/2.5/weather?q={location.lower()}&appid={config.Weather}&units=imperial"
                try:
                    await ctx.send(embed=self.weather_message(data, location))
                except KeyError:
                    await ctx.send(embed=self.error_message(location))

    @commands.command(usage="`tp!vote`")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def Vote(self, ctx):
        """Vote for the bot"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar_url_as(static_format="png"),
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar_url_as(static_format="png"))
        embed.add_field(
            name="Thank You!", value=f"[Click Me]({config.Vote})", inline=True
        )
        embed.add_field(
            name=f"{ctx.bot.user.name} was made with love by: {'' if len(self.config.owners) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=False,
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        try:
            await ctx.reply(embed=embed)
        except Exception as err:
            await ctx.reply(err)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`=ping`")
    async def Ping(self, ctx):
        """Pong!"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        before = time.monotonic()
        before_ws = int(round(self.bot.latency * 1000, 2))
        message = await ctx.reply("Ping ")
        ping = (time.monotonic() - before) * 1000
        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar_url_as(static_format="png"),
        )
        embed.add_field(name="REST", value=f"{int(ping)}ms")
        embed.add_field(name="WS", value=f"{before_ws}ms")
        embed.add_field(
            name="‎",
            value=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            inline=False,
        )
        await message.edit(content="Ping ¯\\_(ツ)_/¯", embed=embed)

    @commands.command(usage="`tp!host`")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def host(self, ctx):
        """Our hosting provider"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(
            color=EMBED_COLOUR,
            title="Hosting Provider",
            timestamp=ctx.message.created_at,
        )
        embed.add_field(
            name="Thank you Ponbus!",
            value=f"A huge thanks to William, the CEO and Systems Administrator of [Ponbus]({config.host}) for allowing us to use your service to fuel AGB and keep it online <3\nPlease go check out [Ponbus]({config.host}) ",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(usage="`tp!todo`")
    @commands.cooldown(rate=2, per=5, type=commands.BucketType.user)
    async def Todo(self, ctx):
        """Stuff to come, future updates i have planned for this bot"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        channel = self.bot.get_channel(784053877040873522)
        message = await channel.fetch_message(784054226439372832)
        await ctx.reply(message.content)

    @commands.command(usage="`tp!credits`", aliases=["thanks"])
    @commands.bot_has_permissions(embed_links=True)
    async def Credits(self, ctx):
        """Just a thank you command to the people who helped me make agb, thank you everyone who helped and who is continually helping me on this project"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(
            color=EMBED_COLOUR,
            timestamp=ctx.message.created_at,
            title="Thank you, so much.",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote})",
        )
        embed.add_field(
            name=f"{ctx.bot.user.name} couldn't be what it is without these people:{'' if len(self.config.thanks) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.thanks]
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(
        aliases=["supportserver", "feedbackserver", "support"], usage="`tp!support`"
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=2, per=5, type=commands.BucketType.user)
    async def Botserver(self, ctx):
        """Get an invite to our support server!"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        if (
            isinstance(ctx.channel, discord.DMChannel)
            or ctx.guild.id != 755722576445046806
        ):
            embed = discord.Embed(
                color=ctx.author.color, timestamp=ctx.message.created_at
            )
            embed.set_author(
                name=ctx.bot.user.name,
                icon_url=ctx.bot.user.avatar_url_as(static_format="png"),
            )
            embed.add_field(
                name="You can join here:", value=f"[Click Here.]({config.Server})"
            )
            return await ctx.reply(embed=embed)
        embed = discord.Embed(color=ctx.author.color, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar_url_as(static_format="png"),
        )
        embed.add_field(
            name=f"{ctx.author.name}, you're already in it.",
            value=f"Regardless, a bot invite is [here]({config.Invite}) \n A server invite is also [here]({config.Server})",
        )
        await ctx.reply(embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["joinme", "botinvite", "kek"], usage="`tp!invite`")
    @commands.bot_has_permissions(embed_links=True)
    async def Invite(self, ctx):
        """Invite me to your server"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar_url_as(static_format="png"),
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar_url_as(static_format="png"))
        embed.add_field(
            name="Bot Invite", value=f"[Invite Me!]({config.Invite})", inline=True
        )
        embed.add_field(
            name=f"Support Server",
            value=f"[Join Our Server!!]({config.Server})",
            inline=True,
        )
        embed.add_field(
            name=f"{ctx.bot.user.name} was made with love by: {'' if len(self.config.owners) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=False,
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    # @commands.cooldown(1, 5, commands.BucketType.user)
    # @commands.command(usage="`tp!source`")
    # async def Source(self, ctx):
    #     """Who Coded This Bot """
    #     embed = discord.Embed(color=EMBED_COLOUR,
    #                           timestamp=ctx.message.created_at)
    #     embed.add_field(name="**The repo is private**",
    #                     value=f"This command really doesn't have a purpose. \nBut its here for when the repo does become public.")
    #     embed.add_field(name="Look at these",
    #                     value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote})", inline=False)
    #     await ctx.reply(embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["info", "stats", "status"], usage="`tp!about`")
    @commands.bot_has_permissions(embed_links=True)
    async def About(self, ctx):
        """About the bot"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        ramUsage = self.process.memory_full_info().rss / 1024 ** 2

        STATCORD = "https://statcord.com/bot/723726581864071178"

        # create the cpu usage embed
        cpu = psutil.cpu_percent()
        cpu_box = default.draw_box(round(cpu), ":blue_square:", ":black_large_square:")
        ramlol = round(ramUsage) // 10
        ram_box = default.draw_box(ramlol, ":blue_square:", ":black_large_square:")

        # get total GB of ram in GB
        total_ram = psutil.virtual_memory().total // 1015 ** 2

        # total_ram = psutil.virtual_memory().total

        GUILD_MODAL = f"""{len(ctx.bot.guilds)} Guilds are visible,\nI can see {round(len(self.bot.users))} users."""

        PERFORMANCE_MODAL = f"""
        `RAM Usage: {ramUsage:.2f}MB / {str(total_ram)[:1] + '.' + str(total_ram)[1:2]}GB ({round(psutil.virtual_memory().percent)}%)`
        {ram_box}
        `CPU Usage: {cpu}%`
        {cpu_box}"""

        BOT_INFO = f"""Latency: {round(self.bot.latency * 1000, 2)}ms\nLoaded CMDs: {len([x.name for x in self.bot.commands])}"""

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=ctx.bot.user.avatar_url)

        embed.add_field(
            name="Programmers",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=True,
        )
        embed.add_field(
            name="Performance Overview", value=PERFORMANCE_MODAL, inline=False
        )

        # embed.add_field(name="DB Connection", value=f"Con {mydb.connection_id}, v{mydb._server_version[0]}", inline=True)
        embed.add_field(
            name="Guild Information",
            value=f"{default.pycode(GUILD_MODAL)}",
            inline=False,
        )

        embed.add_field(
            name="Bot Information", value=f"{default.pycode(BOT_INFO)}", inline=False
        )
        # embed.add_field(name="Total Members",
        # value=f' total users\n\n**DB Connection**\nCon {mydb.connection_id},
        # v{mydb._server_version[0]} | {mydb.charset}', inline=False)
        embed.add_field(
            name=" ⠀",
            value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Statcord]({STATCORD})",
            inline=False,
        )
        embed.set_footer(text="Made with Discord.py")
        await ctx.reply(
            content=f"ℹ About **{ctx.bot.user}** | **{self.config.version}**",
            embed=embed,
        )

    @commands.check(permissions.is_owner)
    @commands.command(aliases=["guilds"], hidden=True)
    async def Servers(self, ctx):
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        await ctx.send(
            "alright, fetching all the servers now, please wait, this can take some time...",
            delete_after=delay,
        )
        filename = random.randint(1, 20)
        f = open(f"{str(filename)}.txt", "a", encoding="utf-8")
        try:
            for guild in self.bot.guilds:
                data = f"Guild Name:{(guild.name)}, Guild ID:{(guild.id)}, Server Members:{(len(guild.members))}, Bots: {len([bot for bot in guild.members if bot.bot])}"
                f.write(data + "\n")
                #        await asyncio.sleep(5)
                continue
        except:
            pass
        f.close()
        try:
            await ctx.send(file=discord.File(f"{str(filename)}.txt"))
        except:
            pass
        os.remove(f"{filename}.txt")

    @commands.cooldown(1, random.randint(3, 5), commands.BucketType.user)
    @commands.command(usage="`tp!say message`")
    @commands.bot_has_permissions(embed_links=True)
    async def Say(self, ctx, *, message):
        """Speak through the bot uwu"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(
            color=EMBED_COLOUR,
            title="AGB",
            url=f"{config.Website}",
            description=f"""{message}""",
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(icon_url=ctx.author.avatar_url, text=ctx.author)
        try:
            await ctx.reply(embed=embed)
        except Exception as err:
            await ctx.reply(err)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!policy`")
    @commands.bot_has_permissions(embed_links=True)
    async def Policy(self, ctx):
        """Privacy Policy"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar_url_as(static_format="png"),
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar_url_as(static_format="png"))
        embed.add_field(
            name="Direct Link To The Privacy Policy ",
            value=f"[Click Here](https://gist.github.com/Motzumoto/2f25e114533a35d86078018fdc2dd283)",
            inline=True,
        )
        embed.add_field(
            name="Backup To The Policy ",
            value=f"[Click Here](https://pastebin.com/J5Zj8U1q)",
            inline=False,
        )
        embed.add_field(
            name=f"Support If You Have More Questions",
            value=f"[Click Here To Join]({config.Server})",
            inline=True,
        )
        embed.add_field(
            name=f"{ctx.bot.user.name} was made with love by: {'' if len(self.config.owners) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=False,
        )
        embed.add_field(
            name="Look at these",
            value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            inline=False,
        )
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=2, per=5, type=commands.BucketType.user)
    @commands.command(usage="`tp!profile`")
    @commands.bot_has_permissions(embed_links=True)
    async def profile(self, ctx, user: Union[discord.Member, discord.User] = None):
        """Show your user profile"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        usr = user or ctx.author

        cursor.execute(f"SELECT * FROM userEco WHERE userId = {usr.id}")
        usereco = cursor.fetchall()

        user_balance = f"${int(usereco[0][1]):,}"
        user_bank = f"${int(usereco[0][2]):,}"
        mydb.commit()

        cursor.execute(f"SELECT * FROM badges WHERE userId = {usr.id}")
        userdb = cursor.fetchall()
        badges = ""
        if userdb[0][1] != "false":
            badges += f"{emojis.dev}"
        if userdb[0][2] != "false":
            badges += f" {emojis.admin}"
        if userdb[0][3] != "false":
            badges += f" {emojis.mod}"
        if userdb[0][4] != "false":
            badges += f" {emojis.partner}"
        if userdb[0][5] != "false":
            badges += f" {emojis.support}"
        if userdb[0][6] != "false":
            badges += f" {emojis.friend}"
        if (
            userdb[0][1] == "false"
            and userdb[0][2] == "false"
            and userdb[0][3] == "false"
            and userdb[0][4] == "false"
            and userdb[0][5] == "false"
            and userdb[0][6] == "false"
        ):
            badges += ""

        mydb.commit()

        cursor.execute(f"SELECT * FROM users WHERE userId = {usr.id}")
        udb = cursor.fetchall()

        usedCommands = ""
        if int(udb[0][1]) <= 0 and usr.id != 101118549958877184:
            usedCommands += "0"
        if int(udb[0][1]) > 0 and usr.id != 101118549958877184:
            usedCommands += f"{udb[0][1]}"
        if usr.id == 101118549958877184:
            usedCommands += f"{udb[0][1]}"

        # **Profile Info**\nBadges: {badges}\n\n
        title = f"{usr.name}#{usr.discriminator}"
        description = f"{badges}\n\n**<:users:770650885705302036> Overview**\n`User Bio`\n - **{udb[0][2]}**\n\n**💰 Economy Info**\n`Balance`: **{user_balance}**\n`Bank`: **{user_bank}**\n\n**📜 Misc Info**\n`Commands Used`: **{usedCommands}**"
        embed = discord.Embed(title=title, color=EMBED_COLOUR, description=description)
        embed.set_thumbnail(url=usr.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=2, per=15, type=commands.BucketType.user)
    @commands.command(usage="`tp!bio new_bio`")
    @commands.bot_has_permissions(embed_links=True)
    async def bio(self, ctx, *, bio=None):
        """Set your profile bio"""
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        if bio is None:
            await ctx.reply("Incorrect usage. Check the usage below:", delete_after=10)
            await ctx.send_help(str(ctx.command))
            ctx.command.reset_cooldown(ctx)
            return

        cursor.execute(f"SELECT * FROM users WHERE userId = {ctx.author.id}")
        cursor.execute(f'UPDATE users SET bio = "{bio}" WHERE userId = {ctx.author.id}')
        mydb.commit()
        embed = discord.Embed(
            title="User Bio",
            color=EMBED_COLOUR,
            description=f"Your bio has been set to: `{bio}`",
        )
        await ctx.reply(embed=embed)

    @commands.command(
        usage="`tp!timestamp <MM/DD/YYYY HH:MM:SS>`",
        help="""
            Displays given time in all Discord timestamp formats.
            Example: 12/22/2005 02:20:00
            You don't need to specify time. It will automatically round it to midnight.
            """,
    )
    async def timestamp(self, ctx, date, time=None):
        if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
            await ctx.send(":x: This command has been disabled!")
            return

        if time is None:
            time = "00:00:00"

        datetime_object = datetime.strptime(f"{date} {time}", "%m/%d/%Y %H:%M:%S")
        uts = str(datetime_object.timestamp())[:-2]
        await ctx.reply(
            embed=discord.Embed(
                title="Here's the timestamp you asked for",
                color=EMBED_COLOUR,
                description=f"""
                Short Time: <t:{uts}:t> | \\<t:{uts}:t>
                Long Time: <t:{uts}:T> | \\<t:{uts}:T>
                Short Date: <t:{uts}:d> | \\<t:{uts}:d>
                Long Date: <t:{uts}:D> | \\<t:{uts}:D>
                Short Date/Time: <t:{uts}:f> | \\<t:{uts}:f>
                Long Date/Time: <t:{uts}:F> | \\<t:{uts}:F>
                Relative Time: <t:{uts}:R> | \\<t:{uts}:R>
                """,
            )
        )

    @timestamp.error
    async def timestamp_error(self, ctx, error):
        if isinstance(error, commands.TooManyArguments):
            await self.create_embed(ctx, error)
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await self.create_embed(ctx, error)
            return
        elif isinstance(error, commands.CommandInvokeError):
            await self.create_embed(ctx, error)
            return


def setup(bot):
    bot.add_cog(Information(bot))
