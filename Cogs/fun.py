import asyncio
import datetime
import functools
import heapq
import io
import random
import secrets
import unicodedata
from io import BytesIO
from typing import List, Optional, Tuple, Union

import aiohttp
import asyncpraw
import discord
import matplotlib
import matplotlib.pyplot as plt
import nekos
from discord.ext import commands
from index import (
    CHAT_API_KEY,
    BID,
    EMBED_COLOUR,
    Website,
    config,
    logger,
    cursor_n,
    mydb_n,
)
from Manager.commandManager import cmd
from utils import default, http, permissions, imports
from utils.common_filters import filter_mass_mentions
from utils.default import log
from utils.checks import voter_only

try:
    import cairosvg

    svg_convert = "cairo"
except Exception:
    pass


matplotlib.use("agg")

plt.switch_backend("agg")


class Fun(commands.Cog, name="fun"):
    """Fun / Game commands"""

    def __init__(self, bot):
        self.bot = bot
        self.channels = {}
        global Utils
        Utils = self.bot.get_cog("Utils")
        self.session = aiohttp.ClientSession()
        if svg_convert == "cairo":
            log("enlarge: Using CairoSVG for svg conversion.")
        elif svg_convert == "wand":
            log("enlarge: Using wand for svg conversion.")
        else:
            logger.error(
                "enlarge: Failed to import svg converter. Standard emoji will be limited to 72x72 png."
            )

        self.config = imports.get("config.json")
        self.ttt_games = {}

        self.params = {
            "mode": "random",
        }

        self.reddit = asyncpraw.Reddit(
            client_id=self.config.rID,
            client_secret=self.config.rSecret,
            password=self.config.rPass,
            user_agent="asyncprawpython",
            username=self.config.rUser,
        )

        # self.alex_api = alexflipnote.Client(self.config.flipnote)
        # self.bot.alex_api = self.alex_api

        self.ballresponse = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "send hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My send is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
            "Up to you, but I guess.",
            "No.",
            "Absolutely not.",
            "Nahh.",
            "Nope.",
            "No way.",
            "Not a chance.",
            "Not in a million years.",
            "Probably",
            "Maybe",
            "Maybe not",
            "Not sure",
            "Ask again later",
            "¯\_(ツ)_/¯",
        ]

    async def cog_unload(self):
        self.session.stop()
        self.reddit.stop()
        self.ttt_games.stop()
        self.params.stop()

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def cap_change(self, message: str) -> str:
        result = ""
        for char in message:
            value = random.choice([True, False])
            if value:
                result += char.upper()
            else:
                result += char.lower()
        return result

    async def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    def get_actors(self, bot, offender, target):
        return (
            {"id": bot.id, "nick": bot.display_name, "formatted": bot.mention},
            {
                "id": offender.id,
                "nick": offender.display_name,
                "formatted": "<@{}>".format(offender.id),
            },
            {"id": target.id, "nick": target.display_name, "formatted": target.mention},
        )

    async def fetch_channel_history(
        self,
        channel: discord.TextChannel,
        animation_message: discord.Message,
        messages: int,
    ) -> List[discord.Message]:
        """Fetch the history of a channel while displaying an status message with it"""
        animation_message_deleted = False
        history = []
        history_counter = 0
        async for msg in channel.history(limit=messages):
            # check if the msg author is a bot
            if msg.author.bot:
                continue
            history.append(msg)
            history_counter += 1
            if history_counter % 250 == 0:
                new_embed = discord.Embed(
                    title=f"Fetching messages from #{channel.name}",
                    description=f"This might take a while...\n{history_counter}/{messages} messages gathered",
                    colour=EMBED_COLOUR,
                )

                if channel.permissions_for(channel.guild.me).send_messages:
                    await channel.typing()
                if animation_message_deleted is False:
                    try:
                        await animation_message.edit(embed=new_embed)
                    except discord.NotFound:
                        animation_message_deleted = True
        return history

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
    def calculate_member_perc(history: List[discord.Message]) -> dict:
        """Calculate the member count from the message history"""
        msg_data = {"total_count": 0, "users": {}}
        for msg in history:
            # Name formatting
            if len(msg.author.display_name) >= 20:
                short_name = "{}...".format(msg.author.display_name[:20]).replace(
                    "$", "\\$"
                )
            else:
                short_name = (
                    msg.author.display_name.replace("$", "\\$")
                    .replace("_", "\\_ ")
                    .replace("*", "\\*")
                )
            whole_name = "{}#{}".format(short_name, msg.author.discriminator)
            if msg.author.bot:
                pass
            elif whole_name in msg_data["users"]:
                msg_data["users"][whole_name]["msgcount"] += 1
                msg_data["total_count"] += 1
            else:
                msg_data["users"][whole_name] = {}
                msg_data["users"][whole_name]["msgcount"] = 1
                msg_data["total_count"] += 1
        return msg_data

    @staticmethod
    def calculate_top(msg_data: dict) -> Tuple[list, int]:
        """Calculate the top 20 from the message data package"""
        for usr in msg_data["users"]:
            pd = float(msg_data["users"][usr]["msgcount"]) / float(
                msg_data["total_count"]
            )
            msg_data["users"][usr]["percent"] = round(pd * 100, 1)
        top_twenty = heapq.nlargest(
            20,
            [
                (x, msg_data["users"][x][y])
                for x in msg_data["users"]
                for y in msg_data["users"][x]
                if (y == "percent" and msg_data["users"][x][y] > 0)
            ],
            key=lambda x: x[1],
        )
        others = 100 - sum(x[1] for x in top_twenty)
        return top_twenty, others

    @staticmethod
    async def create_chart(
        top, others, channel_or_guild: Union[discord.Guild, discord.TextChannel]
    ):
        plt.clf()
        sizes = [x[1] for x in top]
        labels = ["{} {:g}%".format(x[0], x[1]) for x in top]
        if len(top) >= 20:
            sizes = sizes + [others]
            labels = labels + ["Others {:g}%".format(others)]
        if len(channel_or_guild.name) >= 19:
            if isinstance(channel_or_guild, discord.Guild):
                channel_or_guild_name = "{}...".format(channel_or_guild.name[:19])
            else:
                channel_or_guild_name = "#{}...".format(channel_or_guild.name[:19])
        else:
            channel_or_guild_name = channel_or_guild.name
        title = plt.title("Stats in {}".format(channel_or_guild_name), color="white")
        title.set_va("top")
        title.set_ha("center")
        plt.gca().axis("equal")
        colors = [
            "r",
            "darkorange",
            "gold",
            "y",
            "olivedrab",
            "green",
            "darkcyan",
            "mediumblue",
            "darkblue",
            "blueviolet",
            "indigo",
            "orchid",
            "mediumvioletred",
            "crimson",
            "chocolate",
            "yellow",
            "limegreen",
            "forestgreen",
            "dodgerblue",
            "slateblue",
            "gray",
        ]
        pie = plt.pie(sizes, colors=colors, startangle=0)
        plt.legend(
            pie[0],
            labels,
            bbox_to_anchor=(0.7, 0.5),
            loc="center",
            fontsize=10,
            bbox_transform=plt.gcf().transFigure,
            facecolor="#ffffff",
        )
        plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
        image_object = BytesIO()
        plt.savefig(image_object, format="PNG", facecolor="#36393E")
        image_object.seek(0)
        return image_object

    async def get_kitties(self) -> str:
        if random.randint(1, 3) == 1:
            url = nekos.cat()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.thecatapi.com/v1/images/search"
                ) as r:
                    data = await r.json()
                    url = data[0]["url"]
        return url

    @commands.command(use="`tp!optout`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def optout(self, ctx):
        """Opt out of the bot's message history fetching"""
        cursor_n.execute(
            f"SELECT msgtracking FROM public.users WHERE userid = '{ctx.author.id}'"
        )
        for row in cursor_n.fetchall():
            if row[0] is False:
                await ctx.send("You are already opted out of message tracking!")
            else:
                cursor_n.execute(
                    f"UPDATE public.users SET msgtracking = False WHERE userid = '{ctx.author.id}'"
                )
                mydb_n.commit()
                await ctx.send("You have opted out of message tracking!")

    @commands.command(use="`tp!optin`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def optin(self, ctx):
        """Opt in to the bot's message history fetching"""
        cursor_n.execute(
            f"SELECT msgtracking FROM public.users WHERE userid = '{ctx.author.id}'"
        )
        for row in cursor_n.fetchall():
            if row[0] is True:
                await ctx.send("You are already opted in to message tracking!")
            else:
                cursor_n.execute(
                    f"UPDATE public.users SET msgtracking = True WHERE userid = '{ctx.author.id}'"
                )
                mydb_n.commit()
                await ctx.send("You have opted in to message tracking!")

    @commands.guild_only()
    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 300, commands.BucketType.guild)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def chatchart(
        self, ctx, channel: Optional[discord.TextChannel] = None, messages: int = 10000
    ):
        """
        Generates a pie chart, representing the last 10000 messages in the specified channel.
        This command has a server wide cooldown of 300 seconds.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        else:
            cursor_n.execute(
                f"SELECT msgtracking FROM public.users WHERE userid = '{ctx.author.id}'"
            )
            for row in cursor_n.fetchall():
                if row[0] is False:
                    return await ctx.send(
                        "You are opted out of message tracking!\nTo opt back in, use `tp!optin`"
                    )
                else:
                    pass

        if channel is None:
            channel = ctx.channel

        # --- Early terminations
        if channel.permissions_for(ctx.message.author).read_messages is False:
            return await ctx.send("You're not allowed to access that channel.")
        if channel.permissions_for(ctx.guild.me).read_messages is False:
            return await ctx.send("I cannot read the history of that channel.")
        if messages < 5:
            return await ctx.send("Theres not enough messages to show dummy")

        message_limit = 10000
        messages = message_limit

        embed = discord.Embed(
            title=f"Fetching messages from #{channel.name}",
            description="This might take a while...",
            colour=EMBED_COLOUR,
        )

        loading_message = await ctx.send(
            embed=embed,
        )
        try:
            history = await self.fetch_channel_history(
                channel, loading_message, messages
            )
        except discord.errors.Forbidden:
            try:
                await loading_message.delete()
            except discord.NotFound:
                pass
            return await ctx.send("No permissions to read that channel.")

        msg_data = self.calculate_member_perc(history)
        # If no members are found.
        if len(msg_data["users"]) == 0:
            try:
                await loading_message.delete()
            except discord.NotFound:
                pass
            return await ctx.send(
                f"Only bots have sent messages in {channel.mention} or I can't read message history."
            )

        top_twenty, others = self.calculate_top(msg_data)
        chart = await self.create_chart(top_twenty, others, channel)

        try:
            await loading_message.delete()
        except discord.NotFound:
            pass
        await ctx.send(file=discord.File(chart, "chart.png"))

    @commands.guild_only()
    @commands.command(aliases=["guildchart"])
    @permissions.dynamic_ownerbypass_cooldown(1, 2000, commands.BucketType.guild)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def serverchart(self, ctx, messages: int = 1000):
        """
        Generates a pie chart, representing the last 1000 messages from every allowed channel in the server.
        As example:
        For each channel that the bot is allowed to scan. It will take the last 1000 messages from each channel.
        And proceed to build a chart out of that.
        This command has a global serverwide cooldown of 2000 seconds.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        else:
            cursor_n.execute(
                f"SELECT msgtracking FROM public.users WHERE userid = '{ctx.author.id}'"
            )
            for row in cursor_n.fetchall():
                if row[0] is False:
                    return await ctx.send(
                        "You are opted out of message tracking!\nTo opt back in, use `tp!optin`"
                    )
                else:
                    pass

        if messages < 5:
            return await ctx.send("Don't be silly.")
        channel_list = []
        for channel in ctx.guild.text_channels:
            channel: discord.TextChannel
            if channel.permissions_for(ctx.message.author).read_messages is False:
                continue
            if channel.permissions_for(ctx.guild.me).read_messages is False:
                continue
            channel_list.append(channel)

        if len(channel_list) == 0:
            return await ctx.send(
                "There are no channels to read... How the fuck did this happen?"
            )

        embed = discord.Embed(
            description="Fetching messages from the entire server this **will** take a while.",
            colour=EMBED_COLOUR,
        )

        global_fetch_message = await ctx.send(
            embed=embed,
        )
        global_history = []

        for channel in channel_list:
            embed = discord.Embed(
                title=f"Fetching messages from #{channel.name}",
                description="This might take a while...",
                colour=EMBED_COLOUR,
            )

            loading_message = await ctx.send(
                embed=embed,
            )
            try:
                history = await self.fetch_channel_history(
                    channel, loading_message, messages
                )
                global_history += history
                await loading_message.delete()
            except discord.errors.Forbidden:
                try:
                    await loading_message.delete()
                except discord.NotFound:
                    continue
            except discord.NotFound:
                try:
                    await loading_message.delete()
                except discord.NotFound:
                    continue

        msg_data = self.calculate_member_perc(global_history)
        # If no members are found.
        if len(msg_data["users"]) == 0:
            try:
                await global_fetch_message.delete()
            except discord.NotFound:
                pass
            return await ctx.send(
                "Only bots have sent messages in this server... hgseiughsuighes..."
            )

        top_twenty, others = self.calculate_top(msg_data)
        chart = await self.create_chart(top_twenty, others, ctx.guild)

        try:
            await global_fetch_message.delete()
        except discord.NotFound:
            pass
        await ctx.send(file=discord.File(chart, "chart.png"))

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def bonk(self, ctx, user: Union[discord.Member, discord.User] = None):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author

        try:
            await ctx.message.delete()
        except Exception:
            pass
        if user != ctx.author:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.waifu.pics/sfw/bonk") as r:
                    if r.status == 200:
                        img = await r.json()
                        img = img["url"]
                        emoji = "<a:BONK:825511960741150751>"
                        embed = discord.Embed(
                            title="Bonky bonk.",
                            color=EMBED_COLOUR,
                            description=f"**{user}** gets bonked {emoji}",
                        )
                        embed.set_image(url=img)
                        await ctx.send(
                            embed=embed,
                        )
        else:
            await ctx.send("bonk <a:BONK:825511960741150751>")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def enlarge(self, ctx, emoji: str = None):
        """Post a large .png of an emoji"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")
        if emoji is None:
            return await ctx.send("Please provide an emoji.")
        convert = False
        if emoji[0] == "<":
            # custom Emoji
            try:
                name = emoji.split(":")[1]
            except IndexError:
                await ctx.send("thats not even an emote bruh")
                return
            emoji_name = emoji.split(":")[2][:-1]
            if emoji.split(":")[0] == "<a":
                # animated custom emoji
                url = "https://cdn.discordapp.com/emojis/" + emoji_name + ".gif"
                name += ".gif"
            else:
                url = "https://cdn.discordapp.com/emojis/" + emoji_name + ".png"
                name += ".png"
        else:
            chars = []
            name = []
            for char in emoji:
                chars.append(str(hex(ord(char)))[2:])
                try:
                    name.append(unicodedata.name(char))
                except ValueError:
                    # Sometimes occurs when the unicodedata library cannot
                    # resolve the name, however the image still exists
                    name.append("none")
            name = "_".join(name) + ".png"

            if len(chars) == 2:
                if "fe0f" in chars:
                    # remove variation-selector-16 so that the appropriate url can be built without it
                    chars.remove("fe0f")
            if "20e3" in chars:
                # COMBINING ENCLOSING KEYCAP doesn't want to play nice either
                chars.remove("fe0f")

            if svg_convert is not None:
                url = "https://twemoji.maxcdn.com/2/svg/" + "-".join(chars) + ".svg"
                convert = True
            else:
                url = "https://twemoji.maxcdn.com/2/72x72/" + "-".join(chars) + ".png"

        async with self.session.get(url) as resp:
            if resp.status != 200:
                await ctx.send("Emoji not found.")
                return
            img = await resp.read()

        if convert:
            task = functools.partial(Fun.generate, img)
            task = self.bot.loop.run_in_executor(None, task)

            try:
                img = await asyncio.wait_for(task, timeout=15)
            except asyncio.TimeoutError:
                await ctx.send("Image creation timed out.")
                return
        else:
            img = io.BytesIO(img)

        await ctx.send(file=discord.File(img, name))

    @staticmethod
    def generate(img):
        # Designed to be run in executor to avoid blocking
        if svg_convert == "cairo":
            kwargs = {"parent_width": 1024, "parent_height": 1024}
            return io.BytesIO(cairosvg.svg2png(bytestring=img, **kwargs))
        else:
            return io.BytesIO(img)

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def ascii(self, ctx, *, text: str = None):
        """Beautify some text"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if len(text) > 30:
            return await ctx.send("Text too long!")

        await ctx.send(f"```ascii\n{default.ascii_art(text)}\n```")

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def chatrevive(self, ctx):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        responces = [
            "Who is your favorite superhero? ",
            "Who is the most powerful superhero and why?",
            "Who created me?",
            "You dont WHAT at night? (minecraft reference)",
            "Whats your favorite song?",
            "What would the perfect weekend be? ",
            "What is your favorite video game? ",
            "What is your favorite food? ",
            "If you could have any car in the world what would it be? ",
            "What's better, tiktok or vine? ",
            "What's better, console or PC? ",
            "What do you prefer: online school or being in school? ",
            "What is your favorite sport? ",
            "Who is your favorite pro player?",
            f"Dyno, Mee6, or me? ({self.bot.user.name})",
            "Who is the best staff in this server? ",
            "iPhone or Android and why? ",
            "Xbox or Playstation? ",
            "What is your dream job? ",
            "Would you rather live by the beach or the mountains? ",
            "Which is better: cookies or ice cream? ",
            "Minecraft or Roblox? ",
            "TV show or movies? ",
            "Book or movie? ",
            "What is your favorite way to pass time? ",
            "Whats the most addicting app? ",
            "What is the funniest joke you know? ",
            "Who is your favorite actor? ",
            "What is the strangest dream you have had? ",
            "Where is the most beautiful place you have been? ",
            "What animal or insect do you wish humans could eradicate and why? ",
            "What is the most disgusting habit some people have? ",
            "What is the silliest fear you have? ",
            "Who has the smallest pp in this server?",
            "Who is the funniest person you've met? ",
            "What weird or useless talent do you have? ",
            "What's the most underrated (or overrated) TV show? ",
        ]
        say = random.choice(responces)
        embed = discord.Embed(
            colour=EMBED_COLOUR,
            title=f"{say}",
            url=Website,
            timestamp=ctx.message.created_at,
        )
        await ctx.send(
            embed=embed,
        )

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def coinflip(self, ctx):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        sides = ["**Heads**", "**Tails**"]
        randomcoin = random.choice(sides)
        if random.randint(1, 6000) == 1:
            await ctx.send("The coin landed on its side!")
        else:
            await ctx.send(f"The coin landed on {randomcoin}!")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def pp(self, ctx, *, user: MemberConverter = None):
        """See how much someone is packing :flushed:"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        final = "=" * random.randrange(15)
        value = f"8{final}D"
        if final == "":
            value = "Doesn't exist."
        # final = '=' * (user.id % 15)
        embed = discord.Embed(
            colour=EMBED_COLOUR,
            timestamp=ctx.message.created_at,
            url=Website,
        )
        embed.add_field(name=f"{user.name}'s pp size", value=value)
        await ctx.send(
            embed=embed,
        )

    @commands.command(aliases=["bm"], hidden=True)
    @commands.check(permissions.is_owner)
    async def beemovie(self, ctx):
        """
        Sends the entire beemovie script.
        Has an 83 minute cooldown for a reason
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        async with ctx.channel.typing():
            with open("beemovie_script.txt", "r") as f:
                for line in f:
                    try:
                        await ctx.send(line)
                        await asyncio.sleep(1.5)
                    except Exception:
                        pass

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command(hidden=True)
    @commands.check(permissions.is_owner)
    async def math(self, ctx):
        """Solve simple math problems
        Example
        tp!math 2x6 or 2*6
        ÷ = /
        x = *
        • = *
        = = ==
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        mem = ctx.author
        try:
            problem = str(ctx.message.clean_content.replace(f"{ctx.prefix}math", ""))
            # If a problem isn't given
            if problem == "":
                e = discord.Embed(
                    description=f"Actually put something for me to solve...",
                    color=0xFF0000,
                )
                await ctx.send(embed=e)
                return
            #    If the user's problem is too long
            if len(problem) > 500:
                e = discord.Embed(description=f"Too long, try again.", color=0x3498DB)
                await ctx.send(embed=e)
                return
            problem = (
                problem.replace("÷", "/")
                .replace("x", "*")
                .replace("•", "*")
                .replace("=", "==")
                .replace("π", "3.14159")
            )
            #    Iterate through a string of invalid
            #    Chracters
            for letter in "abcdefghijklmnopqrstuvwxyz\\_`,@~<>?|'\"{}[]":
                # If any of those characters are in user's math
                if letter in problem:
                    e = discord.Embed(
                        description="I can only do simplistic math, adding letters and other characters doesn't work.",
                        color=0xFF0000,
                    )
                    await ctx.send(embed=e)
                    return
            #    Make embed
            e = discord.Embed(timestamp=datetime.datetime.utcnow())
            #    Make fields
            fields = [
                ("Problem Given", problem, True),
                ("Answer", f"{str(round(eval(problem), 4))}", True),
            ]
            #    Add the fields
            for n, v, i in fields:
                e.add_field(name=n, value=v, inline=i)
            e.set_footer(text=mem, icon_url=mem.avatar)
            #    Send embed
            await ctx.send(embed=e)
        # If the problem is unsolvable
        except Exception:
            e = discord.Embed(
                description=f"Either the problem couldn't be solved or something happened, report it to the devs either way.",
                color=0xFF0000,
            )
            await ctx.send(embed=e)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def covid(self, ctx, country_code: str = "Global"):
        """Covid stats. Provide a country via it's ISO code.
        Common codes:
                        US: United States
                        GB: Great Britan,
                        CN: China,
                        FR: France,
                        DE: Germany
        https://countrycode.org/"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        embed = discord.Embed(
            title="Covid statistics",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            colour=EMBED_COLOUR,
            url=Website,
        )
        if len(country_code) > 10:
            await ctx.send("That doesn't look like a valid country code!")
            await ctx.send_help(str(ctx.command))
            return
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.covid19api.com/summary") as resp:
                resp = await resp.json()
                if country_code == "Global":
                    resp = resp["Global"]
                else:
                    resp = next(
                        item
                        for item in resp["Countries"]
                        if item["CountryCode"] == country_code.upper()
                    )
                    embed.title = f"Covid statistics for {resp['Country']}"
        # r = requests.get("https://api.covid19api.com/summary")
        # r= r.json()["Global"]
        embed.add_field(name="New Cases", value=f'{resp["NewConfirmed"]:,}')
        embed.add_field(name="New Deaths", value=f'{resp["NewDeaths"]:,}')
        embed.add_field(name="Newly Recovered", value=f'{resp["NewRecovered"]:,}')
        embed.add_field(name="Total Confirmed", value=f'{resp["TotalConfirmed"]:,}')
        embed.add_field(name="Total Deaths", value=f'{resp["TotalDeaths"]:,}')
        embed.add_field(name="Total Recovered", value=f'{resp["TotalRecovered"]:,}')
        embed.set_footer(
            text="Heads up! - Individual countries may not report the same information in the same way."
        )
        await ctx.send(
            embed=embed,
        )

    @permissions.dynamic_ownerbypass_cooldown(3, 8, commands.BucketType.user)
    @commands.command()
    async def chat(self, ctx, *, message: str = None):
        """New and **improved** chat bot!"""
        BASE_URL = f"http://api.brainshop.ai/get?bid={BID}&key={CHAT_API_KEY}"
        async with ctx.channel.typing():
            if message is None:

                return await ctx.send(
                    f"Hello! In order to chat with me use: `{ctx.prefix}chat <message>`"
                )

            async with aiohttp.ClientSession() as s:
                async with s.get(f"{BASE_URL}&uid={ctx.author.id}&msg={message}") as r:
                    if r.status != 200:
                        return await ctx.send(
                            f"An error occured while accessing the chat API!"
                        )
                    j = await r.json()
                    await ctx.reply(j["cnt"], mention_author=True)

    @commands.Cog.listener(name="on_message")
    async def autochat(self, message: discord.Message):
        chat_channel_id = 971893038999797770
        if message.author.bot:
            return
        if message.content == "":
            return
        if message.channel.id == chat_channel_id:
            ctx = await self.bot.get_context(message)
            await ctx.invoke(self.bot.get_command("chat"), message=message.content)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def mock(
        self,
        ctx,
        *,
        msg: Optional[Union[discord.Message, discord.Member, str]] = None,
    ) -> None:
        """
        Mock a user with the spongebob meme
        `[msg]` Optional either member, message ID, or string
        message ID can be channe_id-message-id formatted or a message link
        if no `msg` is provided the command will use the last message in channel before the command
        is `msg` is a member it will look through the past 10 messages in
        the `channel` and put them all together
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if isinstance(msg, str):
            log(f"Mocking a given string")
            result = await self.cap_change(str(msg))
            result += f"\n\n[Mocking Message]({ctx.message.jump_url})"
            author = ctx.message.author
        elif isinstance(msg, discord.Member):
            log(f"Mocking a user")
            total_msg = ""
            async for message in ctx.channel.history(limit=10):
                if message.author == msg:
                    total_msg += message.content + "\n"
            result = await self.cap_change(total_msg)
            author = msg
        elif isinstance(msg, discord.Message):
            log(f"Mocking a message")
            result = await self.cap_change(msg.content)
            result += f"\n\n[Mocking Message]({msg.jump_url})"
            author = msg.author
            search_msg = msg
        else:
            log(f"Mocking last message in chat")
            async for message in ctx.channel.history(limit=2):
                search_msg = message
            author = search_msg.author
            result = await self.cap_change(search_msg.content)
            result += f"\n\n[Mocking Message]({search_msg.jump_url})"
            if result == "" and len(search_msg.embeds) != 0:
                if search_msg.embeds[0].description != None:
                    result = await self.cap_change(search_msg.embeds[0].description)
        ctx.message.created_at
        embed = discord.Embed(
            description=result, timestamp=ctx.message.created_at, url=Website
        )
        embed.colour = getattr(author, "colour", discord.Colour.default())
        embed.set_author(name=author.display_name, icon_url=author.avatar)
        embed.set_thumbnail(url="https://i.imgur.com/upItEiG.jpg")
        embed.set_footer(
            text=f"{ctx.message.author.display_name} mocked {author.display_name}",
            icon_url=ctx.message.author.avatar,
        )
        if hasattr(msg, "attachments") and search_msg.attachments != []:
            embed.set_image(url=search_msg.attachments[0].url)
        if not ctx.channel.permissions_for(ctx.me).embed_links:
            if author != ctx.message.author:
                await ctx.send(f"{result} - {author.mention}")
            else:
                await ctx.send(result)
        else:
            await ctx.send(
                embed=embed,
            )
            if author != ctx.message.author:
                await ctx.send(f"- {author.mention}")

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def eightball(self, ctx, *, question: commands.clean_content):
        """Ask 8ball"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        embed = discord.Embed(
            title=f"{ctx.message.author.display_name} asked:", description=question
        )
        embed.set_image(url=nekos.img("8ball"))
        await ctx.send(embed=embed)

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def spoiler(self, ctx, *, text: str):
        """Make a message have multiple spoilers"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")
        fuck = nekos.spoiler(text)
        await ctx.send(f"{fuck}\n- {ctx.message.author}")

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def owoify(self, ctx, *, text: commands.clean_content):
        """Owoify any message"""

        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        owoified = nekos.owoify(text)
        await ctx.send(f"{owoified}\n- {ctx.message.author}")

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def why(self, ctx):
        """why"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        why = nekos.why()
        await ctx.send(why)

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def fact(self, ctx):
        """Get a random fact"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        fact = nekos.fact()
        await ctx.send(fact)

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def name(self, ctx):
        """Get a random name"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")
        name = nekos.name()
        await ctx.send(f"Your name is: {name}")

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def slap(self, ctx, *, user: MemberConverter):
        """Slap people"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} hits themselves lol...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("slap"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} hits {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("slap"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command(hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    async def pot(self, ctx):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        embed = discord.Embed(title="bred")
        embed.add_field(
            name="How'd you find this lol",
            value=f"[Don't click me :flushed:](https://www.youtube.com/watch?v=MwMuEBhgNNE&ab_channel=ShelseaO%27Hanlon)",
        )
        await ctx.send(
            embed=embed,
        )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def hug(self, ctx, *, user: MemberConverter):
        """Hug people"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} hugs themselves, how sad...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("hug"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} hugs {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("hug"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def kiss(self, ctx, *, user: MemberConverter):
        """Kiss people"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        if user == ctx.author:
            weird = [
                "how lonely they must be",
                "weirdo...",
                "god thats sad",
                "get a gf",
            ]
            embed = discord.Embed(
                title=f"{ctx.author.name} kisses themselves, {random.choice(weird)}",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("kiss"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )
        else:
            cute = ["awww", "adorable", "cute"]
            embed = discord.Embed(
                title=f"{ctx.author.name} kisses {user.name}... {random.choice(cute)}",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("kiss"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def smug(self, ctx, *, user: MemberConverter = None):
        """Look smug"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        embed = discord.Embed(
            title=f"{ctx.author} is smug...",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            url=Website,
            colour=EMBED_COLOUR,
            timestamp=ctx.message.created_at,
        )

        embed.set_image(url=nekos.img("smug"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
        await ctx.send(
            embed=embed,
        )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def pat(self, ctx, *, user: MemberConverter):
        """Pat people"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} pats themselves, kinda sad tbh...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("pat"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} patted {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("pat"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def tickle(self, ctx, *, user: MemberConverter):
        """Tickle people"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} tickles themselves, gross...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("tickle"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} tickled {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("tickle"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.command(aliases=["jump", "murder", "slay"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def kill(self, ctx, *, user: MemberConverter):
        """Kill someone"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author
        kill_msg = [
            f"{user.name} gets stabbed by a knife from {ctx.author.name}",
            f"{user.name} gets shot by {ctx.author.name}",
            f"{user.name} gets executed by {ctx.author.name}",
            f"{user.name} gets impaled by {ctx.author.name}",
            f"{user.name} gets burned by {ctx.author.name}",
            f"{user.name} gets crucified by {ctx.author.name}",
            f"{user.name} was eaten by {ctx.author.name}",
            f"{user.name} died from {ctx.author.name}'s awful puns",
            f"{user.name} was cut in half by {ctx.author.name}",
            f"{user.name} was hanged by {ctx.author.name}",
            f"{user.name} was strangled by {ctx.author.name}",
            f"{user.name} died from a poorly made cupcake by {ctx.author.name}",
            f"{user.name} died within a couple seconds of getting jumped by {ctx.author.name}",
            f"{ctx.author.name} 'accidentally' killed {user.name}",
            f"{ctx.author.name} tried to kill {user.name}, but just missed",
            f"{ctx.author.name} tried to strangle {user.name}, but it didn't work",
            f"{ctx.author.name} tripped over their own knife trying to kill {user.name} but killed themselves instead!",
            f"{ctx.author.name} tried to kill {user.name}, but they didn't have a knife!",
            f"{ctx.author.name} tried to kill {user.name}, but they were too scared to kill them!",
            f"{ctx.author.name} absolutely demolished {user.name}'s head with a frying pan!",
            f"{ctx.author.name} got ratioed so hard {user.name} fucking died 💀",
            f"{user.name} kicked {ctx.author.name}'s ass so bad they died",
            f"{user.name} breathed {ctx.author.name}'s air so hard they died",
            f"{ctx.author.name} inhaled a fart from {user.name} and died",
            f"{user.name} inhaled a fart from {ctx.author.name} and died",
        ]
        if user == ctx.author:
            embed = discord.Embed(
                title=f"Okay you've killed yourself {ctx.author.name}, I hope this was worth it! Now tag someone else to kill them!",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )
        else:
            embed = discord.Embed(
                title=f"{random.choice(kill_msg)}",
                url=Website,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(
                embed=embed,
            )

    @commands.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def meme(self, ctx, ephemeral: bool = False):
        """Sends you the dankest memes"""
        subs = ["dankmemes", "memes", "ComedyCemetery"]
        subreddit = await self.reddit.subreddit(random.choice(subs))
        all_subs = []
        top = subreddit.hot(limit=50)
        async for submission in top:
            all_subs.append(submission)
        random_sub = random.choice(all_subs)
        name = random_sub.title
        url = random_sub.url
        if "https://v" in url:
            return await ctx.send(url)
        elif "https://streamable.com/" in url:
            return
        elif "https://i.imgur.com/" in url:
            return await ctx.send(url)
        elif "https://gfycat.com/" in url:
            return await ctx.send(url)
        elif "https://imgflip.com/gif/" in url:
            return await ctx.send(url)
        elif "https://youtu.be/" in url:
            return await ctx.send(url)
        elif "https://youtube.com/" in url:
            return await ctx.send(url)
        embed = discord.Embed(
            title=name,
            url=url,
            colour=EMBED_COLOUR,
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
        )
        embed.set_image(url=url)
        embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar)
        await ctx.send(
            content="Alright, have this meme.", embed=embed, ephemeral=ephemeral
        )

    @commands.guild_only()
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_nsfw()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def shitpost(self, ctx):
        """Smear shit all over the chat."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        async with ctx.channel.typing():
            subs = ["okaybuddyretard", "gayspiderbrothel", "shitposting"]
            subreddit = await self.reddit.subreddit(random.choice(subs))
            all_subs = []
            top = subreddit.hot(limit=50)
            async for submission in top:
                all_subs.append(submission)
            random_sub = random.choice(all_subs)
            name = random_sub.title
            url = random_sub.url
            if "https://v" in url:
                return await ctx.send(url)
            elif "https://streamable.com/" in url:
                return
            elif "https://i.imgur.com/" in url:
                return await ctx.send(url)
            elif "https://gfycat.com/" in url:
                return await ctx.send(url)
            elif "https://imgflip.com/gif/" in url:
                return await ctx.send(url)
            embed = discord.Embed(
                title=name,
                url=url,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            )
            embed.set_image(url=url)
            embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar)
            await ctx.send(content="Alright, have this shitpost.", embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 15, commands.BucketType.user)
    @commands.command()
    async def hack(self, ctx, user: MemberConverter = None):
        """Hack a user, totally real and legit"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if user is None:
            async with ctx.channel.typing():
                await ctx.send("I can't hack air, mention someone.")

        elif user == ctx.author:
            async with ctx.channel.typing():
                await ctx.send("Lol what would hacking yourself get you lmao")

        else:
            email_fun = [
                "69420",
                "8008135",
                "eatsA$$",
                "PeekABoo",
                "TheShire",
                "isFAT",
                "Dumb_man",
                "Ruthless_gamer",
                "Sexygirl69",
                "Loyalboy69",
                "likesButts",
                "isastupidfuck",
                "milfsmasher",
                "dumbwhore",
                "am_dumbass",
                "is_assholesniffer",
                "is_stupid",
            ]

            email_address = (
                f"{user.name.lower()}{random.choice(email_fun).lower()}@gmail.com"
            )

            passwords = [
                "animeislife69420",
                "big_awoogas",
                "red_sus_ngl",
                "IamACompleteIdiot",
                "YouWontGuessThisOne",
                "yetanotherpassword",
                "iamnottellingyoumypw",
                "SayHelloToMyLittleFriend",
                "ImUnderYourBed",
                "TellMyWifeILoveHer",
                "P@$$w0rd",
                "iLike8008135",
                "IKnewYouWouldHackIntoMyAccount",
                "BestPasswordEver",
                "JustARandomPassword",
                "softnipples",
            ]

            password = f"{random.choice(passwords)}"

            DMs = [
                "nudes?",
                f"https://lunardev.group/home is a pretty cool website",
                "im kinda gay tbh",
                "bro dont make fun of my small penis",
                "https://youtu.be/iik25wqIuFo",
                "lmfao you kinda ugly",
                "pls no, stay out of my ass",
                "i use discord in light mode",
                "some animals give me boners..",
                "rub your asshole on the carpet and smell it",
                "I am a exquisite virgin",
                "dick fart",
                "Your pretty hot wanna fuck bbg?",
                "i got diabetes from rats",
                "Gib robux pls",
                "Dick pic or not pro",
                "Can i sniff?",
                "Lick the inside of my mouth pls",
                "*sniffs your asshole cutely uwu*",
                "Inject herion into my veins",
                "*performs butt sex*",
                "your dads pretty fat for a meth head",
                "hewwwoooo mommy?",
            ]

            latest_DM = f"{random.choice(DMs)}"
            # generate a random IP address
            ip_address = f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

            Discord_Servers = [
                "Virgins Only",
                "No friends gang",
                "Gaymers Together",
                "FuckShit",
                "Lunar Development",
                "Join this server if ur gay",
                "Egirls palace",
                "single people only",
                "Join if ur gay",
                "gacha heat 🥵🥵",
                "retards only",
                "furry pride",
                "subway surfers fan club (18+)",
                "racists only",
                "cocklovers only",
                "kitchen dwellers(women)",
                "WinterFe fanclub",
                "motz fanclub",
                "Please cancel us. Email: contact@lunardev.group",
            ]

            Most_Used_Discord_Server = f"{random.choice(Discord_Servers)}"

            async with ctx.channel.typing():
                msg1 = await ctx.send(
                    "Initializing Hack.exe... <a:discord_loading:816846352075456512>"
                )
                await asyncio.sleep(1)

                real_msg1 = await ctx.channel.fetch_message(msg1.id)
                await real_msg1.edit(
                    content=f"Successfully initialized Hack.exe, beginning hack on {user.name}... <a:discord_loading:816846352075456512>"
                )
                await asyncio.sleep(1)

                real_msg2 = await ctx.channel.fetch_message(msg1.id)
                await real_msg2.edit(
                    content=f"Logging into {user.name}'s Discord Account... <a:discord_loading:816846352075456512>"
                )
                await asyncio.sleep(1)

                real_msg3 = await ctx.channel.fetch_message(msg1.id)
                await real_msg3.edit(
                    content=f"<:discord:816846362267090954> Logged into {user.name}'s Discord:\nEmail Address: `{email_address}`\nPassword: `{password}`"
                )
                await asyncio.sleep(1)

                real_msg4 = await ctx.channel.fetch_message(msg1.id)
                await real_msg4.edit(
                    content=f"Fetching DMs from their friends(if there are any)... <a:discord_loading:816846352075456512>"
                )
                await asyncio.sleep(1)

                real_msg5 = await ctx.channel.fetch_message(msg1.id)
                await real_msg5.edit(
                    content=f"Latest DM from {user.name}: `{latest_DM}`"
                )
                await asyncio.sleep(1)

                real_msg6 = await ctx.channel.fetch_message(msg1.id)
                await real_msg6.edit(
                    content=f"Getting IP address... <a:discord_loading:816846352075456512>"
                )
                await asyncio.sleep(1)

                real_msg7 = await ctx.channel.fetch_message(msg1.id)
                await real_msg7.edit(content=f"IP address found: `{ip_address}`")
                await asyncio.sleep(1)

                real_msg11 = await ctx.channel.fetch_message(msg1.id)
                await real_msg11.edit(
                    content=f"Fetching the Most Used Discord Server... <a:discord_loading:816846352075456512>"
                )
                await asyncio.sleep(1)

                real_msg10 = await ctx.channel.fetch_message(msg1.id)
                await real_msg10.edit(
                    content=f"Most used Discord Server in {user.name}'s Account: `{Most_Used_Discord_Server}`"
                )
                await asyncio.sleep(1)

                real_msg8 = await ctx.channel.fetch_message(msg1.id)
                await real_msg8.edit(
                    content=f"Selling data to the dark web... <a:discord_loading:816846352075456512>"
                )
                await asyncio.sleep(1)

                real_msg9 = await ctx.channel.fetch_message(msg1.id)
                await real_msg9.edit(content=f"Hacking complete.")
                await asyncio.sleep(1.5)

                await real_msg9.edit(
                    content=f"{user.name} has successfully been hacked. <a:EpicTik:816846395302477824>\n\n**{user.name}**'s Data:\nDiscord Email: `{email_address}`\nDiscord Password: `{password}`\nMost used Discord Server: `{Most_Used_Discord_Server}`\nIP Address: `{ip_address}`\nLatest DM: `{latest_DM}`"
                )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    async def dog(self, ctx):
        """Puppers"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        async with aiohttp.ClientSession() as data:
            async with data.get("https://api.thedogapi.com/v1/images/search") as r:
                data = await r.json()
                breeds = data[0]["breeds"]
                weight = (
                    "Weight Unavailable"
                    if not breeds
                    else "\n".join(
                        [a.title() + ": " + b for a, b in breeds[0]["weight"].items()]
                    )
                )
                embed = discord.Embed(
                    title="Enjoy this doggo <3",
                    url="https://lunardev.group/",
                    description=f"**Name**\n{'Name Unavailable' if not breeds else breeds[0]['name']}\n\n**Weight**\n{weight}",
                    colour=EMBED_COLOUR,
                    timestamp=ctx.message.created_at,
                )
                embed.set_image(url=data[0]["url"])
                embed.set_footer(
                    text=f"lunardev.group",
                    icon_url=ctx.author.avatar,
                )
                await ctx.send(
                    embed=embed,
                )

    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    async def cat(self, ctx):
        """Kitties!!"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        embed = discord.Embed(
            title="Enjoy this cat <3", colour=EMBED_COLOUR, url=Website
        )
        embed.set_image(url=await self.get_kitties())
        embed.set_footer(text="lunardev.group", icon_url=ctx.author.avatar)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def birb(self, ctx):
        """Its really just geese"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        embed = discord.Embed(
            title="H o n k",
            colour=EMBED_COLOUR,
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            timestamp=ctx.message.created_at,
            url=Website,
        )

        embed.set_image(url=nekos.img("goose"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
        await ctx.send(
            embed=embed,
        )

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    @commands.bot_has_permissions(add_reactions=True)
    async def pressf(self, ctx, *, user: discord.User = None):
        """Pay respects by pressing F"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if str(ctx.channel.id) in self.channels:
            return await ctx.send(
                "Oops! I'm still paying respects in this channel, you'll have to wait until I'm done."
            )

        if user:
            answer = user.display_name
        else:
            await ctx.send("What do you want to pay respects to?")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                pressf = await ctx.bot.wait_for("message", timeout=120.0, check=check)
            except asyncio.TimeoutError:
                return await ctx.send("You took too long to send.")

            answer = pressf.content[:1900]

        message = await ctx.send(
            f"Everyone, let's pay respects to **{filter_mass_mentions(answer)}**! Press the f reaction on this message to pay respects."
        )
        await message.add_reaction("\U0001f1eb")
        self.channels[str(ctx.channel.id)] = {"msg_id": message.id, "reacted": []}
        await asyncio.sleep(120)
        try:
            await message.delete()
        except (discord.errors.NotFound, discord.errors.Forbidden):
            pass
        amount = len(self.channels[str(ctx.channel.id)]["reacted"])
        word = "person has" if amount == 1 else "people have"
        await ctx.send(
            f"**{amount}** {word} paid respects to **{filter_mass_mentions(answer)}**."
        )
        del self.channels[str(ctx.channel.id)]

    @commands.Cog.listener(name="on_reaction_add")
    async def PressF(self, reaction, user):
        if str(reaction.message.channel.id) not in self.channels:
            return
        if (
            self.channels[str(reaction.message.channel.id)]["msg_id"]
            != reaction.message.id
        ):
            return
        if user.id == self.bot.user.id:
            return
        if user.id not in self.channels[str(reaction.message.channel.id)]["reacted"]:
            if str(reaction.emoji) == "\U0001f1eb":
                await reaction.message.channel.send(
                    f"**{user.name}** has paid their respects."
                )
                self.channels[str(reaction.message.channel.id)]["reacted"].append(
                    user.id
                )

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def lenny(self, ctx):
        """( ͡° ͜ʖ ͡°)"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(f"( ͡° ͜ʖ ͡°)")

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def urban(self, ctx, *, search: commands.clean_content):
        """Find the 'best' definition to your words"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        async with ctx.channel.typing():
            try:
                url = await http.get(
                    f"https://api.urbandictionary.com/v0/define?term={search}",
                    res_method="json",
                )
            except Exception:
                return await ctx.send(
                    "Urban API returned invalid data... might be down atm."
                )
            if not url:
                return await ctx.send("I think the API broke...")
            if not len(url["list"]):
                return await ctx.send("Couldn't find your search in the dictionary...")
            result = sorted(
                url["list"], reverse=True, key=lambda g: int(g["thumbs_up"])
            )[0]

            definition = result["definition"]
            if len(definition) >= 1000:
                definition = definition[:1000]
                definition = definition.rsplit(" ", 1)[0]
                definition += "..."
            if ctx.interaction is None:
                if ctx.channel.is_nsfw():
                    await ctx.send(
                        f"📚 Definitions for **{result['word']}**```fix\n{definition}```"
                    )
                    return
                else:
                    # raise nsfw channel required
                    raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(
                f"📚 Definitions for **{result['word']}**```fix\n{definition}```",
                ephemeral=True,
            )

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def reverse(self, ctx, *, text: str):
        """Reverses Shit"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        t_rev = text[::-1].replace("@", "@‎").replace("&", "&‎")
        await ctx.send(f"🔁 {t_rev}")

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def password(self, ctx, nbytes: int = 40):
        """Generates a random password string for you
        This returns a random URL-safe text string, containing nbytes random bytes.
        The text is Base64 encoded, so on average each byte results in approximately 1.3 characters.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if nbytes not in range(3, 1001):
            return await ctx.send("I only accept any numbers between 3-1000")
        if hasattr(ctx, "guild") and ctx.guild is not None:
            await ctx.send(
                f"Alright, lemme send you this randomly generated password {ctx.author.mention}."
            )
        await ctx.author.send(
            f"🎁 **Here is your password:**\n{secrets.token_urlsafe(nbytes)}\n\n**You could actually use this password for things too since this was completely randomly generated.**"
        )

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 2, type=commands.BucketType.user)
    async def rate(self, ctx, *, thing: commands.clean_content):
        """Rates what you want"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        rate_amount = random.uniform(0.0, 100.0)
        await ctx.send(f"I'd rate `{thing}` a **{round(rate_amount, 4)} / 100**")

    @permissions.dynamic_ownerbypass_cooldown(1, 2.5, type=commands.BucketType.user)
    @commands.command()
    async def hotcalc(self, ctx, *, user: MemberConverter = None):
        """Returns a random percent for how hot is a discord user"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author

        if user.id == 318483487231574016:
            return await ctx.send(f"**{user.name}** is fucking dumb")

        r = random.randint(1, 100)
        hot = r / 1.17

        emoji = "💔"
        if hot > 25:
            emoji = "❤"
        if hot > 50:
            emoji = "💖"
        if hot > 75:
            emoji = "💞"

        await ctx.send(f"**{user.name}** is **{hot:.2f}%** hot {emoji}")

    @permissions.dynamic_ownerbypass_cooldown(1, 2.5, type=commands.BucketType.user)
    @commands.command()
    async def howgay(self, ctx, *, user: MemberConverter = None):
        """Tells you how gay a user is lol."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author

        # if user.id == 101118549958877184:
        #    return await ctx.send(f"**{user.name}** cant be gay, homo.")

        # if user.id == 503963293497425920:
        # return await ctx.send(f"**{user.name}** is not gay and he is a cool
        # kid")

        if user.id == 723726581864071178:
            return await ctx.send("I'm a fuckin bot lmao.")

        r = random.randint(1, 100)
        gay = r / 1.17

        emoji = "<:LMAO:838988129431191582>"
        if gay > 25:
            emoji = "<:kek:838988145550557244>"
        if gay > 50:
            emoji = "<:yikes:838988155947319337>"
        if gay > 75:
            emoji = "<:stop_pls:838988169251782666>"

        await ctx.send(f"**{user.name}** is **{gay:.2f}%** gay {emoji}")

    @permissions.dynamic_ownerbypass_cooldown(1, 2.5, type=commands.BucketType.user)
    @commands.command()
    async def simp(self, ctx, *, user: MemberConverter = None):
        """Tells you if a user is a simp lol."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author

        if user.id == 503963293497425920:
            return await ctx.send(f"**{user.name}** is not a simp and he is a cool kid")

        if user.id == 723726581864071178:
            return await ctx.send("I'm a fuckin bot lmao.")

        r = random.randint(1, 100)
        simp = r / 1.17

        emoji = "<:LMAO:838988129431191582>"
        if simp > 25:
            emoji = "<:kek:838988145550557244>"
        if simp > 50:
            emoji = "<:yikes:838988155947319337>"
        if simp > 75:
            emoji = "<:stop_pls:838988169251782666>"

        await ctx.send(f"**{user.name}** is **{simp:.2f}%** simp {emoji}")

    @permissions.dynamic_ownerbypass_cooldown(1, 2.5, type=commands.BucketType.user)
    @commands.command()
    async def horny(self, ctx, *, user: MemberConverter = None):
        """Tells you how horny someone is :flushed:"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        user = user or ctx.author

        if user.id == 101118549958877184:
            return await ctx.send(
                f"**{user.name}** is super fucking horny, like constantly."
            )

        if user.id == 503963293497425920:
            return await ctx.send(f"**{user.name}** ***Horny.***")

        if user.id == 723726581864071178:
            return await ctx.send("I'm a fuckin bot lmao.")

        r = random.randint(0, 200)
        horny = r / 1.17
        emoji = "<:swagcat:843525938952404993>"
        if horny > 0:
            emoji = "<:swagcat:843525938952404993>"
        if horny > 55:
            emoji = "<:kek:838988145550557244>"
        if horny > 75:
            emoji = "<:yikes:838988155947319337>"
        if horny > 150:
            emoji = "<:stop_pls:838988169251782666>"

        await ctx.send(f"**{user.name}** is **{horny:.2f}%** horny {emoji}")


async def setup(bot):
    await bot.add_cog(Fun(bot))
