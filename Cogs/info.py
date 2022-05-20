import datetime
import aiohttp
import json
import os
import pathlib
import speedtest
from typing import List, Union

import discord
import psutil
import requests
from discord.ext import commands
from index import (
    EMBED_COLOUR,
    config,
    cursor_n,
    emojis,
    mydb_n,
)
from Manager.commandManager import cmd
from utils import default, permissions, imports


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
        self.config = imports.get("config.json")
        self.lunar_headers = {f"{config.lunarapi.header}": f"{config.lunarapi.token}"}
        # self.thanks = default.get("thanks.json")
        # self.blist_api = blist.Blist(bot, token=self.config.blist)
        self.process = psutil.Process(os.getpid())

    async def cog_unload(self):
        self.process.stop()

    def parse_weather_data(self, data):
        data = data["main"]
        del data["humidity"]
        del data["pressure"]
        return data

    def weather_message(self, data, location):
        location = location.title()
        embed = discord.Embed(
            title=f"{location} Weather",
            description=f"Here is the weather data for {location}.",
            color=EMBED_COLOUR,
        )
        embed.add_field(
            name=f"Temperature", value=f"{str(data['temp'])}° F", inline=False
        )
        embed.add_field(
            name=f"Minimum temperature",
            value=f"{str(data['temp_min'])}° F",
            inline=False,
        )
        embed.add_field(
            name=f"Maximum temperature",
            value=f"{str(data['temp_max'])}° F",
            inline=False,
        )
        embed.add_field(
            name=f"Feels like", value=f"{str(data['feels_like'])}° F", inline=False
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
            title=f"Error Caught!", color=0xFF0000, description=f"{error}"
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        await ctx.send(
            embed=embed,
        )

    class MemberConverter(commands.MemberConverter):
        async def convert(self, ctx, argument):
            try:
                return await super().convert(ctx, argument)
            except commands.BadArgument:
                members = [
                    member
                    for member in ctx.guild.members
                    if member.display_name.lower().startswith(argument.lower())
                ]
                if len(members) == 1:
                    return members[0]
                else:
                    raise commands.BadArgument(
                        f"{len(members)} members found, please be more specific."
                    )

    @staticmethod
    def generate_embed(step: int, results_dict):
        """Generate the embed."""
        measuring = ":mag: Measuring..."
        waiting = ":hourglass: Waiting..."

        color = discord.Color.red()
        title = "Measuring internet speed..."
        message_ping = measuring
        message_down = waiting
        message_up = waiting
        if step > 0:
            message_ping = f"**{results_dict['ping']}** ms"
            message_down = measuring
        if step > 1:
            message_down = f"**{results_dict['download'] / 1_000_000:.2f}** mbps"
            message_up = measuring
        if step > 2:
            message_up = f"**{results_dict['upload'] / 1_000_000:.2f}** mbps"
            title = "NetSpeed Results"
            color = discord.Color.green()
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Ping", value=message_ping)
        embed.add_field(name="Download", value=message_down)
        embed.add_field(name="Upload", value=message_up)
        return embed

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def weather(self, ctx, *, location: str = None):
        """Get weather data for a location
        You can use your zip code or your city name.
        Ex; `tp!weather City / Zip Code` or `tp!weather City,Town`"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if location == None:
            await ctx.send("Please send a valid location.")
            return

        URL = f"http://api.openweathermap.org/data/2.5/weather?q={location.lower()}&appid={config.Weather}&units=imperial"
        try:
            data = json.loads(requests.get(URL).content)
            data = self.parse_weather_data(data)
            await ctx.send(embed=self.weather_message(data, location))
        except KeyError:
            await ctx.send(embed=self.error_message(location))

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def f2c(self, ctx, *, temp: str, ephemeral: bool = False):
        """Convert Fahrenheit to Celsius

        Args:
            temp (str): The temperature to convert
            ephemeral (optional): make the command visible to you or others.. Defaults to False.
        """

        if temp is None:
            await ctx.send("Please send a valid temperature.", ephemeral=True)
            return

        temp = float(temp)
        cel = (temp - 32) * (5 / 9)
        await ctx.send(f"{temp}°F is {round(cel, 2)}°C", ephemeral=ephemeral)

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def c2f(self, ctx, *, temp: str, ephemeral: bool = False):
        """Convert Celsius to Fahrenheit

        Args:
            temp (str): the temperature to convert
            ephemeral (optional): make the command visible to you or others.. Defaults to False.
        """

        if temp is None:
            await ctx.send("Please send a valid temperature.", ephemeral=True)
            return

        temp = float(temp)
        fah = (temp * (9 / 5)) + 32
        await ctx.send(f"{temp}°C is {round(fah, 2)}°F", ephemeral=ephemeral)

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def vote(self, ctx):
        """Vote for the bot"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar,
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar)
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
        embed.set_thumbnail(url=ctx.author.avatar)
        try:
            await ctx.send(
                embed=embed,
            )
        except Exception as err:
            await ctx.send(err)

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def ping(self, ctx, ephemeral: bool = False):
        """Ping the bot

        Args:
            ephemeral (optional): make the command visible to you or others. Defaults to False.
        """
        embed = discord.Embed(color=EMBED_COLOUR)
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar,
        )
        embed.add_field(
            name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True
        )
        embed.set_thumbnail(url=ctx.author.avatar)
        await ctx.send(embed=embed, ephemeral=ephemeral)

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def invite(self, ctx, ephemeral: bool = False):
        """Get an invite to the bot

        Args:
            ephemeral (optional): make the command visible to you or others.. Defaults to False.
        """

        embed = discord.Embed(color=EMBED_COLOUR)
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar,
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        embed.add_field(
            name="Bot Invite", value=f"[Invite Me!]({config.Invite})", inline=True
        )
        embed.add_field(
            name=f"Support Server",
            value=f"[Join Our Server!!]({config.Server})",
            inline=True,
        )
        embed.add_field(
            name=f"{self.bot.user.name} was made with love by: {'' if len(self.config.owners) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=False,
        )
        embed.set_thumbnail(url=ctx.author.avatar)
        await ctx.send(embed=embed, ephemeral=ephemeral)

    # @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    # @commands.hybrid_command(usage="`tp!source`")
    # async def Source(self, ctx):
    #     """Who Coded This Bot """
    #     embed = discord.Embed(color=EMBED_COLOUR,
    #                           timestamp=ctx.message.created_at)
    #     embed.add_field(name="**The repo is private**",
    #                     value=f"This command really doesn't have a purpose. \nBut its here for when the repo does become public.")
    #     embed.add_field(name="Look at these",
    #                     value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})", inline=False)
    #     await ctx.send(content="This command will be converted to slash commands before April 30th.", embed=embed)

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def stats(self, ctx, ephemeral: bool = False):
        """Get some information about the bot"""
        async with ctx.channel.typing():
            fetching = await ctx.send("Fetching stats...", ephemeral=ephemeral)
            discord_version = discord.__version__
            amount_of_app_cmds = await self.bot.tree.fetch_commands()
            chunked = []
            for guild in self.bot.guilds:
                if guild.chunked:
                    chunked.append(guild)
            ramUsage = self.process.memory_full_info().rss / 1024**2
            intervals = (
                ("w", 604800),  # 60 * 60 * 24 * 7
                ("d", 86400),  # 60 * 60 * 24
                ("h", 3600),  # 60 * 60
                ("m", 60),
                ("s", 1),
            )

            async def get_internet_speed():
                await fetching.edit(content="Fetching internet speed...")
                s = speedtest.Speedtest(secure=True)
                s.get_servers()
                s.get_best_server()
                s.download()
                s.upload()
                await fetching.edit(content="Fetching internet speed...")
                return f"Download: {s.results.download / 1024**2:.2f} MBs\nUpload: {s.results.upload / 1024**2:.2f} MBs"

            def display_time(seconds, granularity=2):
                result = []

                for name, count in intervals:
                    value = seconds // count
                    if value:
                        seconds -= value * count
                        if value == 1:
                            name = name.rstrip("s")
                        result.append("{}{}".format(value, name))
                return " ".join(result[:granularity])

            async def lunar_api_stats(self):
                await fetching.edit(content="Fetching Lunar API stats...")
                async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                    try:
                        async with s.get(f"https://lunardev.group/api/ping") as r:
                            j = await r.json()
                            seconds = j["uptime"]

                            # str(await lunar_api_stats(self)).partition(".")

                            if r.status == 200:
                                return display_time(
                                    int(str(seconds).partition(".")[0]), 4
                                )
                            elif r.status == 503:
                                return "❌ API Error"
                            else:
                                return "❌ API Error"
                    except Exception:
                        return "❌ API Error"

            async def lunar_api_cores(self):
                await fetching.edit(content="Fetching Lunar system cores...")
                async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                    try:
                        async with s.get(f"https://lunardev.group/api/ping") as r:
                            j = await r.json()
                            cores = j["system"]["cores"]

                            # str(await lunar_api_stats(self)).partition(".")

                            if r.status == 200:
                                return cores
                            elif r.status == 503:
                                return "❌ API Error"
                            else:
                                return "❌ API Error"
                    except Exception:
                        return "❌ API Error"

            async def lunar_api_files(self):
                await fetching.edit(content="Fetching Lunar API files...")
                async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                    try:
                        async with s.get(f"https://lunardev.group/api/ping") as r:
                            j = await r.json()
                            files = j["images"]["total"]

                            # str(await lunar_api_stats(self)).partition(".")

                            if r.status == 200:
                                return f"{int(files):,}"
                            elif r.status == 503:
                                return "❌ API Error"
                            else:
                                return "❌ API Error"
                    except Exception:
                        return "❌ API Error"

            async def lunar_system_uptime(self):
                await fetching.edit(content="Fetching Lunar system uptime...")
                async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                    try:
                        async with s.get(f"https://lunardev.group/api/ping") as r:
                            j = await r.json()
                            uptime = j["system"]["uptime"]

                            # str(await lunar_api_stats(self)).partition(".")

                            if r.status == 200:
                                return display_time(
                                    int(str(uptime).partition(".")[0]), 4
                                )
                            elif r.status == 503:
                                return "❌ API Error"
                            else:
                                return "❌ API Error"
                    except Exception:
                        return "❌ API Error"

            async def line_count(self):
                total = 0
                file_amount = 0
                ENV = "env"

                for path, _, files in os.walk("."):
                    for name in files:
                        file_dir = str(pathlib.PurePath(path, name))
                        # ignore env folder and not python files.
                        if not name.endswith(".py") or ENV in file_dir:
                            continue
                        if "__pycache__" in file_dir:
                            continue
                        if ".git" in file_dir:
                            continue
                        if ".local" in file_dir:
                            continue
                        if ".config" in file_dir:
                            continue
                        if "?" in file_dir:
                            continue
                        if ".cache" in file_dir:
                            continue
                        file_amount += 1
                        with open(file_dir, "r", encoding="utf-8") as file:
                            for line in file:
                                if not line.strip().startswith("#") or not line.strip():
                                    total += 1
                return f"{total:,} lines, {file_amount:,} files"

            # create the cpu usage embed
            cpu = psutil.cpu_percent()
            cpu_box = default.draw_box(
                round(cpu), ":blue_square:", ":black_large_square:"
            )
            ramlol = round(ramUsage) // 10
            ram_box = default.draw_box(ramlol, ":blue_square:", ":black_large_square:")
            GUILD_MODAL = f"""{len(self.bot.guilds)} Guilds are seen,\n{default.commify(len(self.bot.users))} users."""
            PERFORMANCE_MODAL = f"""
            `RAM Usage: {ramUsage:.2f}MB / 1GB scale`
            {ram_box}
            `CPU Usage: {cpu}%`
            {cpu_box}"""
            API_UPTIME = await lunar_api_stats(self)
            BOT_INFO = f"""Latency: {round(self.bot.latency * 1000, 2)}ms\nLoaded CMDs: {len([x.name for x in self.bot.commands])} and {len(amount_of_app_cmds)} slash commands\nMade: <t:1592620263:R>\n{await line_count(self)}\nUptime: {default.uptime(start_time=self.bot.launch_time)}"""
            API_INFO = f"""API Uptime: {API_UPTIME}\nCPU Cores: {await lunar_api_cores(self)}\nTotal Images: {await lunar_api_files(self)}"""
            SYS_INFO = f"""System Uptime: {await lunar_system_uptime(self)}\nCPU Cores: {await lunar_api_cores(self)}\n{await get_internet_speed()}"""

            embed = discord.Embed(
                color=EMBED_COLOUR,
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            )
            embed.set_thumbnail(url=self.bot.user.avatar)
            embed.add_field(
                name="Performance Overview", value=PERFORMANCE_MODAL, inline=False
            )
            embed.add_field(
                name="Guild Information",
                value=GUILD_MODAL,
                inline=False,
            )
            if len(chunked) == len(self.bot.guilds):
                embed.add_field(
                    name="\u200b", value=f"**All servers are cached!**", inline=False
                )
            else:
                embed.add_field(
                    name="\u200b",
                    value=f"**{len(chunked)}** / **{len(self.bot.guilds)}** servers are cached.",
                )
            embed.add_field(name="Bot Information", value=BOT_INFO, inline=False)
            embed.add_field(name="API Information", value=API_INFO, inline=False)
            embed.add_field(name="System Information", value=SYS_INFO, inline=False)
            embed.set_image(
                url="https://media.discordapp.net/attachments/940897271120273428/954507474394808451/group.gif"
            )
            embed.set_footer(
                text=f"Made with ❤️ by the Lunar Development team.\nLibrary used: Discord.py{discord_version}"
            )
            await fetching.edit(content="Almost done...")
            await fetching.edit(
                content=f"Stats about **{self.bot.user}** | **{self.config.version}**",
                embed=embed,
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    async def say(self, ctx, *, message: str):
        """Speak through the bot uwu"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        # if message.
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send(message)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def policy(self, ctx):
        """Privacy Policy"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar,
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar)
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
            value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            inline=False,
        )
        await ctx.send(
            embed=embed,
        )

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def profile(self, ctx, user: Union[MemberConverter, discord.User] = None):
        """Show your user profile"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        usr = user or ctx.author

        msg = await ctx.send("Fetching...")

        cursor_n.execute(f"SELECT * FROM public.usereco WHERE \"userid\" = '{usr.id}'")
        usereco = cursor_n.fetchall()

        try:
            user_balance = f"${int(usereco[0][1]):,}"
        except Exception:
            user_balance = "$0"
        try:
            user_bank = f"${int(usereco[0][2]):,}"
        except Exception:
            user_bank = "$0"
        mydb_n.commit()
        try:
            cursor_n.execute(f"SELECT * FROM public.badges WHERE userid = '{usr.id}'")
            userdb = cursor_n.fetchall()
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
        except Exception:
            badges += ""

        mydb_n.commit()

        cursor_n.execute(f"SELECT * FROM public.users WHERE userid = '{usr.id}'")
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"

        # **Profile Info**\nBadges: {badges}\n\n
        title = f"{usr.name}#{usr.discriminator}"
        description = f"""{badges}\n\n**💰 Economy Info**
		`Balance`: **{user_balance}**
		`Bank`: **{user_bank}**
		
		**📜 Misc Info**
		`Commands Used`: **{usedCommands}**
		
		**<:users:770650885705302036> Overview**
		`User Bio`\n{udb[0][2]}"""

        embed = discord.Embed(title=title, color=EMBED_COLOUR, description=description)
        embed.set_thumbnail(url=usr.avatar)
        await msg.edit(content="", embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bio(self, ctx, *, bio: str = None):
        """Set your profile bio"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if bio is None:
            await ctx.send("Incorrect usage. Check the usage below:", delete_after=10)
            await ctx.send_help(str(ctx.command))

            return

        cursor_n.execute(f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'")
        cursor_n.execute(
            f"UPDATE public.users SET bio = '{bio}' WHERE userid = '{ctx.author.id}'"
        )
        mydb_n.commit()
        embed = discord.Embed(
            title="User Bio",
            color=EMBED_COLOUR,
            description=f"Your bio has been set to: `{bio}`",
        )
        await ctx.send(
            embed=embed,
        )

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def timestamp(self, ctx, date: str, time: str = None):
        """
        Displays given time in all Discord timestamp formats.
        Example: 12/22/2005 02:20:00
        You don't need to specify time. It will automatically round it to midnight.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if time is None:
            time = "00:00:00"

        datetime_object = datetime.datetime.strptime(
            f"{date} {time}", "%m/%d/%Y %H:%M:%S"
        )
        uts = str(datetime_object.timestamp())[:-2]
        await ctx.send(
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
            ),
        )


async def setup(bot):
    await bot.add_cog(Information(bot))
