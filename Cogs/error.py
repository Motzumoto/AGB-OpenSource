import json
import os
import re

import discord
import psutil
from discord.ext import commands
from discord.ext.commands import errors
from index import EMBED_COLOUR, config, cursor_n, mydb_n
from utils.checks import NotVoted, MusicGone
from utils import default
import psycopg
from Manager.logger import formatColor
from utils.default import log


class Error(commands.Cog, name="error"):
    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process(os.getpid())
        with open("blacklist.json") as f:
            self.blacklist = json.load(f)
        self.default_prefix = "tp!"
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1.0, 3.0, commands.BucketType.user
        )
        self.nword_re = re.compile(
            r"(n|m|и|й)(i|1|l|!|ᴉ|¡)(g|ƃ|6|б)(g|ƃ|6|б)(e|3|з|u)(r|Я)", re.I
        )

        self.errors = (
            NotVoted,
            MusicGone,
            discord.errors.NotFound,
            commands.NoPrivateMessage,
            commands.MissingPermissions,
            commands.BadArgument,
            commands.CommandInvokeError,
            commands.ChannelNotReadable,
            commands.MaxConcurrencyReached,
            commands.BotMissingPermissions,
            commands.NotOwner,
            commands.TooManyArguments,
            commands.MessageNotFound,
            commands.UserInputError,
            discord.errors.Forbidden,
            discord.HTTPException,
            errors.DisabledCommand,
            commands.BadBoolArgument,
            psycopg.errors.Warning,
            psycopg.errors.InterfaceError,
            psycopg.errors.DatabaseError,
            psycopg.errors.DataError,
            psycopg.errors.OperationalError,
            psycopg.errors.IntegrityError,
            psycopg.errors.InternalError,
            psycopg.errors.ProgrammingError,
            psycopg.errors.NotSupportedError,
        )

    async def create_embed(self, ctx, error):
        embed = discord.Embed(title="Error", description=error, colour=0xFF0000)
        bucket = self.message_cooldown.get_bucket(ctx.message)
        if retry_after := bucket.update_rate_limit():
            return
        try:
            await ctx.send(embed=embed, delete_after=15)
        except Exception:
            await ctx.send(
                f"`{error}`\n***Enable Embed permissions please.***",
                delete_after=15,
            )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        # if isinstance(error, app_commands.errors.CommandNotFound):
        #     return
        error = getattr(error, "original", error)
        if hasattr(ctx.command, "on_error"):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            bucket = self.message_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            embed = discord.Embed(
                title="Hey now...",
                color=0xFF0000,
                description=f"You're missing a required argument.\ntry again by doing `{ctx.command.signature}`\nif you still don't understand, type `{ctx.prefix}help {ctx.command}`",
            )
            embed.set_thumbnail(url=ctx.author.avatar)
            if retry_after:
                return
            else:
                await ctx.send(embed=embed)

        elif isinstance(error, self.errors):
            await self.create_embed(ctx, error)
            return

        elif isinstance(error, discord.errors.InteractionResponded):
            return
        elif isinstance(error, ValueError):
            bucket = self.message_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            embed = discord.Embed(
                title="Hey now...",
                color=0xFF0000,
                description=f"This command requires a number as an argument.\nTry again by doing `{ctx.command.signature}`\nif you still don't understand, type `{ctx.prefix}help {ctx.command}`",
            )
            embed.set_thumbnail(url=self.bot.user.avatar)
            if retry_after:
                return
            else:
                await ctx.send(embed=embed)

        elif isinstance(error, commands.CommandOnCooldown):
            bucket = self.message_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            log(
                f"{formatColor(ctx.author.name, 'gray')} tried to use {ctx.command.name} but it was on cooldown for {error.retry_after:.2f} seconds."
            )
            day = round(error.retry_after / 86400)
            hour = round(error.retry_after / 3600)
            minute = round(error.retry_after / 60)
            if retry_after:
                return
            if day > 0:
                await ctx.send(f"This command has a cooldown for {str(day)}day(s)")
            elif hour > 0:
                await ctx.send(f"This command has a cooldown for {str(hour)} hour(s)")
            elif minute > 0:
                await ctx.send(f"This command has a cooldown for {str(minute)} minute(s)")
            else:
                await ctx.send(
                    f"This command has a cooldown for {error.retry_after:.2f} second(s)"
                )
                return

        elif isinstance(error, commands.NSFWChannelRequired):
            embed = discord.Embed(
                title="Error",
                description="This command is for NSFW channels only!",
                colour=0xFF0000,
                timestamp=ctx.message.created_at,
            )
            embed.set_image(url="https://i.hep.gg/hdlOo67BI.gif")
            embed.set_thumbnail(url=ctx.message.author.avatar)
            embed.set_author(
                name=ctx.message.author.name, icon_url=ctx.message.author.avatar
            )
            bucket = self.message_cooldown.get_bucket(ctx.message)
            if retry_after := bucket.update_rate_limit():
                return
            try:
                await ctx.send(embed=embed, delete_after=30)
            except discord.errors.Forbidden:
                await ctx.send(
                    f"`{error}`\n***Enable Embed permissions please.***",
                    delete_after=30,
                )

                return

        elif isinstance(error, commands.CheckAnyFailure):
            pass

        elif isinstance(error, commands.CheckFailure):
            me1 = self.bot.get_user(101118549958877184)
            me2 = self.bot.get_user(683530527239962627)
            cursor_n.execute(
                f"SELECT * FROM public.blacklist WHERE userid = '{ctx.message.author.id}'"
            )
            rows = cursor_n.fetchall()
            if rows[0][1] == "true":
                embed = discord.Embed(
                    title="Error",
                    colour=0xFF0000,
                    timestamp=ctx.message.created_at,
                )
                embed.add_field(name="Author", value=ctx.message.author.mention)
                embed.add_field(
                    name="Error",
                    value=f"You've been blacklisted from using this bot\nTo see why and or get the blacklist removed, send us an email - `contact@lunardev.group`\nOr contact the owners directly - {me1}, {me2}",
                )
                embed.set_thumbnail(url=ctx.message.author.avatar)
                embed.set_footer(
                    text="If you believe this is a mistake, contact the bot owner or the server owner."
                )
                embed.set_author(
                    name=ctx.message.author.name, icon_url=ctx.message.author.avatar
                )
                bucket = self.message_cooldown.get_bucket(ctx.message)
                if retry_after := bucket.update_rate_limit():
                    return
                try:
                    await ctx.send(embed=embed, delete_after=15)
                    await ctx.message.add_reaction("\u274C")
                except discord.errors.Forbidden:
                    await ctx.send(
                        f"You don't have permission to run this command.\n***Enable Embed permissions please.***",
                        delete_after=15,
                    )
                    await ctx.message.add_reaction("\u274C")

                    return
            elif self.nword_re.search(ctx.message.content.lower()):
                await me1.send(
                    f"{ctx.author} is trying to get AGB to say racist things"
                )
                await me2.send(
                    f"{ctx.author} is trying to get AGB to say racist things"
                )
                return
            else:
                embed = discord.Embed(
                    title="Error",
                    colour=0xFF0000,
                    timestamp=ctx.message.created_at,
                )

                embed.add_field(name="Author", value=ctx.message.author.mention)
                embed.add_field(
                    name="Error",
                    value="You don't have permission to run this command.",
                )
                embed.set_thumbnail(url=ctx.message.author.avatar)
                embed.set_footer(
                    text="If you believe this is a mistake, contact the bot owner or the server owner."
                )
                embed.set_author(
                    name=ctx.message.author.name,
                    icon_url=ctx.message.author.avatar,
                )
                bucket = self.message_cooldown.get_bucket(ctx.message)
                if retry_after := bucket.update_rate_limit():
                    return
                try:
                    await ctx.send(embed=embed, delete_after=35)
                except Exception:
                    await ctx.send(
                        "You don't have permission to run this command.",
                        delete_after=15,
                    )


                    return
            mydb_n.commit()
            return
        bucket = self.message_cooldown.get_bucket(ctx.message)
        if retry_after := bucket.update_rate_limit():
            return
        await ctx.send(
            f"An error has occured. The error has automatically been reported and logged. Please wait until the developers work on a fix.\nJoin the support server for updates: {config.Server}",
        )
        bug_channel = self.bot.get_channel(791265212429762561)

        embed = discord.Embed(
            title=f"New Bug Submitted By {ctx.author.name}.",
            colour=EMBED_COLOUR,
        )
        embed.add_field(name="Error", value=default.traceback_maker(error))
        embed.add_field(name="Command", value=ctx.command.name)
        embed.set_footer(
            text=f"User *({ctx.author.id})* in {ctx.channel.id} {ctx.message.id}",
            icon_url=ctx.author.avatar,
        )
        # check if the error is already being handled in self.errors list

        if error in self.errors:
            return
        else:
            await bug_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Error(bot))
