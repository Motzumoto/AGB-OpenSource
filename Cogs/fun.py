import asyncio
import datetime
import functools
import heapq
import io
import random
import secrets
import unicodedata
import urllib
from io import BytesIO
from typing import List, Optional, Tuple, Union

import aiohttp
import alexflipnote
import asyncpraw
import discord
import matplotlib
import matplotlib.pyplot as plt
import nekos
from Cogs import DL, DisplayName, Utils
from discord.ext import commands
from index import BID, CHAT_API_KEY, EMBED_COLOUR, Website, config
from utils import default, http, lists, permissions
from utils.checks import voter_only
from utils.common_filters import filter_mass_mentions
from utils.default import type_message

from .Utils import *

try:
    import cairosvg

    svg_convert = "cairo"
except:
    try:
        from wand.image import Image

        svg_convert = "wand"
    except:
        svg_convert = None

matplotlib.use("agg")

plt.switch_backend("agg")


class Fun(commands.Cog, name="fun"):
    """Fun / Game commands"""

    def __init__(self, bot):
        self.bot = bot
        self.channels = {}
        global Utils, DisplayName
        # self.trans = googletrans.Translator()
        Utils = self.bot.get_cog("Utils")
        self.session = aiohttp.ClientSession()
        if svg_convert == "cairo":
            print(f"{default.date()} | bigmoji: Using CairoSVG for svg conversion.")
        elif svg_convert == "wand":
            print(f"{default.date()} | bigmoji: Using wand for svg conversion.")
        else:
            print(
                f"{default.date()} | bigmoji: Failed to import svg converter. Standard emoji will be limited to 72x72 png."
            )

        self.config = default.get("config.json")
        DisplayName = self.bot.get_cog("DisplayName")
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

        self.alex_api = alexflipnote.Client(self.config.flipnote)
        self.bot.alex_api = self.alex_api

    def cog_unload(self):
        self.session.stop()
        self.reddit.stop()
        self.ttt_games.stop()
        self.params.stop()

    def format_help_for_context(self, ctx: commands.Context):
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

    def cog_unload(self):
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
            history.append(msg)
            history_counter += 1
            if history_counter % 250 == 0:
                new_embed = discord.Embed(
                    title=f"Fetching messages from #{channel.name}",
                    description=f"This might take a while...\n{history_counter}/{messages} messages gathered",
                    colour=EMBED_COLOUR,
                )

                if channel.permissions_for(channel.guild.me).send_messages:
                    await channel.trigger_typing()
                if animation_message_deleted is False:
                    try:
                        await animation_message.edit(embed=new_embed)
                    except discord.NotFound:
                        animation_message_deleted = True
        return history

    @commands.guild_only()
    @commands.command(usage="`tp!chatchart #channel`")
    @voter_only()
    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def chatchart(
        self, ctx, channel: Optional[discord.TextChannel] = None, messages: int = 10000
    ):
        """
        Generates a pie chart, representing the last 10000 messages in the specified channel.
        This command has a server wide cooldown of 300 seconds.
        """
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

        loading_message = await ctx.send(embed=embed)
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
    @commands.command(usage="`tp!serverchart`", aliases=["guildchart"])
    @commands.cooldown(1, 2000, commands.BucketType.guild)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @voter_only()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def serverchart(self, ctx: commands.Context, messages: int = 1000):
        """
        Generates a pie chart, representing the last 1000 messages from every allowed channel in the server.
        As example:
        For each channel that the bot is allowed to scan. It will take the last 1000 messages from each channel.
        And proceed to build a chart out of that.
        This command has a global serverwide cooldown of 2000 seconds.
        """
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

        global_fetch_message = await ctx.send(embed=embed)
        global_history = []

        for channel in channel_list:
            embed = discord.Embed(
                title=f"Fetching messages from #{channel.name}",
                description="This might take a while...",
                colour=EMBED_COLOUR,
            )

            loading_message = await ctx.send(embed=embed)
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
                f"Only bots have sent messages in this server... hgseiughsuighes..."
            )

        top_twenty, others = self.calculate_top(msg_data)
        chart = await self.create_chart(top_twenty, others, ctx.guild)

        try:
            await global_fetch_message.delete()
        except discord.NotFound:
            pass
        await ctx.send(file=discord.File(chart, "chart.png"))

    # @commands.command(hidden=True)
    # async def translate(self, ctx, *, message: commands.clean_content = None):
    #     """Translates a message to English using Google translate."""

    #     loop = self.bot.loop
    #     if message is None:
    #         ref = ctx.message.reference
    #         if ref and isinstance(ref.resolved, discord.Message):
    #             message = ref.resolved.content
    #         else:
    #             return await ctx.send('Missing a message to translate')

    #     try:
    #         ret = await loop.run_in_executor(None, self.trans.translate, message)
    #     except Exception as e:
    #         return await ctx.send(f'An error occurred: {e.__class__.__name__}: {e}')

    #     embed = discord.Embed(title='Translated', colour=0x4284F3)
    #     src = googletrans.LANGUAGES.get(ret.src, '(auto-detected)').title()
    #     dest = googletrans.LANGUAGES.get(ret.dest, 'Unknown').title()
    #     embed.add_field(name=f'From {src}', value=ret.origin, inline=False)
    #     embed.add_field(name=f'To {dest}', value=ret.text, inline=False)
    #     await ctx.send(embed=embed)

    @commands.command(usage="`tp!bonk`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def bonk(self, ctx, user: Union[discord.Member, discord.User] = None):
        user = user or ctx.author

        try:
            await ctx.message.delete()
        except discord.Forbidden:
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
                        await ctx.send(embed=embed)
        else:
            await ctx.send("bonk <a:BONK:825511960741150751>")

    @commands.command(usage="`tp!enlarge <emoji>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def enlarge(self, ctx, emoji):
        """Post a large .png of an emoji"""
        if not permissions.can_handle(ctx, "attach_files"):
            return await ctx.send("I can't send images here lol. fix that.")
        channel = ctx.channel
        convert = False
        if emoji[0] == "<":
            # custom Emoji
            try:
                name = emoji.split(":")[1]
            except IndexError:
                await ctx.send("That doesn't look like an emoji to me!")
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
            task = functools.partial(Bigmoji.generate, img)
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
        elif svg_convert == "wand":
            with Image(blob=img, format="svg", resolution=2160) as bob:
                return bob.make_blob("png")
        else:
            return io.BytesIO(img)

    @commands.command(usage="`tp!ascii <Optional:font> <text>`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def ascii(self, ctx, *, text: str = None):
        """Beautify some text
        You can find a fonts list here: http://artii.herokuapp.com/fonts_list"""
        if len(text) > 30:
            await ctx.send(
                "The message you wanted was too long, it has to be under 30 characters!"
            )
            return
        # Get list of fonts
        fonturl = "http://artii.herokuapp.com/fonts_list"
        response = await DL.async_text(fonturl)
        fonts = response.split()

        font = None
        # Split text by space - and see if the first word is a font
        parts = text.split()
        if len(parts) > 1:
            # We have enough entries for a font
            if parts[0] in fonts:
                # We got a font!
                font = parts[0]
                text = " ".join(parts[1:])

        url = "http://artii.herokuapp.com/make?{}".format(
            urllib.parse.urlencode({"text": text})
        )
        if font:
            url += "&font={}".format(font)
        response = await DL.async_text(url)
        await ctx.send("```ascii\n{}```".format(response))

    @commands.command(aliases=["topics", "revive"], usage="`tp!topics`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def chatrevive(self, ctx):

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
            "Who is the funniest person you’ve met? ",
            "What weird or useless talent do you have? ",
            "What’s the most underrated (or overrated) TV show? ",
        ]
        say = random.choice(responces)
        embed = discord.Embed(
            colour=EMBED_COLOUR,
            title=f"{say}",
            url=f"{Website}",
            timestamp=ctx.message.created_at,
        )
        await ctx.reply(embed=embed)

    @commands.command(
        aliases=[
            "cf",
            "cointoss",
            "coin_toss",
            "coin",
            "coin_flip",
            "HeadsorTails",
            "random_coin",
            "randomcoin",
        ],
        usage="`tp!coin`",
    )
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def coinflip(self, ctx):
        if ctx.author.id == 101118549958877184:
            await ctx.reply(
                "Somehow, the coin never came back down when you flipped it!"
            )
            return
        else:
            sides = ["**Heads**", "**Tails**", "**Heads**", "**Middle**"]
            randomcoin = random.choice(sides)
            await ctx.reply(f"The coin landed on {randomcoin}!")

    @commands.command(usage="`tp!supreme <text>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def supreme(self, ctx, *, text: str):
        """
        Make mockups of the shittiest clothing brand of all time.
        """
        if len(text) > 25:
            return await ctx.send(
                "The file you tried to render was over 25 characters! Please try again!"
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://supreme.png")
        image = discord.File(
            await (await self.alex_api.supreme(text=text)).read(), "supreme.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!facts <text>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def facts(self, ctx, *, text: str):
        """
        And that's a fact.
        """
        if len(text) > 40:
            return await ctx.send(
                "The file you tried to render was over 40 characters! Please try again!"
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://fact.png")
        image = discord.File(
            await (await self.alex_api.facts(text=text)).read(), "fact.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!scroll <text>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def scroll(self, ctx, *, text: str):
        """
        The scroll of truth!
        """
        if len(text) > 40:
            return await ctx.send(
                "The file you tried to render was over 40 characters! Please try again!"
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://scroll.png")
        image = discord.File(
            await (await self.alex_api.scroll(text=text)).read(), "scroll.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!calling <text>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def calling(self, ctx, *, text: str):
        """
        Tom calling whatever.
        """
        if len(text) > 70:
            return await ctx.send(
                "The file you tried to render was over 70 characters! Please try again!"
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://call.png")
        image = discord.File(
            await (await self.alex_api.calling(text=text)).read(), "call.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!salty <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def salty(self, ctx, user: discord.Member = None):
        """
        Comparable to the amount of salt on the Atlantic Ocean
        """
        if not user:
            user = ctx.author

        embed = discord.Embed(colour=EMBED_COLOUR, title=f"{':salt:'*7}").set_image(
            url="attachment://salty.png"
        )
        embed.set_footer(
            text=f"{ctx.author.name} > {user.name} | Powered by ponbus.com"
        )
        image = discord.File(
            await (await self.alex_api.salty(image=user.avatar_url)).read(), "salty.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!shame <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def shame(self, ctx, user: discord.Member = None):
        """
        The dock of shame.
        """
        if not user:
            user = ctx.author

        embed = discord.Embed(colour=EMBED_COLOUR, title=f"Dock of shame.").set_image(
            url="attachment://shame.png"
        )
        embed.set_footer(
            text=f"{ctx.author.name} > {user.name} | Powered by ponbus.com"
        )
        image = discord.File(
            await (await self.alex_api.shame(image=user.avatar_url)).read(), "shame.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!captcha <text>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def captcha(self, ctx, *, text: str):
        """
        Funny captcha image hahaha
        """
        if len(text) > 25:
            return await ctx.send(
                "The file you tried to render was over 25 characters! Please try again!"
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://captcha.png")
        image = discord.File(
            await (await self.alex_api.captcha(text=text)).read(), "captcha.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!hex <code>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def hex(self, ctx, hex: str):
        """
        Get color information from hex string.
        """
        try:
            if len(hex) == 6:
                colorinf = await self.alex_api.colour(colour=hex)
                embed = discord.Embed(colour=EMBED_COLOUR, title=f"{colorinf.name}")
                embed.set_image(url=colorinf.image)
                embed.set_footer(
                    text=f"Rendered by {ctx.author} | Powered by ponbus.com"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    "A hex color code without transparency is composed of 6 characters, no more, no less."
                )
        except:
            await ctx.send(
                f"Failed to obtain color information. Maybe {hex} isn't a valid code."
            )

    @commands.command(usage="`tp!hub <text1> <text2>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def hub(self, ctx, text1, text2):
        """
        Hehe.
        """
        if len(text1) > 10 or len(text2) > 10:
            return await ctx.send(
                "One or both words for the file you tried to render were over 10 characters! Please try again."
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://hub.png")
        image = discord.File(
            await (await self.alex_api.pornhub(text=text1, text2=text2)).read(),
            "hub.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!achievement <text>`", aliases=["ach"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def achievement(self, ctx, *, text: str):
        """
        Le minecraft achievement has arrived.
        """
        if len(text) > 30:
            return await ctx.send(
                "The file you tried to render was over 30 characters! Please try again!"
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://achievment.png")
        image = discord.File(
            await (await self.alex_api.achievement(text=text, icon=46)).read(),
            "achievment.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!challenge <text>`", aliases=["ch"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def challenge(self, ctx, *, text: str):
        """
        Le minecraft challenge has arrived.
        """
        if len(text) > 40:
            return await ctx.send(
                "The file you tried to render was over 40 characters! Please try again!"
            )
        embed = discord.Embed(
            colour=EMBED_COLOUR, title=f"Rendered by {ctx.author}"
        ).set_image(url="attachment://challenge.png")
        image = discord.File(
            await (await self.alex_api.challenge(text=text, icon=46)).read(),
            "challenge.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command(usage="`tp!pp <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def pp(self, ctx, *, user: discord.Member = None):
        """See how much someone is packing :flushed:"""
        user = user or ctx.author
        if user.id == 318483487231574016:

            embedd = discord.Embed(colour=EMBED_COLOUR)
            embedd.add_field(name=f"{user.name}'s pp size", value="Non-Existent")
            await ctx.reply(embed=embedd)
            return
        if user.id == 101118549958877184:
            embedd = discord.Embed(colour=EMBED_COLOUR)
            mot = "=" * 100
            embedd.add_field(name=f"{user.name}'s pp size", value=f"8{mot}D")
            await ctx.reply(embed=embedd)
            return

        if user.id == 367448341103247360:
            embedd = discord.Embed(colour=EMBED_COLOUR)
            obed = "=" * 100
            embedd.add_field(name=f"{user.name}'s pp size", value=f"8{obed}D")
            await ctx.reply(embed=embedd)
            return

        if user.id == 468373112841306112:
            embedd = discord.Embed(colour=EMBED_COLOUR)
            embedd.add_field(
                name=f"{user.name}'s pp size",
                value="Literally a vagina. Literally inverted.",
            )
            await ctx.reply(embed=embedd)
            return

        else:
            final = "=" * random.randrange(15)
            value = f"8{final}D"
            if final == "":
                value = "Doesn't exist."
            # final = '=' * (user.id % 15)
            embed = discord.Embed(
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
                url=f"{Website}",
            )
            embed.add_field(name=f"{user.name}'s pp size", value=value)
            await ctx.reply(embed=embed)

    @commands.guild_only()
    @commands.bot_has_permissions(add_reactions=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(aliases=["tic", "tictac", "tictactoe"], usage="`tp!ttt`")
    async def ttt(self, ctx, move=""):
        """Tic Tac Toe"""
        await self.ttt_new(ctx.author, ctx.channel)

    async def ttt_new(self, user, channel):
        self.ttt_games[user.id] = [" "] * 9
        response = self._make_board(user)
        response += "Your move:"
        msg = await channel.send(response)
        await self._make_buttons(msg)

    async def ttt_move(self, user, message, move):
        print(f"{default.date()} | ttt_move:{user.id}")
        # Check user currently playing
        if user.id not in self.ttt_games:
            print(f"{default.date()} | New ttt game")
            return await self.ttt_new(user, message.channel)

        # Check spot is empty
        if self.ttt_games[user.id][move] == " ":
            self.ttt_games[user.id][move] = "x"
            print(f"{default.date()} | Moved to {move}")
        else:
            print(f"{default.date()} | Invalid move: {move}")
            return None

        # Check winner
        check = self._do_checks(self.ttt_games[user.id])
        if check is not None:
            msg = "It's a draw!" if check == "draw" else f"{check[-1]} wins!"
            print(f"{default.date()} | {msg}")
            await message.edit(content=f"{self._make_board(user)}{msg}")
            return None
        print(f"{default.date()} | Check passed")

        # AI move
        mv = self._ai_think(self._matrix(self.ttt_games[user.id]))
        self.ttt_games[user.id][self._coords_to_index(mv)] = "o"
        print(f"{default.date()} | AI moved")

        # Update board
        await message.edit(content=self._make_board(user))
        print(f"{default.date()} | Board updated")

        # Check winner again
        check = self._do_checks(self.ttt_games[user.id])
        if check is not None:
            msg = "It's a draw!" if check == "draw" else f"{check[-1]} wins!"
            print(f"{default.date()} | {msg}")
            await message.edit(content=f"{self._make_board(user)}{msg}")
        print(f"{default.date()} | Check passed")

    def _make_board(self, author):
        return f"{author.mention}\n{self._table(self.ttt_games[author.id])}\n"

    async def _make_buttons(self, msg):
        await msg.add_reaction("\u2196")  # 0 tl
        await msg.add_reaction("\u2B06")  # 1 t
        await msg.add_reaction("\u2197")  # 2 tr
        await msg.add_reaction("\u2B05")  # 3 l
        await msg.add_reaction("\u23FA")  # 4 mid
        await msg.add_reaction("\u27A1")  # 5 r
        await msg.add_reaction("\u2199")  # 6 bl
        await msg.add_reaction("\u2B07")  # 7 b
        await msg.add_reaction("\u2198")  # 8 br

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.message.guild is None:
            return
        if reaction.message.author != self.bot.user:
            return
        game_session = self.ttt_games.get(user.id, None)
        if game_session is None:
            return
        move = self._decode_move(str(reaction.emoji))
        if move is None:
            return
        await self.ttt_move(user, reaction.message, move)

    @staticmethod
    def _decode_move(emoji):
        dict = {
            "\u2196": 0,
            "\u2B06": 1,
            "\u2197": 2,
            "\u2B05": 3,
            "\u23FA": 4,
            "\u27A1": 5,
            "\u2199": 6,
            "\u2B07": 7,
            "\u2198": 8,
        }
        return dict[emoji] if emoji in dict else None

    @staticmethod
    def _table(xo):
        return (
            (("%s%s%s\n" * 3) % tuple(xo))
            .replace("o", ":o2:")
            .replace("x", ":regional_indicator_x:")
            .replace(" ", ":white_large_square:")
        )

    @staticmethod
    def _matrix(b):
        return [[b[0], b[1], b[2]], [b[3], b[4], b[5]], [b[6], b[7], b[8]]]

    @staticmethod
    def _coords_to_index(coords):
        map = {
            (0, 0): 0,
            (0, 1): 1,
            (0, 2): 2,
            (1, 0): 3,
            (1, 1): 4,
            (1, 2): 5,
            (2, 0): 6,
            (2, 1): 7,
            (2, 2): 8,
        }
        return map[coords]

    def _do_checks(self, b):
        m = self._matrix(b)
        if self._check_win(m, "x"):
            return "win X"
        if self._check_win(m, "o"):
            return "win O"
        if self._check_draw(b):
            return "draw"
        return None

    # The following comes from an old project
    # https://gist.github.com/HizkiFW/0aadefb73e71794fb4a2802708db5bcf
    @staticmethod
    def _find_streaks(m, xo):
        row = [0, 0, 0]
        col = [0, 0, 0]
        dia = [0, 0]

        # Check rows and columns for X streaks
        for y in range(3):
            for x in range(3):
                if m[y][x] == xo:
                    row[y] += 1
                    col[x] += 1

        # Check diagonals
        if m[0][0] == xo:
            dia[0] += 1
        if m[1][1] == xo:
            dia[0] += 1
            dia[1] += 1
        if m[2][2] == xo:
            dia[0] += 1
        if m[2][0] == xo:
            dia[1] += 1
        if m[0][2] == xo:
            dia[1] += 1

        return (row, col, dia)

    @staticmethod
    def _find_empty(matrix, rcd, n):
        # Rows
        if rcd == "r":
            for x in range(3):
                if matrix[n][x] == " ":
                    return x
        # Columns
        if rcd == "c":
            for x in range(3):
                if matrix[x][n] == " ":
                    return x
        # Diagonals
        if rcd == "d":
            if n == 0:
                for x in range(3):
                    if matrix[x][x] == " ":
                        return x
            else:
                for x in range(3):
                    if matrix[x][2 - x] == " ":
                        return x

        return False

    def _check_win(self, m, xo):
        row, col, dia = self._find_streaks(m, xo)
        dia.append(0)

        for i in range(3):
            if row[i] == 3 or col[i] == 3 or dia[i] == 3:
                return True

        return False

    @staticmethod
    def _check_draw(board):
        return not " " in board

    def _ai_think(self, m):
        rx, cx, dx = self._find_streaks(m, "x")
        ro, co, do = self._find_streaks(m, "o")

        mv = self._ai_move(2, m, ro, co, do)
        if mv is not False:
            return mv
        mv = self._ai_move(2, m, rx, cx, dx)
        if mv is not False:
            return mv
        mv = self._ai_move(1, m, ro, co, do)
        if mv is not False:
            return mv
        return self._ai_move(1, m, rx, cx, dx)

    def _ai_move(self, n, m, row, col, dia):
        for r in range(3):
            if row[r] == n:
                x = self._find_empty(m, "r", r)
                if x is not False:
                    return (r, x)
            if col[r] == n:
                y = self._find_empty(m, "c", r)
                if y is not False:
                    return (y, r)

        if dia[0] == n:
            y = self._find_empty(m, "d", 0)
            if y is not False:
                return (y, y)
        if dia[1] == n:
            y = self._find_empty(m, "d", 1)
            if y is not False:
                return (y, 2 - y)

        return False

    KAOMOJI_JOY = [
        " (\\* ^ ω ^)",
        " (o^▽^o)",
        " (≧◡≦)",
        ' ☆⌒ヽ(\\*"､^\\*)chu',
        " ( ˘⌣˘)♡(˘⌣˘ )",
        " xD",
    ]
    KAOMOJI_EMBARRASSED = [
        " (⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)..",
        " (\\*^.^\\*)..,",
        "..,",
        ",,,",
        "... ",
        ".. ",
        " mmm..",
        "O.o",
    ]
    KAOMOJI_CONFUSE = [" (o_O)?", " (°ロ°) !?", " (ーー;)?", " owo?"]
    KAOMOJI_SPARKLES = [" \\*:･ﾟ✧\\*:･ﾟ✧ ", " ☆\\*:・ﾟ ", "〜☆ ", " uguu.., ", "-.-"]

    @commands.command(aliases=["owo"], usage="`tp!uwu <Optional:text>`")
    async def uwu(self, ctx: commands.Context, *, text: str = None):
        """Uwuize the replied to message, previous message, or your own text."""
        if not text:
            if hasattr(ctx.message, "reference") and ctx.message.reference:
                try:
                    text = (
                        await ctx.fetch_message(ctx.message.reference.message_id)
                    ).content
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
            if not text:
                text = (await ctx.channel.history(limit=2).flatten())[
                    1
                ].content or "I can't translate that!"
        await type_message(
            ctx.channel,
            self.uwuize_string(text),
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False
            ),
        )

    def uwuize_string(self, string: str):
        """Uwuize and return a string."""
        converted = ""
        current_word = ""
        for letter in string:
            if letter.isprintable() and not letter.isspace():
                current_word += letter
            elif current_word:
                converted += self.uwuize_word(current_word) + letter
                current_word = ""
            else:
                converted += letter
        if current_word:
            converted += self.uwuize_word(current_word)
        return converted

    def uwuize_word(self, word: str):
        """Uwuize and return a word.
        Thank you to the following for inspiration:
        https://github.com/senguyen1011/UwUinator
        """
        word = word.lower()
        uwu = word.rstrip(".?!,")
        punctuations = word[len(uwu) :]
        final_punctuation = punctuations[-1] if punctuations else ""
        extra_punctuation = punctuations[:-1] if punctuations else ""

        # Process punctuation
        if final_punctuation == "." and not random.randint(0, 3):
            final_punctuation = random.choice(self.KAOMOJI_JOY)
        if final_punctuation == "?" and not random.randint(0, 2):
            final_punctuation = random.choice(self.KAOMOJI_CONFUSE)
        if final_punctuation == "!" and not random.randint(0, 2):
            final_punctuation = random.choice(self.KAOMOJI_JOY)
        if final_punctuation == "," and not random.randint(0, 3):
            final_punctuation = random.choice(self.KAOMOJI_EMBARRASSED)
        if final_punctuation and not random.randint(0, 4):
            final_punctuation = random.choice(self.KAOMOJI_SPARKLES)

        # Full word exceptions
        if uwu in ("you're", "youre"):
            uwu = "ur"
        elif uwu == "fuck":
            uwu = "fwickk"
        elif uwu == "fucking":
            uwu = "fwicking"
        elif uwu == "shit":
            uwu = "poopoo"
        elif uwu == "bitch":
            uwu = "meanie"
        elif uwu == "asshole":
            uwu = "b-butthole"
        elif uwu in ("dick", "penis"):
            uwu = "peenie"
        elif uwu in ("cum", "semen"):
            uwu = "cummies"
        elif uwu == "ass":
            uwu = "boi pussy"
        elif uwu in ("dad", "father"):
            uwu = "daddy"
        elif uwu in ("mom", "mother"):
            uwu = "mommy"
        # Normal word conversion
        else:
            # Protect specific word endings from changes
            protected = ""
            if (
                uwu.endswith("le")
                or uwu.endswith("ll")
                or uwu.endswith("er")
                or uwu.endswith("re")
            ):
                protected = uwu[-2:]
                uwu = uwu[:-2]
            elif (
                uwu.endswith("les")
                or uwu.endswith("lls")
                or uwu.endswith("ers")
                or uwu.endswith("res")
            ):
                protected = uwu[-3:]
                uwu = uwu[:-3]
            # l -> w, r -> w, n<vowel> -> ny<vowel>, ove -> uv
            uwu = (
                uwu.replace("l", "w")
                .replace("r", "w")
                .replace("na", "nya")
                .replace("ne", "nye")
                .replace("ni", "nyi")
                .replace("no", "nyo")
                .replace("nu", "nyu")
                .replace("ove", "uv")
                + protected
            )

        # Add back punctuations
        uwu += extra_punctuation + final_punctuation

        # Add occasional stutter
        if (
            len(uwu) > 2
            and uwu[0].isalpha()
            and "-" not in uwu
            and not random.randint(0, 6)
        ):
            uwu = f"{uwu[0]}-{uwu}"

        return uwu

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(hidden=True)
    async def troll(self, ctx):
        await ctx.send(
            """

⣿⣿⣿⣿⣿⣿⣿⣿⠟⠋⠁⠄⠄⠄⠄⠄⠄⠄⠄⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⡟⠁⠄⠄⠄⠄⣠⣤⣴⣶⣶⣶⣶⣤⡀⠈⠙⢿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⡟⠄⠄⠄⠄⠄⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣆⠄⠈⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⠁⠄⠄⠄⢀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠄⠄⢺⣿⣿⣿⣿
⣿⣿⣿⣿⣿⡄⠄⠄⠄⠙⠻⠿⣿⣿⣿⣿⠿⠿⠛⠛⠻⣿⡄⠄⣾⣿⣿⣿⣿
⣿⣿⣿⣿⣿⡇⠄⠄⠁        ⠄⢹⣿⡗⠄        ⢄⡀⣾⢀⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⡇⠘⠄⠄⠄⢀⡀⠄⣿⣿⣷⣤⣤⣾⣿⣿⣿⣧⢸⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⡇⠄⣰⣿⡿⠟⠃⠄⣿⣿⣿⣿⣿⡛⠿⢿⣿⣷⣾⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⡄⠈⠁⠄⠄⠄⠄⠻⠿⢛⣿⣿⠿⠂⠄⢹⢹⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⡐⠐⠄⠄⣠⣀⣀⣚⣯⣵⣶⠆⣰⠄⠞⣾⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣷⡄⠄⠄⠈⠛⠿⠿⠿⣻⡏⢠⣿⣎⣾⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⡿⠟⠛⠄⠄⠄⠄⠙⣛⣿⣿⣵⣿⡿⢹⡟⣿⣿⣿⣿⣿⣿⣿
⣿⠿⠿⠋⠉⠄⠄⠄⠄⠄⠄⠄⣀⣠⣾⣿⣿⣿⡟⠁⠹⡇⣸⣿⣿⣿⣿⣿⣿
⠁⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠙⠿⠿⠛⠋⠄⣸⣦⣠⣿⣿⣿⣿⣿⣿⣿
"""
        )

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    async def virgin(self, ctx):
        user = ctx.author.name
        await ctx.reply(
            f"<@626528672249151538> (Cold#1338) is a virgin, we all know this {user}."
        )

    # @commands.command(usage="`tp!remind <time>`")
    # @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    # async def remind(self, ctx, time: str, *, reminder: str = None):
    #     """ Set a reminder for yourself.
    #     If you want to provide multiple times, encase in quotes, such as:
    #         tp!remind "1h 20m" Pizza time!
    #     Can take days (1d), hours (3h), minutes (44m), or seconds (32s)
    #     Max time provision of weeks (2w)
    #     """

    #     remind_str = ""
    #     secs = 0

    #     for item in time.split():
    #         secs = self.convert_to_seconds(item) + secs

    #     secs_as_timedelta = datetime.timedelta(seconds=secs)

    #     if secs == 0:
    #         return ctx.reply("Hmm. Looks like you didn't provide a valid time. Please try again.")
    #     embed = discord.Embed(
    #         colour=ctx.author.color,
    #         timestamp=ctx.message.created_at,
    #         title=f'You will be reminded in {str(secs_as_timedelta)}',
    #         url=f"{Website}",
    #         description=reminder
    #     )
    #     await ctx.reply(embed=embed)
    #     await asyncio.sleep(secs)

    #     if reminder is not None:
    #         remind_str = f" - {reminder}"

    #     remind_message = discord.Embed(
    #         colour=ctx.author.color,
    #         title=f'Reminder{remind_str}!'
    #     )
    #     try:
    #         await ctx.author.send(embed=remind_message)
    #     except discord.Forbidden:
    #         await ctx.reply(f'{ctx.author.mention}', embed=remind_message)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
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
        mem = ctx.author
        try:
            problem = str(ctx.message.clean_content.replace(f"{ctx.prefix}math", ""))
            # If a problem isn't given
            if problem == "":
                e = discord.Embed(
                    description=f"Actually put something for me to solve...",
                    color=discord.Colour.red(),
                )
                await ctx.reply(embed=e)
                return
            #    If the user's problem is too long
            if len(problem) > 500:
                e = discord.Embed(description=f"Too long, try again.", color=0x3498DB)
                await ctx.reply(embed=e)
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
                        color=discord.Colour.red(),
                    )
                    await ctx.reply(embed=e)
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
            e.set_footer(text=mem, icon_url=mem.avatar_url)
            #    Send embed
            await ctx.reply(embed=e)
        # If the problem is unsolvable
        except Exception:
            e = discord.Embed(
                description=f"Either the problem couldn't be solved or something happened, report it to the devs either way.",
                color=discord.Colour.red(),
            )
            await ctx.reply(embed=e)

    @commands.command(hidden=True, usage="`tp!covid`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def covid(self, ctx, country_code="Global"):
        """Covid stats. Provide a country via it's ISO code.
        Common codes:
                US: United States
                GB: Great Britan,
                CN: China,
                FR: France,
                DE: Germany
        https://countrycode.org/"""

        embed = discord.Embed(
            title="Covid statistics",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            colour=EMBED_COLOUR,
            url=f"{Website}",
        )

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
        await ctx.reply(embed=embed)

    # @commands.cooldown(3, 8, commands.BucketType.user)
    # @commands.command(usage="`tp!chat <msg>`")
    # async def chat(self, ctx: commands.Context, *, message: str = None):
    #     """New and **improved** chat bot! """
    #     BASE_URL = f"http://api.brainshop.ai/get?bid={BID}&key={CHAT_API_KEY}"
    #     async with ctx.channel.typing():
    #         if message is None:
    #             ctx.command.reset_cooldown(ctx)
    #             return await ctx.reply(
    #                 f"Hello! In order to chat with me use: `{ctx.prefix}chat <message>`"
    #             )

    #         async with aiohttp.ClientSession() as s:
    #             async with s.get(f"{BASE_URL}&uid={ctx.author.id}&msg={message}") as r:
    #                 if r.status != 200:
    #                     return await ctx.reply(f"An error occured while accessing the chat API!")
    #                 j = await r.json()
    #                 await ctx.reply(j['cnt'], mention_author=True)

    # @commands.Cog.listener(name="on_message")
    # async def autochat(self, message: discord.Message):
    #     chat_channel_id = 859776178108497920
    #     if message.author.bot:
    #         return
    #     if message.content == "":
    #         return
    #     if message.channel.id == chat_channel_id:
    #         ctx = await self.bot.get_context(message)
    #         await ctx.invoke(self.bot.get_command('chat'), message=message.content)

    @commands.command(usage="`tp!mock <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def mock(
        self,
        ctx: commands.Context,
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
        if isinstance(msg, str):
            print(f"{default.date()} | Mocking a given string")
            result = await self.cap_change(str(msg))
            result += f"\n\n[Mocking Message]({ctx.message.jump_url})"
            author = ctx.message.author
        elif isinstance(msg, discord.Member):
            print(f"{default.date()} | Mocking a user")
            total_msg = ""
            async for message in ctx.channel.history(limit=10):
                if message.author == msg:
                    total_msg += message.content + "\n"
            result = await self.cap_change(total_msg)
            author = msg
        elif isinstance(msg, discord.Message):
            print(f"{default.date()} | Mocking a message")
            result = await self.cap_change(msg.content)
            result += f"\n\n[Mocking Message]({msg.jump_url})"
            author = msg.author
            search_msg = msg
        else:
            print(f"{default.date()} | Mocking last message in chat")
            async for message in ctx.channel.history(limit=2):
                search_msg = message
            author = search_msg.author
            result = await self.cap_change(search_msg.content)
            result += f"\n\n[Mocking Message]({search_msg.jump_url})"
            if result == "" and len(search_msg.embeds) != 0:
                if search_msg.embeds[0].description != discord.Embed.Empty:
                    result = await self.cap_change(search_msg.embeds[0].description)
        time = ctx.message.created_at
        embed = discord.Embed(
            description=result, timestamp=ctx.message.created_at, url=f"{Website}"
        )
        embed.colour = getattr(author, "colour", discord.Colour.default())
        embed.set_author(name=author.display_name, icon_url=author.avatar_url)
        embed.set_thumbnail(url="https://i.imgur.com/upItEiG.jpg")
        embed.set_footer(
            text=f"{ctx.message.author.display_name} mocked {author.display_name}",
            icon_url=ctx.message.author.avatar_url,
        )
        if hasattr(msg, "attachments") and search_msg.attachments != []:
            embed.set_image(url=search_msg.attachments[0].url)
        if not ctx.channel.permissions_for(ctx.me).embed_links:
            if author != ctx.message.author:
                await ctx.reply(f"{result} - {author.mention}")
            else:
                await ctx.reply(result)
        else:
            await ctx.reply(embed=embed)
            if author != ctx.message.author:
                await ctx.send(f"- {author.mention}")

    @commands.command(aliases=["8ball"], usage="`tp!8ball <question>`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def eightball(self, ctx, *, question: commands.clean_content):
        """Ask 8ball"""

        answer = random.choice(lists.ballresponse)
        await ctx.reply(f"🎱 **Question:** {question}\n**Answer:** {answer}")

    async def randomimageapi(self, ctx, url, endpoint):
        try:
            r = await http.get(url, res_method="json", no_cache=True)
        except aiohttp.ClientConnectorError:
            return await ctx.reply("The API seems to be down...")
        except aiohttp.ContentTypeError:
            return await ctx.reply("The API returned an error or didn't return JSON...")

        await ctx.reply(r[endpoint])

    async def api_img_creator(self, ctx, url, filename, content=None):
        async with ctx.channel.typing():
            req = await http.get(url, res_method="read")

            if req is None:
                return await ctx.reply("I couldn't create the image")

            bio = BytesIO(req)
            bio.seek(0)
            await ctx.reply(content=content, file=discord.File(bio, filename=filename))

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(aliases=["hit", "punch", "yeet"], usage="`tp!slap <user>`")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def slap(self, ctx, *, user: discord.Member):
        """Slap people"""
        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} hits themselves lol...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("slap"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} hits {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("slap"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(usage="`tp!poke <user>`")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def poke(self, ctx, *, user: discord.Member):
        """Poke people"""
        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} pokes themselves, why...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("poke"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} pokes {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("poke"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(usage="`tp!bred`", hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    async def pot(self, ctx):
        embed = discord.Embed(title="bred")
        embed.add_field(
            name="How'd you find this lol",
            value=f"[Don't click me :flushed:](https://www.youtube.com/watch?v=MwMuEBhgNNE&ab_channel=ShelseaO%27Hanlon)",
        )
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(aliases=["cuddle", "love", "hold"], usage="`tp!hug <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def hug(self, ctx, *, user: discord.Member):
        """Hug people"""
        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} hugs themselves, how sad...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("hug"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} hugs {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("hug"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(usage="`tp!kiss <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def kiss(self, ctx, *, user: discord.Member):
        """Kiss people"""
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
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("kiss"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)
        else:
            cute = ["awww", "adorable", "cute"]
            embed = discord.Embed(
                title=f"{ctx.author.name} kisses {user.name}... {random.choice(cute)}",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("kiss"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(usage="`tp!smug`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def smug(self, ctx, *, user: discord.Member = None):
        """Look smug"""
        user = user or ctx.author
        embed = discord.Embed(
            title=f"{ctx.author} is smug...",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            url=f"{Website}",
            colour=EMBED_COLOUR,
            timestamp=ctx.message.created_at,
        )

        embed.set_image(url=nekos.img("smug"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(usage="`tp!pat <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def pat(self, ctx, *, user: discord.Member):
        """Pat people"""
        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} pats themselves, kinda sad tbh...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("pat"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} patted {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("pat"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(usage="`tp!tickle <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def tickle(self, ctx, *, user: discord.Member):
        """Tickle people"""
        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author.name} tickles themselves, gross...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("tickle"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{ctx.author.name} tickled {user.name}...",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url=nekos.img("tickle"))
            embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(usage="`tp!kill <user>`", aliases=["jump", "murder", "slay"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def kill(self, ctx, *, user: discord.Member):
        """Kill someone"""
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
        ]
        if user == ctx.author:
            embed = discord.Embed(
                title=f"Okay you've killed yourself {ctx.author.name}, I hope this was worth it! Now tag someone else to kill them!",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{random.choice(kill_msg)}",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            await ctx.reply(embed=embed)

    @commands.guild_only()
    @commands.command(usage="`tp!meme`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def meme(self, ctx, content=None):
        """sends you the dankest of the dank memes from reddit"""

        async with ctx.channel.typing():
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
                return await ctx.reply(url)
            elif "https://streamable.com/" in url:
                return
            elif "https://i.imgur.com/" in url:
                return await ctx.reply(url)
            elif "https://gfycat.com/" in url:
                return await ctx.reply(url)
            elif "https://imgflip.com/gif/" in url:
                return await ctx.reply(url)
            elif "https://youtu.be/" in url:
                return await ctx.reply(url)
            elif "https://youtube.com/" in url:
                return await ctx.reply(url)
            embed = discord.Embed(
                title=name,
                url=url,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            )
            embed.set_image(url=url)
            embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(content="Alright, have this meme.", embed=embed)

    @commands.guild_only()
    @commands.command(usage="`tp!okbr`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_nsfw()
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def okbr(self, ctx, content=None):
        """Okay buddy. Retard."""

        async with ctx.channel.typing():
            subs = ["okaybuddyretard"]
            subreddit = await self.reddit.subreddit(random.choice(subs))
            all_subs = []
            top = subreddit.hot(limit=50)
            async for submission in top:
                all_subs.append(submission)
            random_sub = random.choice(all_subs)
            name = random_sub.title
            url = random_sub.url
            if "https://v" in url:
                return await ctx.reply(url)
            elif "https://streamable.com/" in url:
                return
            elif "https://i.imgur.com/" in url:
                return await ctx.reply(url)
            elif "https://gfycat.com/" in url:
                return await ctx.reply(url)
            elif "https://imgflip.com/gif/" in url:
                return await ctx.reply(url)
            embed = discord.Embed(
                title=name,
                url=url,
                colour=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            )
            embed.set_image(url=url)
            embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.reply(
                content="HAHA OH MY GOD THAT IS SO FUNNY!!!! <:stfupls:880141007029669979>",
                embed=embed,
            )

    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(usage="`tp!hack <user>`")
    async def hack(self, ctx, user: discord.Member = None):
        """Hack a user, totally real and legit"""
        if user == None:
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
                f"{self.bot.user.name} is the best bot",
                "im kinda gay tbh",
                "bro dont make fun of my small penis",
                "https://youtu.be/iik25wqIuFo",
                "lmfao you kinda ugly",
                "pls no",
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
            ]

            latest_DM = f"{random.choice(DMs)}"

            ip_address = f"690.4.2.0:{random.randint(1000, 9999)}"

            Discord_Servers = [
                "Virgins Only",
                "No friends gang",
                "Gaymers Together",
                "FuckShit",
                "Anxiety Zone",
                "Cawk",
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
                await ctx.send(
                    f"{user.name} has successfully been hacked. <a:EpicTik:816846395302477824>\n\n**{user.name}**'s Data:\nDiscord Email: `{email_address}`\nDiscord Password: `{password}`\nMost used Discord Server: `{Most_Used_Discord_Server}`\nIP Address: `{ip_address}`\nLatest DM: `{latest_DM}`"
                )

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(aliases=["doggo", "pupper", "puppy"], usage="`tp!dog`")
    @commands.bot_has_permissions(embed_links=True)
    async def dog(self, ctx: commands.Context):
        """Puppers"""
        embed = discord.Embed(
            title="Aw, doggo",
            url=f"{Website}",
            colour=EMBED_COLOUR,
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            timestamp=ctx.message.created_at,
        )

        embed.set_image(url=nekos.img("woof"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.command(usage="`tp!birb`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def birb(self, ctx: commands.Context):
        """Its really just geese"""
        embed = discord.Embed(
            title="H o n k",
            colour=EMBED_COLOUR,
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            timestamp=ctx.message.created_at,
            url=f"{Website}",
        )

        embed.set_image(url=nekos.img("goose"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.bot_has_permissions(add_reactions=True)
    async def pressf(self, ctx, *, user: discord.User = None):
        """Pay respects by pressing F"""
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
                return await ctx.send("You took too long to reply.")

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
    async def FtoPayRespects(self, reaction, user):
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

    @commands.command(usage="`tp!lenny`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def lenny(self, ctx):
        """( ͡° ͜ʖ ͡°)"""

        await ctx.reply(f"( ͡° ͜ʖ ͡°)")

    @commands.command(usage="`tp!urban <search>`")
    @commands.is_nsfw()
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def urban(self, ctx, *, search: commands.clean_content):
        """Find the 'best' definition to your words"""

        async with ctx.channel.typing():
            try:
                url = await http.get(
                    f"https://api.urbandictionary.com/v0/define?term={search}",
                    res_method="json",
                )
            except Exception:
                return await ctx.reply(
                    "Urban API returned invalid data... might be down atm."
                )

            if not url:
                return await ctx.reply("I think the API broke...")

            if not len(url["list"]):
                return await ctx.reply("Couldn't find your search in the dictionary...")

            result = sorted(
                url["list"], reverse=True, key=lambda g: int(g["thumbs_up"])
            )[0]

            definition = result["definition"]
            if len(definition) >= 1000:
                definition = definition[:1000]
                definition = definition.rsplit(" ", 1)[0]
                definition += "..."

            await ctx.reply(
                f"📚 Definitions for **{result['word']}**```fix\n{definition}```"
            )

    @commands.command(hidden=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def coom(self, ctx):
        await ctx.reply("https://www.youtube.com/watch?v=yvWUDNsZXwA")

    @commands.command(usage="`tp!sussy`", hidden=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def sussy(self, ctx):
        await ctx.send(
            """
⠀       ⠀⠀⠀⣠⠤⠖⠚⠛⠉⠛⠒⠒⠦⢤
⠀⠀⠀⠀⣠⠞⠁⠀⠀⠠⠒⠂⠀⠀⠀⠀⠀⠉⠳⡄
⠀⠀⠀⢸⠇⠀⠀⠀⢀⡄⠤⢤⣤⣤⡀⢀⣀⣀⣀⣹⡄
⠀⠀⠀⠘⢧⠀⠀⠀⠀⣙⣒⠚⠛⠋⠁⡈⠓⠴⢿⡿⠁
⠀⠀⠀⠀⠀⠙⠒⠤⢀⠛⠻⠿⠿⣖⣒⣁⠤⠒⠋
⠀⠀⠀⠀⠀⢀⣀⣀⠼⠀⠈⣻⠋⠉⠁ A M O G U S
⠀⠀⠀⡴⠚⠉⠀⠀⠀⠀⠀⠈⠀⠐⢦
⠀⠀⣸⠃⠀⡴⠋⠉⠀⢄⣀⠤⢴⠄⠀⡇
⠀⢀⡏⠀⠀⠹⠶⢀⡔⠉⠀⠀⣼⠀⠀⡇
⠀⣼⠁⠀⠙⠦⣄⡀⣀⡤⠶⣉⣁⣀⠘
⢀⡟⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⣽
⢸⠇⠀⠀⠀⢀⡤⠦⢤⡄⠀⠀⡟
⢸⠀⠀⠀⠀⡾⠀⠀⠀⡿⠀⠀⣇⣀⣀
⢸⠀⠀⠈⠉⠓⢦⡀⢰⣇⡀⠀⠉⠀⠀⣉⠇
⠈⠓⠒⠒⠀⠐⠚⠃⠀⠈⠉⠉⠉⠉⠉⠁
"""
        )

    @commands.command(usage="`tp!reverse <text>`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def reverse(self, ctx, *, text: str):
        """Reverses Shit"""

        t_rev = text[::-1].replace("@", "@‎").replace("&", "&‎")
        await ctx.reply(f"🔁 {t_rev}")

    @commands.command(usage="`tp!password <optional:bytes>`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def password(self, ctx, nbytes: int = 40):
        """Generates a random password string for you
        This returns a random URL-safe text string, containing nbytes random bytes.
        The text is Base64 encoded, so on average each byte results in approximately 1.3 characters.
        """

        if nbytes not in range(3, 1001):
            return await ctx.reply("I only accept any numbers between 3-1000")
        if hasattr(ctx, "guild") and ctx.guild is not None:
            await ctx.reply(
                f"Alright, lemme send you this randomly generated password {ctx.author.mention}."
            )
        await ctx.author.send(
            f"🎁 **Here is your password:**\n{secrets.token_urlsafe(nbytes)}\n\n**You could actually use this password for things too since this was completely randomly generated.**"
        )

    @commands.command(usage="`tp!rate <thing>`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def rate(self, ctx, *, thing: commands.clean_content):
        """Rates what you want"""

        rate_amount = random.uniform(0.0, 100.0)
        await ctx.reply(f"I'd rate `{thing}` a **{round(rate_amount, 4)} / 100**")

    @commands.cooldown(rate=1, per=2.5, type=commands.BucketType.user)
    @commands.command(aliases=["howhot", "hot"], usage="`tp!howhot <user>`")
    async def hotcalc(self, ctx, *, user: discord.Member = None):
        """Returns a random percent for how hot is a discord user"""
        user = user or ctx.author

        if user.id == 468373112841306112:
            return await ctx.reply(
                f"**{user.name}** Is Hotter Than Anyone Can Imagine, Don't Ever Put Yourself Down Darling, You're Amazing :)"
            )

        if user.id == 318483487231574016:
            return await ctx.reply(f"**{user.name}** is fucking dumb")

        r = random.randint(1, 100)
        hot = r / 1.17

        emoji = "💔"
        if hot > 25:
            emoji = "❤"
        if hot > 50:
            emoji = "💖"
        if hot > 75:
            emoji = "💞"

        await ctx.reply(f"**{user.name}** is **{hot:.2f}%** hot {emoji}")

    @commands.cooldown(rate=1, per=2.5, type=commands.BucketType.user)
    @commands.command(aliases=["gay", "homo", "gayrate"], usage="`tp!howgay <user>`")
    async def howgay(self, ctx, *, user: discord.Member = None):
        """Tells you how gay a user is lol."""
        user = user or ctx.author

        # if user.id == 101118549958877184:
        #    return await ctx.reply(f"**{user.name}** cant be gay, homo.")

        # if user.id == 503963293497425920:
        #    return await ctx.reply(f"**{user.name}** is not gay and he is a cool kid")

        if user.id == 723726581864071178:
            return await ctx.reply("I'm a fuckin bot lmao.")

        r = random.randint(1, 100)
        gay = r / 1.17

        emoji = "<:LMAO:838988129431191582>"
        if gay > 25:
            emoji = "<:kek:838988145550557244>"
        if gay > 50:
            emoji = "<:yikes:838988155947319337>"
        if gay > 75:
            emoji = "<:stop_pls:838988169251782666>"

        await ctx.reply(f"**{user.name}** is **{gay:.2f}%** gay {emoji}")

    @commands.cooldown(rate=1, per=2.5, type=commands.BucketType.user)
    @commands.command(aliases=["howsimp", "areyouasimp"], usage="`tp!simp <user>`")
    async def simp(self, ctx, *, user: discord.Member = None):
        """Tells you if a user is a simp lol."""
        user = user or ctx.author

        if user.id == 101118549958877184:
            return await ctx.reply(f"**{user.name}** only simps for zoe, fuck you.")

        if user.id == 503963293497425920:
            return await ctx.reply(
                f"**{user.name}** is not a simp and he is a cool kid"
            )

        if user.id == 723726581864071178:
            return await ctx.reply("I'm a fuckin bot lmao.")

        r = random.randint(1, 100)
        simp = r / 1.17

        emoji = "<:LMAO:838988129431191582>"
        if simp > 25:
            emoji = "<:kek:838988145550557244>"
        if simp > 50:
            emoji = "<:yikes:838988155947319337>"
        if simp > 75:
            emoji = "<:stop_pls:838988169251782666>"

        await ctx.reply(f"**{user.name}** is **{simp:.2f}%** simp {emoji}")

    @commands.cooldown(rate=1, per=2.5, type=commands.BucketType.user)
    @commands.command(aliases=["howhorny", "hornyrate"], usage="`tp!horny <user>`")
    async def horny(self, ctx, *, user: discord.Member = None):
        """Tells you how horny someone is :flushed:"""
        user = user or ctx.author

        if user.id == 101118549958877184:
            return await ctx.reply(
                f"**{user.name}** is super fucking horny, like constantly."
            )

        if user.id == 468373112841306112:
            return await ctx.reply(
                f"**{user.name}** is either always incredibly horny or not at all, either or ***TAKE OFF YOUR PANTS***"
            )

        if user.id == 503963293497425920:
            return await ctx.reply(f"**{user.name}** ***Horny.***")

        if user.id == 723726581864071178:
            return await ctx.reply("I'm a fuckin bot lmao.")

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

        await ctx.reply(f"**{user.name}** is **{horny:.2f}%** horny {emoji}")


def setup(bot):
    bot.add_cog(Fun(bot))
