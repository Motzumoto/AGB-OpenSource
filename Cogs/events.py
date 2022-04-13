import asyncio
from itertools import count
import random
from datetime import datetime
import aiohttp
import cronitor

import discord
from discord.ext import commands, tasks
from httpx import RequestNotRead
from index import cursor_n, mydb_n, logger, msgtracking
from utils import default
from utils.default import add_one, log
from Manager.logger import formatColor


class events(commands.Cog):
    def __init__(self, bot: commands.Bot, *args, **kwargs):
        self.bot = bot
        self.config = default.get("config.json")
        self.db_config = default.get("db_config.json")
        self.presence_loop.start()
        self.update_stats.start()
        self.post_status.start()
        self.status_page.start()
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1.0, 3.0, commands.BucketType.guild
        )
        self.loop = asyncio.get_event_loop()

        cronitor.api_key = f"{self.config.cronitor}"

    async def cog_unload(self):
        self.presence_loop.stop()
        self.update_stats.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        discord_version = discord.__version__
        log(f"Logged in as: {formatColor(str(self.bot.user), 'bold_red')}")
        log(f"Client ID: {formatColor(str(self.bot.user.id), 'bold_red')}")
        log(
            f"Client Server Count: {formatColor(str(len(self.bot.guilds)), 'bold_red')}"
        )
        log(f"Client User Count: {formatColor(str(len(self.bot.users)), 'bold_red')}")
        if len(self.bot.shards) > 1:
            log(
                f"{formatColor(str(self.bot.user), 'bold_red')} is using {formatColor(str(len(self.bot.shards)), 'green')} shards."
            )
        else:
            log(
                f"{formatColor(str(self.bot.user), 'bold_red')} is using {formatColor(str(len(self.bot.shards)), 'green')} shard."
            )
        log(f"Discord Python Version: {formatColor(f'{discord_version}', 'green')}")
        try:
            await self.bot.load_extension("jishaku")
            log(f"Loaded JSK.")
        except:
            pass
        for guild in self.bot.guilds:
            try:
                cursor_n.execute(
                    f"SELECT * FROM public.commands WHERE guild = '{guild.id}'"
                )
            except:
                pass
            cmd_rows = cursor_n.rowcount
            if cmd_rows == 0:
                cursor_n.execute(
                    f"INSERT INTO public.commands (guild) VALUES ('{guild.id}')"
                )
                mydb_n.commit()
                log(f"Added to commands table: {formatColor(f'{guild.id}', 'green')}")
            try:
                cursor_n.execute(
                    f"SELECT * FROM public.guilds WHERE guildID = '{guild.id}'"
                )
            except:
                pass
            row_count = cursor_n.rowcount
            if row_count == 0:
                cursor_n.execute(f"INSERT INTO guilds (guildId) VALUES ('{guild.id}')")
                mydb_n.commit()
                log(f"New guild detected: {guild.id} | Added to database!")
            else:
                pass

    @tasks.loop(count=None, seconds=random.randint(25, 60))
    async def presence_loop(self):
        await self.bot.wait_until_ready()
        if datetime.today().month == 10 and datetime.today().day == 3:
            await self.bot.change_presence(
                activity=discord.Game(name="Happy birthday Motz!")
            )
            return
        statuses = [
            f"tp!help | {len(self.bot.guilds)} Servers",
            f"tp!help | {len(self.bot.commands)} commands!",
            "tp!help | tp!support",
            "You can toggle commands now! | tp!toggle command",
            "ElysianVRC is cool: https://discord.gg/yCfKu7D3GD",
            "*badoop* hey look, i joined your vc",
            "*gets the rare discord ringtone*, im better than all of you",
            "today's weather is looking pretty weather-like",
            "ikea is cool",
            "i upgraded from windows 10 to doors",
            "gamers take showers? i don't think so!",
            "lets watch anime together, that would be cute",
            "tp!help | your mom lol.",
            "who invented grass, it's tasty",
            "i mistook salt for sugar, and put it in my coffee",
            "The dog goes meow, the motz goes THERES AN ERROR",
            "this status is so poggers",
            "ITS SENTIENT",
            "i drink rainwater from the walmart parking lot",
            "im a good bot, give me attention (please?)",
            "meow, im a bot? i think not! meow",
            "lets hold hands before marriage",
            "vote for me on top.gg, i love the attention",
            "im feeling a bit like a plastic bag",
            "if ur too tall, just be shorter",
            "dont be broke, just have money :)",
            "go, commit a sin",
            "go, commit a crime",
            "im committing crimes rn (and code)",
            "stupid idiot. (get roasted)",
            "i am a bot, and i am a bot",
            "I miss you cookie.",
            "Yo mamma (Laugh at this)",
            "We're really trying to be funny",
            "im gonna eat plastic :>",
            "Dm me the word tomato",
            "ok, kitten",
        ]
        # Goodbye Cookie 2012 - 06/24/2021
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing, name=random.choice(statuses)
            )
        )

    @commands.Cog.listener(name="on_message")
    async def add(self, message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.author == self.bot.user:
            return
        if message.channel.id == 929741070777069608:
            # check if the message is a number
            if message.content.isdigit():
                number = int(message.content)
                new_number = add_one(number)
                await message.channel.send(new_number)
            else:
                await message.channel.send("Please enter a number")

    # make an event to update channels with the bots server count
    @tasks.loop(count=None, minutes=15)
    async def update_stats(self):
        await self.bot.wait_until_ready()
        update_guild_count = self.bot.get_channel(948926912296804353)
        update_user_count = self.bot.get_channel(948927596018675772)
        await update_guild_count.edit(name=f"Server Count: {len(self.bot.guilds)}")
        await update_user_count.edit(name=f"User Count: {len(self.bot.users)}")

    ### DO NOT PUT THIS IN MERGED EVENT, IT WILL ONLY WORK IN ITS OWN SEPERATE EVENT. **I DO NOT KNOW WHY :D**
    ### DO NOT PUT THIS IN MERGED EVENT, IT WILL ONLY WORK IN ITS OWN SEPERATE EVENT. **I DO NOT KNOW WHY :D**
    ### XOXOXO, KISSES ~ FIFI
    @commands.Cog.listener(name="on_command")
    async def command_usage_updater(self, ctx):
        await self.bot.wait_until_ready()
        try:
            cursor_n.execute(
                f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
            )
            row = cursor_n.fetchall()

            cursor_n.execute(
                f"UPDATE public.users SET usedcmds = '{row[0][1] + 1}' WHERE userid = '{ctx.author.id}'"
            )
            # log(f"Updated userCmds for {ctx.author.id} -> {row[0][3]}")
        except:
            pass

    # @commands.Cog.listener(name="on_command")
    # async def owner_check(self, ctx):
    #     await self.bot.wait_until_ready()

    #     if ctx.author.id in self.config.owners:
    #         await ctx.command.reset_cooldown(ctx)
    #     else:
    #         pass

    @commands.Cog.listener(name="on_message")
    async def user_check(self, ctx):
        await self.bot.wait_until_ready()
        # cursor_n.execute(f"SELECT blacklisted FROM blacklist WHERE userID = {ctx.author.id}")
        # res = cursor_n.fetchall()
        # for x in res():
        #     if x[0] == "true":
        #         return print("blacklisted")
        #     else:
        # pass
        if ctx.author.bot:
            return

        try:
            cursor_n.execute(
                f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
            )
        except:
            pass
        automod_rows = cursor_n.rowcount
        if automod_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.users (userid) VALUES ('{ctx.author.id}')"
            )
            mydb_n.commit()
            log(
                f"New user detected: {formatColor(ctx.author.id, 'green')} | Added to database!"
            )

    @commands.Cog.listener(name="on_command")
    async def blacklist_check(self, ctx):
        await self.bot.wait_until_ready()
        try:
            cursor_n.execute(
                f"SELECT * FROM public.blacklist WHERE userid = '{ctx.author.id}'"
            )
        except:
            pass
        bl_rows = cursor_n.rowcount
        if bl_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.blacklist (userid, blacklisted) VALUES ('{ctx.author.id}', 'false')"
            )
            mydb_n.commit()
            logger.debug(
                f"No blacklist entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
            )

    @commands.Cog.listener(name="on_command")
    async def badge(self, ctx):
        await self.bot.wait_until_ready()
        try:
            cursor_n.execute(
                f"SELECT * FROM public.badges WHERE userid = '{ctx.author.id}'"
            )
        except:
            pass
        badges_rows = cursor_n.rowcount
        if badges_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.badges (userid) VALUES ('{ctx.author.id}')"
            )
            mydb_n.commit()

    @commands.Cog.listener(name="on_command")
    async def eco(self, ctx):
        await self.bot.wait_until_ready()
        try:
            cursor_n.execute(
                f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
            )
        except:
            pass
        eco_rows = cursor_n.rowcount
        if eco_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.usereco (userid, balance, bank) VALUES ('{ctx.author.id}', '1000', '500')"
            )
            mydb_n.commit()
            logger.debug(
                f"No economy entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
            )

    @commands.Cog.listener(name="on_command")
    async def logger_shit(self, ctx):
        await self.bot.wait_until_ready()
        if msgtracking(ctx.author.id):
            if not ctx.guild.chunked:
                await ctx.guild.chunk()

            if ctx.author.bot:
                return
            else:
                pass
            if ctx.author.id in self.config.owners:
                log(
                    f"{formatColor('[DEV]', 'bold_red')} {formatColor(ctx.author, 'red')} used command {formatColor(ctx.message.clean_content, 'grey')}"
                )
                return
            else:
                log(
                    f"{formatColor(ctx.author.id, 'grey')} used command {formatColor(ctx.message.clean_content, 'grey')}"
                )
        else:
            return

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.wait_until_ready()

        embed = discord.Embed(title="Removed from a server.", colour=0xFF0000)
        try:
            embed.add_field(
                name=f":( forced to leave a server, heres their info:",
                value=f"Server name: `{guild.name}`\n ID `{guild.id}`\n Member Count: `{guild.member_count}`.",
            )
        except:
            embed.add_field(
                name=f"This is a false error. Completely ignore this", value="NaN"
            )
            return
        embed.set_thumbnail(url=self.bot.user.avatar)
        channel = self.bot.get_channel(769080397669072939)
        if guild.name is None:
            return
        if guild.member_count is None:
            return
        await channel.send(embed=embed)
        # Remove server from database
        cursor_n.execute(f"SELECT * FROM public.guilds WHERE guildId = '{guild.id}'")
        # results = cursor_n.fetchall() # Assigned but not used
        row_count = cursor_n.rowcount
        if row_count == 0:
            log(f"Removed from: {guild.id}")
        else:
            cursor_n.execute(f"DELETE FROM guilds WHERE guildId = '{guild.id}'")
            mydb_n.commit()
            logger.warning(f"Removed from: {guild.id} | Deleting database entry!")

    @commands.Cog.listener(name="on_guild_join")
    async def MessageSentOnGuildJoin(self, guild):
        await self.bot.wait_until_ready()
        if not guild.chunked:
            await guild.chunk()
        nick = f"[tp!] {self.bot.user.name}"
        try:
            await guild.me.edit(nick=nick)
        except discord.errors.Forbidden:
            return logger.error(f"Unable to change nickname in {guild.id}")
        else:
            log(f"Changed nickname to {nick} in {guild.id}")
        embed = discord.Embed(
            title="Oi cunt, Just got invited to another server.",
            colour=discord.Colour.green(),
        )
        embed.add_field(
            name="Here's the servers' info.",
            value=f"Server name: `{guild.name}`\n ID `{guild.id}`\n Member Count: `{guild.member_count}`.",
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        channel = self.bot.get_channel(769075552736641115)
        await channel.send(embed=embed)
        # Add server to database
        cursor_n.execute(f"SELECT * FROM public.guilds WHERE guildId = '{guild.id}'")
        # results = cursor_n.fetchall() # Assigned but not used
        row_count = cursor_n.rowcount
        if row_count == 0:
            cursor_n.execute(
                f"INSERT INTO public.guilds (guildId) VALUES ('{guild.id}')"
            )
            mydb_n.commit()
            log(f"New guild joined: {guild.id} | Added to database!")
        else:
            log(f"New guild joined: {guild.id} | But it was already in the DB")

        try:
            cursor_n.execute(
                f"SELECT * FROM public.commands WHERE guild = '{guild.id}'"
            )
        except:
            pass
        cmd_rows = cursor_n.rowcount
        if cmd_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.commands (guild) VALUES ('{guild.id}')"
            )
            mydb_n.commit()

    @commands.Cog.listener(name="on_guild_join")
    async def add_ppl_on_join(self, guild):
        for member in guild.members:
            # check to see if the servers member count is over x people, and if it is, wait to add them until the next hour
            if len(guild.members) > 300:
                await asyncio.sleep(3600)
                # check to see if the guild still exists, if it doesn't, return
                if guild is None:
                    return
            else:
                if not member.bot:
                    try:
                        cursor_n.execute(
                            f"SELECT * FROM public.users WHERE userid = '{member.id}'"
                        )
                    except:
                        pass
                    automod_rows = cursor_n.rowcount
                    if automod_rows == 0:
                        cursor_n.execute(
                            f"INSERT INTO public.users (userid) VALUES ('{member.id}')"
                        )
                        mydb_n.commit()
                        log(
                            f"New user detected: {formatColor(member.id, 'green')} | Added to database!"
                        )


async def setup(bot):
    await bot.add_cog(events(bot))
