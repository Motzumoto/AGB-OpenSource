import random
import discord
import asyncio

from datetime import datetime
from discord.ext import commands, tasks
from index import cursor_n, mydb_n, logger
from utils import default
from Manager.commandManager import commandsEnabled


class events(commands.Cog):
    def __init__(self, bot: commands.Bot, *args, **kwargs):
        self.bot = bot
        self.config = default.get("config.json")
        self.db_config = default.get("db_config.json")
        self.presence_loop.start()
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1.0, 3.0, commands.BucketType.guild
        )
        self.loop = asyncio.get_event_loop()

    def cog_unload(self):
        self.presence_loop.stop()

    @commands.Cog.listener(name="on_message")
    async def add_server_to_db(self, ctx):

        # Add server to database
        try:
            cursor_n.execute(
                f"SELECT * FROM public.guilds WHERE guildId = '{ctx.guild.id}'"
            )
        except:
            pass
        row_count = cursor_n.rowcount
        if row_count == 0:
            cursor_n.execute(f"INSERT INTO guilds (guildId) VALUES ('{ctx.guild.id}')")
            mydb_n.commit()
            logger.info(f"New guild detected: {ctx.guild.id} | Added to database!")
        else:
            return

    @commands.Cog.listener()
    async def on_ready(self):
        # self.bot.pool = await aiomysql.connect(
        #     host = self.db_config.host,
        #     user = self.db_config.user,
        #     password = self.db_config.password,
        #     db = self.db_config.database,
        #     port = int(self.db_config.port),
        #     autocommit = True,
        #     loop = self.loop,
        # )

        logger.info(f"Logged in as: {self.bot.user}")
        logger.info(f"Client: {self.bot.user}")
        logger.info(f"Client ID: {self.bot.user.id}")
        logger.info(f"Client Server Count: {len(self.bot.guilds)}")
        logger.info(f"Client User Count: {len(self.bot.users)}")
        if len(self.bot.shards) > 1:
            logger.info(f"{self.bot.user} is using {len(self.bot.shards)} shards.")
        else:
            logger.info(f"{self.bot.user} is using {len(self.bot.shards)} shard.")
        logger.info(f"Discord Python Version: {discord.__version__}")
        try:
            self.bot.load_extension("Cogs.music")
        except:
            pass
        try:
            self.bot.load_extension("jishaku")
            logger.info(f"Loaded JSK.")
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.guild is None:
            return
        if ctx.guild.chunked:
            return
        try:
            await ctx.guild.chunk()
        except:
            pass

    @commands.Cog.listener(name="on_command")
    async def blacklist_check(self, ctx):
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
                f"SELECT * FROM public.users WHERE \"userId\" = '{ctx.author.id}'"
            )
        except:
            pass
        automod_rows = cursor_n.rowcount
        if automod_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.users (\"userId\") VALUES ('{ctx.author.id}')"
            )
            mydb_n.commit()

    @commands.Cog.listener(name="on_command")
    async def eco_and_badges_and_users_and_and_blacklist_check_sql(self, ctx):
        if ctx.author.bot:
            return
        else:
            pass
        # if ctx.guild.chunked:
        #     return
        if ctx.author.id in self.config.owners:
            logger.info(
                f"[DEV] {ctx.author.name} used command {ctx.message.clean_content}"
            )
            return
        else:
            logger.info(f"{ctx.author.id} used command {ctx.message.clean_content}")

        row = cursor_n.fetchall()
        cursor_n.execute(
            f'UPDATE public.users SET "usedCmds" = {row[0][1] + 1} WHERE "userId" = \'{ctx.author.id}\''
        )
        print(row[0][1])
        mydb_n.commit()
        try:
            cursor_n.execute(
                f'SELECT * FROM public."userEco" WHERE "userId" = \'{ctx.author.id}\''
            )
        except:
            pass
        eco_rows = cursor_n.rowcount
        if eco_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.\"userEco\" (\"userId\", balance, bank) VALUES ('{ctx.author.id}', '1000', '500')"
            )
            mydb_n.commit()
            logger.debug(
                f"No economy entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
            )

        try:
            cursor_n.execute(
                f"SELECT * FROM public.badges WHERE userId = '{ctx.author.id}'"
            )
        except:
            pass
        badges_rows = cursor_n.rowcount
        if badges_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.badges (userId) VALUES ('{ctx.author.id}')"
            )
            mydb_n.commit()

        try:
            cursor_n.execute(
                f"SELECT * FROM public.users WHERE \"userId\" = '{ctx.author.id}'"
            )
        except:
            pass
        automod_rows = cursor_n.rowcount
        if automod_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.users (\"userId\") VALUES ('{ctx.author.id}')"
            )
            mydb_n.commit()

        try:
            cursor_n.execute(
                f"SELECT * FROM public.users WHERE \"userId\" = '{ctx.author.id}'"
            )
        except:
            pass
        automod_rows = cursor_n.rowcount
        if automod_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.users (\"userId\") VALUES ('{ctx.author.id}')"
            )
            mydb_n.commit()
        else:
            cursor_n.execute(
                f"SELECT * FROM public.users WHERE \"userId\" = '{ctx.author.id}'"
            )

        # blacklist check
        try:
            cursor_n.execute(
                f"SELECT * FROM public.blacklist WHERE \"userID\" = '{ctx.author.id}'"
            )
        except:
            pass
        bl_rows = cursor_n.rowcount
        if bl_rows == 0:
            cursor_n.execute(
                f"INSERT INTO public.blacklist (\"userID\", blacklisted) VALUES ('{ctx.author.id}', 'false')"
            )
            mydb_n.commit()
            logger.debug(
                f"No blacklist entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
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
    #     except:
    #         pass
    #     automod_rows = cursor_n.rowcount
    #     if automod_rows == 0:
    #         cursor_n.execute(
    #             f"INSERT INTO automod (guildId) VALUES ({ctx.guild.id})")
    #         mydb_n.commit()
    #     else:
    #         return

    @tasks.loop(count=None, seconds=30)
    async def presence_loop(self):
        await self.bot.wait_until_ready()
        if datetime.today().month == 10 and datetime.today().day == 3:
            await self.bot.change_presence(
                activity=discord.Game(name="Happy birthday Motz!")
            )
            return
        omegalul = random.choice(["watching", "playing", "listening", "competing"])
        funny_statuses = [
            f"tp!help | {len(self.bot.guilds)} Servers",
            f"tp!help | {len(self.bot.commands)} commands!",
            "tp!help | tp!support ",
        ]
        # Goodbye Cookie 2012 - 06/24/2021
        if omegalul == "watching":
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=random.choice(funny_statuses),
                )
            )
        if omegalul == "playing":
            await self.bot.change_presence(
                activity=discord.Game(name=random.choice(funny_statuses))
            )
        if omegalul == "listening":
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=random.choice(funny_statuses),
                )
            )
        if omegalul == "competing":
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.competing,
                    name=random.choice(funny_statuses),
                )
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):

        embed = discord.Embed(
            title="Removed from a server.", colour=discord.Colour.red()
        )
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
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(static_format="png"))
        channel = self.bot.get_channel(769080397669072939)
        await channel.send(embed=embed)
        # Remove server from database
        cursor_n.execute(f"SELECT * FROM public.guilds WHERE guildId = '{guild.id}'")
        # results = cursor_n.fetchall() # Assigned but not used
        row_count = cursor_n.rowcount
        if row_count == 0:
            logger.info(f"Removed from: {guild.id}")
        else:
            cursor_n.execute(f"DELETE FROM guilds WHERE guildId = '{guild.id}'")
            mydb_n.commit()
            logger.warning(f"Removed from: {guild.id} | Deleting database entry!")

    @commands.Cog.listener(name="on_guild_join")
    async def commandToggle(self, guild):
        commandsEnabled[str(guild.id)] = {}
        for cmd in self.bot.commands:
            commandsEnabled[str(guild.id)][cmd.name] = True

    @commands.Cog.listener(name="on_guild_join")
    async def MessageSentOnGuildJoin(self, guild):

        nick = f"[tp!] {self.bot.user.name}"
        try:
            await guild.me.edit(nick=nick)
        except discord.Forbidden:
            return logger.info(f"Unable to change nickname in {guild.id}")
        else:
            logger.info(f"Changed nickname to {nick} in {guild.id}")
        embed = discord.Embed(
            title="Oi cunt, Just got invited to another server.",
            colour=discord.Colour.green(),
        )
        embed.add_field(
            name="Here's the servers' info.",
            value=f"Server name: `{guild.name}`\n ID `{guild.id}`\n Member Count: `{guild.member_count}`.",
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(static_format="png"))
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
            logger.info(f"New guild joined: {guild.id} | Added to database!")
        else:
            logger.info(f"New guild joined: {guild.id} | But it was already in the DB")

    @commands.Cog.listener(name="on_ready")
    async def toggle_command_guild_stuff(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                commandsEnabled[str(guild.id)] = {}
                for cmd in self.bot.commands:
                    commandsEnabled[str(guild.id)][cmd.name] = True
            except:
                pass


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


def setup(bot):
    bot.add_cog(events(bot))
