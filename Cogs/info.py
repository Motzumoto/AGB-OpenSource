from __future__ import annotations
import contextlib

import datetime
import json
import os
import pathlib
import random
from typing import TYPE_CHECKING, Annotated, List, Optional, Union

import aiohttp
import discord
import psutil
import requests
from discord.ext import commands
from discord.ui import Button, View
from index import colors, config
from sentry_sdk import capture_exception
from utils import default, imports, permissions


def list_items_in_english(l: List[str], oxford_comma: bool = True) -> str:
    """
    Produce a list of the items formatted as they would be in an English sentence.
    So one item returns just the item, passing two items returns "item1 and item2" and
    three returns "item1, item2, and item3" with an optional Oxford comma.
    """
    return ", ".join(
        l[:-2] + [((oxford_comma and len(l) != 2) * "," + " and ").join(l[-2:])]
    )


if TYPE_CHECKING:
    from index import Bot


class MemberConverter(commands.MemberConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except commands.BadArgument as e:
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
                ) from e


class Information(commands.Cog, name="info"):
    """Info commands for info related things"""

    def __init__(self, bot: Bot):
        """Info commands for info related things"""
        self.bot: Bot = bot
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
            color=colors.prim,
        )
        embed.add_field(
            name="Temperature", value=f"{str(data['temp'])}° F", inline=False
        )
        embed.add_field(
            name="Minimum temperature",
            value=f"{str(data['temp_min'])}° F",
            inline=False,
        )
        embed.add_field(
            name="Maximum temperature",
            value=f"{str(data['temp_max'])}° F",
            inline=False,
        )
        embed.add_field(
            name="Feels like", value=f"{str(data['feels_like'])}° F", inline=False
        )

        return embed

    def error_message(self, location):
        location = location.title()
        return discord.Embed(
            title="Error caught!",
            description=f"There was an error finding weather data for {location}.",
            color=colors.prim,
        )

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title="Error Caught!", color=0xFF0000, description=f"{error}"
        )

        embed.set_thumbnail(url=self.bot.user.avatar)
        await ctx.send(
            embed=embed,
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
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def weather(self, ctx, *, location: str = None):
        """Get weather data for a location
        You can use your zip code or your city name.
        Ex; `tp!weather City / Zip Code` or `tp!weather City,Town`"""
        if location is None:
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
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def f2c(self, ctx, *, temp: str, ephemeral: bool = False):
        """Convert Fahrenheit to Celsius

        Args:
            temp (str): The temperature to convert
            ephemeral (optional): make the command visible to you or others. Defaults to False.
        """

        if temp is None:
            await ctx.send("Please send a valid temperature.", ephemeral=True)
            return

        temp = float(temp)
        cel = (temp - 32) * (5 / 9)
        await ctx.send(f"{temp}°F is {round(cel, 2)}°C", ephemeral=ephemeral)

    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def c2f(self, ctx, *, temp: str, ephemeral: bool = False):
        """Convert Celsius to Fahrenheit

        Args:
            temp (str): the temperature to convert
            ephemeral (optional): make the command visible to you or others. Defaults to False.
        """

        if temp is None:
            await ctx.send("Please send a valid temperature.", ephemeral=True)
            return

        temp = float(temp)
        fah = (temp * (9 / 5)) + 32
        await ctx.send(f"{temp}°C is {round(fah, 2)}°F", ephemeral=ephemeral)

    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def vote(self, ctx):
        """Vote for the bot"""
        embed = discord.Embed(color=colors.prim, timestamp=ctx.message.created_at)
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
            capture_exception(err)
            await ctx.send(err)

    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def ping(self, ctx, ephemeral: bool = False):
        """Ping the bot

        Args:
            ephemeral (optional): make the command visible to you or others. Defaults to False.
        """
        embed = discord.Embed(color=colors.prim)
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar,
        )
        try:
            embed.add_field(
                name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True
            )
        except OverflowError:
            embed.add_field(
                name="Ping", value="Ping cannot be calculated right now.", inline=True
            )

        embed.set_thumbnail(url=ctx.author.avatar)
        await ctx.send(embed=embed, ephemeral=ephemeral)

    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def invite(self, ctx, ephemeral: bool = False):
        """Get an invite to the bot"""

        invite_btn = Button(
            label="Click here to invite me!",
            style=discord.ButtonStyle.link,
            url=config.Invite,
        )
        support_btn = Button(
            label="Support server", style=discord.ButtonStyle.link, url=config.Server
        )
        view = View()
        view.add_item(invite_btn)
        view.add_item(support_btn)
        await ctx.send(view=view, ephemeral=ephemeral)

    # @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    # @commands.hybrid_command(usage="`tp!source`")
    # async def Source(self, ctx):
    #     """Who Coded This Bot """
    #     embed = discord.Embed(color=colors.prim,
    #                           timestamp=ctx.message.created_at)
    #     embed.add_field(name="**The repo is private**",
    #                     value=f"This command really doesn't have a purpose. \nBut its here for when the repo does become public.")
    #     embed.add_field(name="Look at these",
    #                     value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})", inline=False)
    #     await ctx.send(content="This command will be converted to slash commands before April 30th.", embed=embed)

    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def stats(self, ctx, ephemeral: bool = False):
        """Get some information about the bot"""
        await ctx.channel.typing()
        fetching = await ctx.send("Fetching stats...", ephemeral=ephemeral)
        num = 0
        for guild in self.bot.guilds:
            for channel in guild.channels:
                num += 1
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

        def display_time(seconds, granularity=2):
            result = []

            for name, count in intervals:
                if value := seconds // count:
                    seconds -= value * count
                    if value == 1:
                        name = name.rstrip("s")
                    result.append(f"{value}{name}")
            return " ".join(result[:granularity])

        async def lunar_api_stats(self):
            await ctx.channel.typing()
            await fetching.edit(content="Fetching Lunar API stats...")
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get("https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        seconds = j["uptime"]

                        # str(await lunar_api_stats(self)).partition(".")

                        if r.status == 200:
                            return display_time(int(str(seconds).partition(".")[0]), 4)
                        else:
                            return "❌ API Error"
                except Exception as e:
                    capture_exception(e)
                    return "❌ API Error"

        async def lunar_api_cores(self):
            await ctx.channel.typing()
            await fetching.edit(content="Fetching Lunar system cores...")
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get("https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        cores = j["system"]["cores"]

                        # str(await lunar_api_stats(self)).partition(".")

                        return cores if r.status == 200 else "❌ API Error"
                except Exception as e:
                    capture_exception(e)
                    return "❌ API Error"

        async def lunar_api_files(self):
            await ctx.channel.typing()
            await fetching.edit(content="Fetching Lunar API files...")
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get("https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        files = j["images"]["total"]

                        # str(await lunar_api_stats(self)).partition(".")

                        return f"{int(files):,}" if r.status == 200 else "❌ API Error"
                except Exception as e:
                    capture_exception(e)
                    return "❌ API Error"

        async def lunar_system_uptime(self):
            await ctx.channel.typing()
            await fetching.edit(content="Fetching Lunar system uptime...")
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get("https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        uptime = j["system"]["uptime"]

                        # str(await lunar_api_stats(self)).partition(".")

                        if r.status == 200:
                            return display_time(int(str(uptime).partition(".")[0]), 4)
                        else:
                            return "❌ API Error"
                except Exception as e:
                    capture_exception(e)
                    return "❌ API Error"

        async def line_count(self):
            await ctx.channel.typing()
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

        if len(chunked) == len(self.bot.guilds):
            all_chunked = "**All servers are cached!**"
        else:
            all_chunked = (
                f"**{len(chunked)}** / **{len(self.bot.guilds)}** servers are cached"
            )

        cpu = psutil.cpu_percent()
        cpu_box = default.draw_box(round(cpu), ":blue_square:", ":black_large_square:")
        ramlol = round(ramUsage) // 10
        ram_box = default.draw_box(ramlol, ":blue_square:", ":black_large_square:")
        GUILD_MODAL = f"""{len(self.bot.guilds)} Guilds are seen,\n{default.commify(num)} channels,\nand {default.commify(len(self.bot.users))} users."""
        PERFORMANCE_MODAL = f"""
        `RAM Usage: {ramUsage:.2f}MB / 1GB scale`
        {ram_box}
        `CPU Usage: {cpu}%`
        {cpu_box}"""
        API_UPTIME = await lunar_api_stats(self)
        BOT_INFO = f"""{all_chunked}\nLatency: {round(self.bot.latency * 1000, 2)}ms\nLoaded CMDs: {len([x.name for x in self.bot.commands])} and {len(amount_of_app_cmds)} slash commands\nMade: <t:1592620263:R>\n{await line_count(self)}\nUptime: {default.uptime(start_time=self.bot.launch_time)}"""
        API_INFO = f"""API Uptime: {API_UPTIME}\nCPU Cores: {await lunar_api_cores(self)}\nTotal Images: {await lunar_api_files(self)}"""
        SYS_INFO = f"""System Uptime: {await lunar_system_uptime(self)}\nCPU Cores: {await lunar_api_cores(self)}"""

        embed = discord.Embed(
            color=colors.prim,
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
    @commands.command()
    @commands.check(permissions.is_owner)
    async def remindme(self, ctx, time: str, *, reminder: str):
        valid_time_units = ("s", "m", "h", "d", "w")
        if not time.endswith(valid_time_units):
            await ctx.send("Invalid time unit! Please use s, m, h, d, or w.")
            return
        if time.endswith("s"):
            time = int(time[:-1])
        elif time.endswith("m"):
            time = int(time[:-1]) * 60
        elif time.endswith("h"):
            time = int(time[:-1]) * 3600
        elif time.endswith("d"):
            time = int(time[:-1]) * 86400
        elif time.endswith("w"):
            time = int(time[:-1]) * 604800
        else:
            time = int(time)
        await self.bot.db.add_reminder(ctx.author.id, str(time), reminder)
        if time > 86400:
            await ctx.send(
                f"Coming back to you in {time // 86400} days.",
            )
        elif time > 3600:
            await ctx.send(
                f"Coming back to you in {time // 3600} hours.",
            )
        elif time > 60:
            await ctx.send(
                f"Coming back to you in {time // 60} minutes.",
            )
        else:
            await ctx.send(
                f"Coming back to you in {time} seconds.",
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @commands.check(permissions.is_owner)
    async def reminders(self, ctx):
        bruh = await self.bot.db.fetch_reminder(ctx.author.id)
        await ctx.send(bruh)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    async def say(self, ctx, *, message: str):
        """Speak through the bot uwu"""
        # if message.
        with contextlib.suppress(Exception):
            await ctx.message.delete()
        await ctx.send(message)
        if random.randint(1, 5) == 1:
            await ctx.send("You can also say an embed with `/embed_say`!")

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    async def embed_say(
        self,
        ctx,
        *,
        message: str,
        description: str = None,
        title: str = None,
        footer: str = None,
        image: str = None,
    ):
        """Speak through the bot with an embed. MUST BE USED AS A SLASH COMMAND TO EDIT FOOTER/TITLE/IMAGE"""
        with contextlib.suppress(Exception):
            await ctx.message.delete()

        title_no_edit = "Lunar Development Echo"
        if footer is None:
            footer = f"Sent at {ctx.message.created_at.strftime('%H:%M:%S')}"
        if image is None:
            image = "https://cdn.discordapp.com/icons/755722576445046806/822bafdc8285f1729af731b4d320c5e5.png?size=1024"
        if description is None:
            description = "No Text Provided :("
        embed = discord.Embed(
            title=title_no_edit, description=description, color=colors.prim
        )
        embed.add_field(name=title, value=message)
        embed.set_thumbnail(url=image)
        embed.set_footer(text=footer)
        await ctx.send(embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def policy(self, ctx):
        """Privacy Policy"""
        embed = discord.Embed(color=colors.prim, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar,
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar)
        embed.add_field(
            name="Direct Link To The Privacy Policy ",
            value="[Click Here](https://gist.github.com/Motzumoto/2f25e114533a35d86078018fdc2dd283)",
            inline=True,
        )

        embed.add_field(
            name="Backup To The Policy ",
            value="[Click Here](https://pastebin.com/J5Zj8U1q)",
            inline=False,
        )

        embed.add_field(
            name="Support If You Have More Questions",
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
    async def profile(
        self,
        ctx: commands.Context,
        user: Optional[
            Union[Annotated[discord.Member, MemberConverter], discord.User]
        ] = None,
    ):
        """Show your user profile"""
        user = user or ctx.author

        msg = await ctx.send("Fetching...")

        usereco = self.bot.db.get_economy_user(
            user.id
        ) or await self.bot.db.fetch_economy_user(user.id)
        if not usereco:
            await msg.edit(content=f"~~{msg.content}~~ User has no profile.")
            return

        user_balance = f"${usereco.balance:,}"
        user_bank = f"${usereco.bank:,}"

        cached_badges = self.bot.db._badges
        fetched_badges = (
            list(cached_badges.values())
            if cached_badges
            else await self.bot.db.fetch_badges()
        )

        badges_list = [
            badge for badge in fetched_badges if badge.has_badge(user.id) is True
        ]
        badges = " ".join(b.name for b in badges_list)

        db_user = self.bot.db.get_user(user.id) or await self.bot.db.fetch_user(user.id)
        if db_user:
            used_commands = db_user.used_commands + 1
            bio = db_user.bio
        else:
            used_commands = 1
            bio = None

        # **Profile Info**\nBadges: {badges}\n\n
        description = f"""{badges}\n\n**💰 Economy Info**
		`Balance`: **{user_balance}**
		`Bank`: **{user_bank}**
		
		**📜 Misc Info**
		`Commands Used`: **{used_commands}**
		
		**<:users:770650885705302036> Overview**
		`User Bio`\n{bio}"""

        embed = discord.Embed(
            title=str(user), color=colors.prim, description=description
        )
        embed.set_thumbnail(url=user.display_avatar)
        await msg.edit(content=None, embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bio(self, ctx, *, bio: Optional[str] = None):
        """Set your profile bio"""
        if bio is None:
            await ctx.send("Incorrect usage. Check the usage below:", delete_after=10)
            await ctx.send_help(str(ctx.command))

            return

        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        if not db_user:
            await ctx.send("You have no profile..?")
            return

        db_user = await db_user.modify(bio=bio)
        embed = discord.Embed(
            title="User Bio",
            color=colors.prim,
            description=f"Your bio has been set to: `{db_user.bio}`",
        )
        await ctx.send(
            embed=embed,
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def timestamp(self, ctx, date: str, time: str = None):
        """
        Displays given time in all Discord timestamp formats.
        Example: 12/22/2005 02:20:00
        You don't need to specify time. It will automatically round it to midnight.
        """
        if time is None:
            time = "00:00:00"

        datetime_object = datetime.datetime.strptime(
            f"{date} {time}", "%m/%d/%Y %H:%M:%S"
        )
        uts = str(datetime_object.timestamp())[:-2]
        await ctx.send(
            embed=discord.Embed(
                title="Here's the timestamp you asked for",
                color=colors.prim,
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


async def setup(bot: Bot) -> None:
    await bot.add_cog(Information(bot))
