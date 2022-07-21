from __future__ import annotations

import asyncio
import contextlib
import random
from datetime import datetime
from typing import TYPE_CHECKING

import aiohttp
import cronitor
import discord
from discord.ext import commands, tasks
from index import logger
from Manager.logger import formatColor
from sentry_sdk import capture_exception
from utils import imports
from utils.default import add_one, log

if TYPE_CHECKING:
    from index import Bot


class events(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.config = imports.get("config.json")
        self.db_config = imports.get("db_config.json")
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

    async def try_to_send_msg_in_a_channel(self, guild, msg):
        for channel in guild.channels:
            with contextlib.suppress(Exception):
                await channel.send(msg)
                break

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
            log("Loaded JSK.")
        except Exception as e:
            capture_exception(e)
        for guild in self.bot.guilds:
            guild_commands = await self.bot.db.execute(
                "SELECT * FROM commands WHERE guild = $1", str(guild.id)
            )
            if not guild_commands:
                await self.bot.db.execute(
                    "INSERT INTO commands (guild) VALUES ($1)", str(guild.id)
                )
                log(f"New guild detected: {guild.id} | Added to commands database!")

            db_guild = self.bot.db.get_guild(guild.id) or await self.bot.db.fetch_guild(
                guild.id
            )
            if not db_guild:
                await self.bot.db.add_guild(guild.id)

                log(f"New guild detected: {guild.id} | Added to guilds database!")

    @tasks.loop(count=None, seconds=random.randint(25, 60))
    async def presence_loop(self):
        await self.bot.wait_until_ready()
        if datetime.now().month == 10 and datetime.now().day == 3:
            await self.bot.change_presence(
                activity=discord.Game(name="Happy birthday Motz!")
            )
            return
        # statuses = [
        #     f"tp!help | {len(self.bot.guilds)} Servers",
        #     f"tp!help | {len(self.bot.commands)} commands!",
        #     "tp!help | tp!support",
        #     "You can toggle commands now! | tp!toggle command",
        #     "ElysianVRC is cool: https://discord.gg/yCfKu7D3GD",
        #     "*badoop* hey look, i joined your vc",
        #     "*gets the rare discord ringtone*, im better than all of you",
        #     "today's weather is looking pretty weather-like",
        #     "ikea is cool",
        #     "i upgraded from windows 10 to doors",
        #     "gamers take showers? i don't think so!",
        #     "lets watch anime together, that would be cute",
        #     "tp!help | your mom lol.",
        #     "who invented grass, it's tasty",
        #     "i mistook salt for sugar, and put it in my coffee",
        #     "The dog goes meow, the motz goes THERES AN ERROR",
        #     "this status is so poggers",
        #     "ITS SENTIENT",
        #     "i drink rainwater from the walmart parking lot",
        #     "im a good bot, give me attention (please?)",
        #     "meow, im a bot? i think not! meow",
        #     "lets hold hands before marriage",
        #     "vote for me on top.gg, i love the attention",
        #     "im feeling a bit like a plastic bag",
        #     "if ur too tall, just be shorter",
        #     "don't be broke, just have money :)",
        #     "go, commit a sin",
        #     "go, commit a crime",
        #     "im committing crimes rn (and code)",
        #     "stupid idiot. (get roasted)",
        #     "i am a bot, and i am a bot",
        #     "I miss you cookie.",
        #     "Yo mamma (Laugh at this)",
        #     "We're really trying to be funny",
        #     "im gonna eat plastic :>",
        #     "Dm me the word tomato",
        #     "ok, kitten",
        # ] ### No longer using this list :)
        # Goodbye Cookie 2012 - 06/24/2021

        statues = self.bot.db._statuses or await self.bot.db.fetch_statuses()
        status_id = random.randint(0, len(statues) - 1)

        status_from_id = self.bot.db.get_status(
            status_id
        ) or await self.bot.db.fetch_status(status_id, cache=True)
        if not status_from_id:
            # should never happen but handling it for linter purposes
            log(f"Status {status_id} not found in database!")
            self.presence_loop.restart()
            return

        db_status = status_from_id.status
        server_count = db_status.replace("{server_count}", str(len(self.bot.guilds)))
        status = server_count.replace("{command_count}", str(len(self.bot.commands)))
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.playing, name=status)
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
        update_guild_count = self.bot.get_channel(968617760756203531)
        update_user_count = self.bot.get_channel(968617853886550056)
        await update_guild_count.edit(name=f"Server Count: {len(self.bot.guilds)}")
        await update_user_count.edit(name=f"User Count: {len(self.bot.users)}")

    @tasks.loop(count=None, minutes=10)
    async def post_status(self):
        monitor = cronitor.Monitor("4VwGKr")
        monitor.ping()  # send a heartbeat event

    @tasks.loop(count=None, minutes=2)
    async def status_page(self):
        await self.bot.wait_until_ready()

        # Post AGB status to status page
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://betteruptime.com/api/v1/heartbeat/pP3xBgddftBNS5T8JeGHtiaN"
            ) as r:
                await r.json()

    # @commands.Cog.listener(name="on_message")
    # async def add_server_to_db(self, ctx):
    #     await self.bot.wait_until_ready()
    #     # Add server to database
    #     try:
    #         cursor_n.execute(
    #             f"SELECT * FROM public.guilds WHERE guildId = '{ctx.guild.id}'"
    #         )
    #     except Exception:
    #         pass
    #     row_count = cursor_n.rowcount
    #     if row_count == 0:
    #         cursor_n.execute(
    #             f"INSERT INTO guilds (guildId) VALUES ('{ctx.guild.id}')")
    #         mydb_n.commit()
    #         log(
    #             f"New guild detected: {ctx.guild.id} | Added to database!")
    #     else:
    #         return

    # DO NOT PUT THIS IN MERGED EVENT, IT WILL ONLY WORK IN ITS OWN SEPERATE EVENT. **I DO NOT KNOW WHY :D**
    # DO NOT PUT THIS IN MERGED EVENT, IT WILL ONLY WORK IN ITS OWN SEPERATE EVENT. **I DO NOT KNOW WHY :D**
    # XOXOXO, KISSES ~ WinterFe
    @commands.Cog.listener(name="on_command")
    async def command_usage_updater(self, ctx):
        await self.bot.wait_until_ready()
        bot: Bot = ctx.bot  # type: ignore # shut

        db_user = bot.db.get_user(ctx.author.id) or await bot.db.fetch_user(
            ctx.author.id
        )
        if not db_user:
            return

        await db_user.modify(usedcmds=db_user.usedcmds + 1)

    # @commands.Cog.listener(name="on_command")
    # async def owner_check(self, ctx):
    #     await self.bot.wait_until_ready()

    #     if ctx.author.id in self.config.owners:
    #         await
    #     else:
    #         pass

    @commands.Cog.listener(name="on_message")
    async def user_check(self, ctx):
        await self.bot.wait_until_ready()
        # cursor_n.execute(f"SELECT blacklisted FROM blacklist WHERE userID = {ctx.author.id}")
        # res = cursor_n.fetch()
        # for x in res():
        #     if x[0] == "true":
        #         return print("blacklisted")
        #     else:
        # pass
        if ctx.author.bot:
            return

        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        if not db_user:
            await self.bot.db.add_user(ctx.author.id)
            log(
                f"New user detected: {formatColor(str(ctx.author.id), 'green')} | Added to database!"
            )

    @commands.Cog.listener(name="on_message")
    async def guildblacklist(self, message):
        if message.guild is None:
            return
        db_guild_blacklist = self.bot.db.get_guild_blacklist(
            message.guild.id
        ) or await self.bot.db.fetch_guild_blacklist(message.guild.id)
        if not db_guild_blacklist:
            await self.bot.db.add_guild_blacklist(message.guild.id, message.guild.name)
            log(
                f"{formatColor(message.guild.id, 'green')} | Didn't have a blacklist entry, added one!"
            )
        elif db_guild_blacklist.is_blacklisted:
            await self.try_to_send_msg_in_a_channel(
                message.guild,
                f"{message.guild.owner.mention}, This server is blacklisted from using this bot. To understand why and how to remove this blacklist, contact us @ `contact@lunardev.group`.",
            )
            log(
                f"{formatColor(message.guild.name, 'red')} tried to add AGB to a blacklisted server. I have left."
            )
            await message.guild.leave()
            return

    @commands.Cog.listener(name="on_invite_create")
    async def log_invites(self, invite):
        await self.bot.wait_until_ready()
        log_channel = self.bot.get_channel(938936724535509012)
        log_server = self.bot.get_guild(755722576445046806)
        if invite.guild.id == log_server.id:
            embed = discord.Embed(title="Invite Created", color=0x00FF00)
            embed.add_field(
                name="Invite Details",
                value=f"Url:{invite.url}, Created:{invite.created_at}, Expires:{invite.expires_at},\nMax Age:{invite.max_age}, Max Uses:{invite.max_uses}, Temporary(?){invite.temporary},\nInviter:{invite.inviter}, Uses:{invite.uses}",
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_command")
    async def blacklist_check(self, ctx):
        await self.bot.wait_until_ready()
        if ctx.author.bot:
            return
        db_blacklist_user = self.bot.db.get_blacklist(
            ctx.author.id
        ) or await self.bot.db.fetch_blacklist(ctx.author.id)
        if not db_blacklist_user:
            await self.bot.db.add_blacklist(ctx.author.id, False)
            log(
                f"No blacklist entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
            )

    @commands.Cog.listener(name="on_command")
    async def badge(self, ctx):
        await self.bot.wait_until_ready()
        if ctx.author.bot:
            return

        badge_user = await self.bot.db.fetchrow(
            "SELECT * FROM public.badges WHERE userid = $1", str(ctx.author.id)
        )
        if not badge_user:
            await self.bot.db.execute(
                "INSERT INTO badges (userid) VALUES ($1)", str(ctx.author.id)
            )
            log(
                f"No badge entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
            )

    @commands.Cog.listener(name="on_command")
    async def eco(self, ctx):
        await self.bot.wait_until_ready()
        if ctx.author.bot:
            return

        db_eco_user = self.bot.db.get_economy_user(
            ctx.author.id
        ) or await self.bot.db.fetch_economy_user(ctx.author.id)
        if not db_eco_user:
            await self.bot.db.add_economy_user(ctx.author.id, balance=1000, bank=500)
            log(
                f"No economy entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
            )

    @commands.Cog.listener(name="on_command")
    async def remove_admin_command_uses(self, ctx):
        """Deletes the invoked command that comes from admin.py"""
        await self.bot.wait_until_ready()
        if ctx.author.bot:
            return
        # check the command to see if it comes from admin.py
        if ctx.command.cog_name == "admin":
            with contextlib.suppress(Exception):
                await ctx.message.delete()

    # @commands.Cog.listener(name="on_member_join")
    # async def autorole(self, member):
    #     log_channel = ()# get the log channel / welcome channel
    #     # . . .
    #     #get the roles they want to give the member
    #     # . . .
    #     await member.add_roles()
    #     await log_channel.send()

    @commands.Cog.listener(name="on_command")
    async def logger_shit(self, ctx):
        await self.bot.wait_until_ready()
        if not ctx.guild or ctx.author.bot or ctx.interaction:
            return

        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        if db_user and not db_user.message_tracking:
            return

        if not ctx.guild.chunked:
            with contextlib.suppress(Exception):
                await ctx.guild.chunk()
                log(
                    f"{formatColor('[CHUNK]', 'bold_red')} Chunked server {formatColor(f'{ctx.guild.id}', 'grey')}"
                )

        if await self.bot.is_owner(ctx.author):
            log(
                f"{formatColor('[DEV]', 'bold_red')} {formatColor(ctx.author, 'red')} used command {formatColor(ctx.message.clean_content, 'grey')}"
            )
        else:
            log(
                f"{formatColor(ctx.author.id, 'grey')} used command {formatColor(ctx.message.clean_content, 'grey')}"
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.wait_until_ready()

        embed = discord.Embed(title="Removed from a server.", colour=0xFF0000)
        try:
            embed.add_field(
                name=":( forced to leave a server, heres their info:",
                value=f"Server name: `{guild.name}`\n ID `{guild.id}`\n Member Count: `{guild.member_count}`.",
            )

        except Exception as e:
            capture_exception(e)
            return
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        channel = self.bot.get_channel(769080397669072939)
        if guild.name is None:
            return
        if guild.member_count is None:
            return
        await channel.send(embed=embed)
        # Remove server from database
        db_guild = self.bot.db.get_guild(
            str(guild.id)
        ) or await self.bot.db.fetch_guild(str(guild.id))
        if not db_guild:
            log(f"Removed from: {guild.id}")
            return
        else:
            await self.bot.db.remove_guild(str(guild.id))
            log(f"Removed from: {guild.id} | Deleting database entry!")

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

        db_guild = self.bot.db.get_guild(guild.id) or await self.bot.db.fetch_guild(
            guild.id
        )
        if db_guild:
            log(f"New guild joined: {guild.id} | But it was already in the DB")
        else:
            await self.bot.db.add_guild(guild.id)
            log(f"New guild joined: {guild.id} | Added to database!")

        guild_commands = await self.bot.db.fetchrow(
            "SELECT * FROM commands WHERE guild = $1", str(guild.id)
        )
        if not guild_commands:
            await self.bot.db.execute(
                "INSERT INTO commands (guild) VALUES ($1)", str(guild.id)
            )

        # add to blacklist and handle if blacklisted
        db_guild_blacklist = self.bot.db.get_guild_blacklist(
            guild.id
        ) or await self.bot.db.fetch_guild_blacklist(guild.id)
        if not db_guild_blacklist:
            await self.bot.db.add_guild_blacklist(guild.id)
        elif db_guild_blacklist.is_blacklisted:
            await guild.leave()
            log(f"Left {guild.id} / {guild.name} because it was blacklisted")

    @commands.Cog.listener(name="on_guild_join")
    async def ban_on_join(self, guild):
        if guild.id != 770873933217005578:
            return
        objs = await self.bot.db.fetch_blacklists()
        user_ids = [x.user_id for x in objs if x.is_blacklisted]
        for user in user_ids:
            coom = await self.bot.fetch_user(user)
            with contextlib.suppress(Exception):
                await guild.ban(coom, reason="AGB Global Blacklist")
        log(f"Successfully banned {len(user_ids)} blacklisted users from {guild.id}")
        await asyncio.sleep(0.5)

    @commands.Cog.listener(name="on_guild_join")
    async def add_ppl_on_join(self, guild):
        # check to see if the servers member count is over x people, and if it is, wait to add them until the next hour
        if len(guild.members) > 300:
            await asyncio.sleep(3600)
        # check to see if the guild still exists, if it doesn't, return
        if guild is None:
            return

        # add the users to the database
        for member in guild.members:
            if member.bot:
                return

            db_user = self.bot.db.get_user(member.id) or await self.bot.db.fetch_user(
                member.id
            )
            if not db_user:
                await self.bot.db.add_user(member.id)
                log(
                    f"New user detected: {formatColor(member.id, 'green')} | Added to database!"
                )

    # @commands.Cog.listener(name="on_message")
    # async def automod_sql(self, ctx):
    #     if ctx.author.bot:
    #         return
    #     else:
    #         pass
    #     try:
    #         cursor_n.execute(
    #             f"SELECT * FROM automod WHERE guildId = {ctx.guild.id}")
    #     except Exception:
    #         pass
    #     automod_rows = cursor_n.rowcount
    #     if automod_rows == 0:
    #         cursor_n.execute(
    #             f"INSERT INTO automod (guildId) VALUES ({ctx.guild.id})")
    #         mydb_n.commit()
    #     else:
    #         return


# from index import cursor_n, mydb_n
# for guild in self.guilds:
#     cursor_n.execute(f"SELECT * FROM public.guilds WHERE guildId = '{guild.id}'")
#     row_count = cursor_n.rowcount
#     if row_count == 0:
#         cursor_n.execute(
#             f"INSERT INTO public.guilds (guildId) VALUES ('{guild.id}')"
#         )
#         mydb_n.commit()
#         print(f"{guild.id} | Added to database!")
# testing, ignore this


async def setup(bot: Bot) -> None:
    await bot.add_cog(events(bot))
