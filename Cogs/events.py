import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks
from index import EMBED_COLOUR, cursor, mydb
from utils import default


class events(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self.config = default.get("config.json")
        self.presence_loop.start()

    def cog_unload(self):
        self.presence_loop.close()

    @commands.Cog.listener()
    async def on_message(self, ctx):

        # Add server to database
        try:
            cursor.execute(f"SELECT * FROM guilds WHERE guildId = {ctx.guild.id}")
        except:
            pass
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(f"INSERT INTO guilds (guildId) VALUES ({ctx.guild.id})")
            mydb.commit()
            print(
                f"{default.date()} | New guild detected: {ctx.guild.id} | Added to database!"
            )
        else:
            return

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{default.date()} | Logged in as: {self.bot.user}")
        print(f"{default.date()} | Client: {self.bot.user}")
        print(f"{default.date()} | Client ID: {self.bot.user.id}")
        print(f"{default.date()} | Client Server Count: {len(self.bot.guilds)}")
        print(f"{default.date()} | Client User Count: {len(self.bot.users)}")
        if len(self.bot.shards) > 1:
            print(
                f"{default.date()} | {self.bot.user} is using {len(self.bot.shards)} shards."
            )
        else:
            print(
                f"{default.date()} | {self.bot.user} is using {len(self.bot.shards)} shard."
            )
        print(f"{default.date()} | Discord Python Version:", (discord.__version__))
        try:
            self.bot.load_extension("Cogs.music")
        except:
            pass
        try:
            self.bot.load_extension("jishaku")
            print(f"{default.date()} | Loaded JSK.")
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.guild is None:
            return
        if ctx.guild.chunked == True:
            return
        try:
            await ctx.guild.chunk()
        except:
            pass

    # @commands.Cog.listener(name="on_message")
    # async def SelfPingResponder(self, message):
    #     embed = discord.Embed(title="Why you ping me?", color=EMBED_COLOUR,
    #                           description=f"My default prefix is `tp!`.\nIf a custom prefix was set and you dont know it, you can use my mention as a prefix!\nNormally, AGB's nickname is set to contain its prefix and it will update when the prefix is changed. If the bot doesnt have permissions to update its nickname, this feature will obviously not work. If there is no nickname thats set currently, please report this to an Admin or to the Owner of this server.\nExample on how to use my mention as the prefix: <@{self.bot.user.id}> prefix")
    #     print("passed embed")
    #     if message.author.bot:
    #         return
    #     print("passed if check for the bot")
    #     if message.content.startswith("<@723726581864071178>"):
    #         print("passed mention")
    #         if message.guild.id == 755722576445046806:
    #             print("passed guild")
    #             await message.channel.send(embed=embed)
    #             print("passed sending embed")
    #             await message.channel.send("testing")
    #             print("sending a test")

    # @commands.Cog.listener(name="on_message")
    # async def testing(self, message):
    #     if message.content.startswith(self.bot.user.mention):
    #         print(f"{message.guild.id} / {message.guild.name}")

    @commands.Cog.listener()
    async def on_command(self, ctx):
        # cursor.execute(f"SELECT blacklisted FROM blacklist WHERE userID = {ctx.author.id}")
        # res = cursor.fetchall()
        # for x in res():
        #     if x[0] == "true":
        #         return print("blacklisted")
        #     else:
        # pass

        if ctx.author.id in self.config.owners:
            print(
                f"{default.date()} | [DEV] {ctx.author.name} used command {ctx.message.clean_content}"
            )
        else:
            print(
                f"{default.date()} | {ctx.author.id} used command {ctx.message.clean_content}"
            )
        try:
            embed = discord.Embed(
                title=f"Basic Info On Latest Used Command.",
                colour=discord.Colour.green(),
            )
            embed.add_field(
                name="Channel?:", value=f"{ctx.channel.name} {ctx.channel.id}."
            )
            embed.add_field(name="Server?:", value=f"{ctx.guild.name} {ctx.guild.id}.")
            embed.add_field(name=f"Who?:", value=f"{ctx.author}, {ctx.author.id}")
            try:
                embed.add_field(name="Command?:", value=f"{ctx.message.clean_content}")
            except discord.errors.HTTPException:
                embed.add_field(
                    name="Command?:", value="Command that was ran was too big."
                )
            channel = self.bot.get_channel(842099510360408104)
            message_cooldown = commands.CooldownMapping.from_cooldown(
                1.0, 60.0, commands.BucketType.user
            )
            bucket = message_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()

            if ctx.guild.id == "755722576445046806":
                return
            if retry_after:
                return
            else:
                await channel.send(embed=embed)
        except AttributeError:
            embed = discord.Embed(
                title=f"Basic Info On Latest Used Command.",
                colour=discord.Colour.green(),
            )
            embed.add_field(name="Where?:", value=f"Private message")
            embed.add_field(name="Who?:", value=f"{ctx.author}, {ctx.author.id}")
            embed.add_field(name="Command?:", value=f"{ctx.message.clean_content}")
            channel = self.bot.get_channel(842099510360408104)
            message_cooldown = commands.CooldownMapping.from_cooldown(
                1.0, 60.0, commands.BucketType.user
            )
            bucket = message_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            if retry_after:
                return
            else:
                await channel.send(embed=embed)

    @commands.Cog.listener(name="on_message")
    async def econmy_yuh(self, ctx):

        if ctx.author.bot:
            return
        else:
            pass
        try:
            cursor.execute(f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        except:
            pass
        eco_rows = cursor.rowcount
        if eco_rows == 0:
            cursor.execute(
                f"INSERT INTO userEco (userId, balance, bank, isBot) VALUES ({ctx.author.id}, '1000', '500', '{ctx.author.bot}')"
            )
            mydb.commit()
            print(
                f"{default.date()} | No economy entry detected for: {ctx.author.id} / {ctx.author} | Added to database!"
            )
        else:
            return

    @commands.Cog.listener(name="on_message")
    async def badges_sql(self, ctx):
        if ctx.author.bot:
            return
        else:
            pass
        try:
            cursor.execute(f"SELECT * FROM badges WHERE userId = {ctx.author.id}")
        except:
            pass
        badges_rows = cursor.rowcount
        if badges_rows == 0:
            cursor.execute(f"INSERT INTO badges (userId) VALUES ({ctx.author.id})")
            mydb.commit()
        else:
            return

    # @commands.Cog.listener(name="on_message")
    # async def automod_sql(self, ctx):
    #     if ctx.author.bot:
    #         return
    #     else:
    #         pass
    #     try:
    #         cursor.execute(
    #             f"SELECT * FROM automod WHERE guildId = {ctx.guild.id}")
    #     except:
    #         pass
    #     automod_rows = cursor.rowcount
    #     if automod_rows == 0:
    #         cursor.execute(
    #             f"INSERT INTO automod (guildId) VALUES ({ctx.guild.id})")
    #         mydb.commit()
    #     else:
    #         return

    @commands.Cog.listener(name="on_message")
    async def users_sql(self, ctx):
        if ctx.author.bot:
            return
        else:
            pass
        try:
            cursor.execute(f"SELECT * FROM users WHERE userId = {ctx.author.id}")
        except:
            pass
        automod_rows = cursor.rowcount
        if automod_rows == 0:
            cursor.execute(f"INSERT INTO users (userId) VALUES ({ctx.author.id})")
            mydb.commit()
        else:
            return

    @commands.Cog.listener(name="on_command")
    async def add_cmd_uses(self, ctx):
        if ctx.author.bot:
            return
        else:
            pass
        try:
            cursor.execute(f"SELECT * FROM users WHERE userId = {ctx.author.id}")
        except:
            pass
        automod_rows = cursor.rowcount
        if automod_rows == 0:
            cursor.execute(f"INSERT INTO users (userId) VALUES ({ctx.author.id})")
            mydb.commit()
        else:
            cursor.execute(f"SELECT * FROM users WHERE userId = {ctx.author.id}")
            row = cursor.fetchall()
            cursor.execute(
                f"UPDATE users SET usedCmds = {row[0][1] + 1} WHERE userId = {ctx.author.id}"
            )
            mydb.commit()

    @commands.Cog.listener(name="on_dbl_vote")
    async def dbl_vote_reward(self, data):
        print(f"{default.date()} | Recieved a vote:\n{data}")

    @tasks.loop(count=None, minutes=1)
    async def presence_loop(self):
        await self.bot.wait_until_ready()
        datetime.utcnow()
        delta_uptime = datetime.utcnow() - self.bot.launch_time
        delta_uptime = delta_uptime - timedelta(microseconds=delta_uptime.microseconds)
        omegalul = random.choice(["watching", "playing", "listening", "competing"])

        funny_statuses = [
            f"tp!help | {len(self.bot.guilds)} Servers",
            f"tp!help | {len(self.bot.commands)} commands!",
            "tp!help | tp!support ",
            f"tp!help | {delta_uptime} since last restart",
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

    def cog_unload(self):
        self.presence_loop.close()

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
        cursor.execute(f"SELECT * FROM guilds WHERE guildId = {guild.id}")
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            print(f"{default.date()} | Removed from: {guild.id}")
        else:
            cursor.execute(f"DELETE FROM guilds WHERE guildId = {guild.id}")
            mydb.commit()
            print(
                f"{default.date()} | removed from: {guild.id} | Deleting database entry!"
            )

    @commands.Cog.listener(name="on_guild_join")
    async def MessageSentOnGuildJoin(self, guild):

        nick = f"[tp!] {self.bot.user.name}"
        try:
            await guild.me.edit(nick=nick)
        except discord.Forbidden:
            return print(f"{default.date()} | Unable to change nickname in {guild.id}")
        else:
            print(f"{default.date()} | Changed nickname to {nick} in {guild.id}")
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
        cursor.execute(f"SELECT * FROM guilds WHERE guildId = {guild.id}")
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(f"INSERT INTO guilds (guildId) VALUES ({guild.id})")
            mydb.commit()
            print(
                f"{default.date()} | New guild joined: {guild.id} | Added to database!"
            )
        else:
            print(
                f"{default.date()} | New guild joined: {guild.id} | But it was already in the DB"
            )

    # @commands.command(hidden=True)
    # @commands.check(permissions.is_owner)
    # async def postcount(self, ctx):
    #     await self.blist_api.post_bot_stats()
    #     await ctx.send("Done!")


def setup(bot):
    bot.add_cog(events(bot))
