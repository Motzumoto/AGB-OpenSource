### IMPORTANT ANNOUNCEMENT ###
#
# All additions to AGB will now cease.
# AGB's management will be limited to the following:
# - Optimization
# - Bug Fixes
# - Basic Maintenance
#
# DO NOT ADD ANY NEW FEATURES TO AGB
# ALL NEW FEATURES WILL BE RESERVED FOR MEKU
#
### IMPORTANT ANNOUNCEMENT ###

import json
import os
import re

import discord
import psutil
from discord.ext import commands
from discord.ext.commands import errors
from index import Vote, cursor_n, mydb_n
from utils.checks import NotVoted
from index import logger
from utils import default
from Manager.logger import formatColor


class Error(commands.Cog):
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
            commands.NoPrivateMessage,
            commands.MissingPermissions,
            commands.BadArgument,
            commands.CommandInvokeError,
            commands.NSFWChannelRequired,
            commands.ChannelNotReadable,
            commands.MaxConcurrencyReached,
            commands.BotMissingPermissions,
            commands.NotOwner,
            commands.CommandOnCooldown,
            commands.TooManyArguments,
            commands.MessageNotFound,
            commands.UserInputError,
            discord.errors.Forbidden,
            discord.HTTPException,
            errors.DisabledCommand,
        )

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title="Error", colour=discord.Colour.red(), timestamp=ctx.message.created_at
        )
        embed.add_field(name="Message", value=ctx.message.content)
        embed.add_field(name="Author", value=ctx.message.author.mention)
        embed.add_field(name="Error", value=error)
        embed.set_thumbnail(url=ctx.message.author.avatar)
        embed.set_author(
            name=ctx.message.author.name, icon_url=ctx.message.author.avatar
        )
        bucket = self.message_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return
        else:
            try:
                await ctx.send(embed=embed, delete_after=15)
                await ctx.message.add_reaction("\u274C")
            except discord.errors.Forbidden:
                await ctx.send(
                    f"`{error}`\n***Enable Embed permissions please.***",
                    delete_after=15,
                )
                await ctx.message.add_reaction("\u274C")
                ctx.command.reset_cooldown(ctx)
                return

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        logger.error(
            f"{formatColor(ctx.command.name, 'grey')} | {formatColor(ctx.author.name, 'grey')} / {formatColor(ctx.author.id, 'grey')}\n{formatColor(default.code_traceback(error), 'red')}"
        )
        await ctx.message.add_reaction("\u274C")
        error = getattr(error, "original", error)
        if hasattr(ctx.command, "on_error"):
            return
        else:
            pass

        if isinstance(error, commands.MissingRequiredArgument):
            await self.create_embed(ctx, error)

        elif isinstance(error, NotVoted):
            bucket = self.message_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            embed = discord.Embed(
                title="Hey now...",
                color=discord.Colour.red(),
                description=f"This command `({ctx.command})` is for voters only!\nVote **[here]({Vote})**",
            )
            embed.set_thumbnail(url=self.bot.user.avatar)
            if retry_after:
                return
            else:
                await ctx.send(embed=embed)
                ctx.command.reset_cooldown(ctx)

        elif isinstance(error, self.errors):
            await self.create_embed(ctx, error)

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
                    colour=discord.Colour.red(),
                    timestamp=ctx.message.created_at,
                )
                embed.add_field(name="Message", value=ctx.message.content)
                embed.add_field(name="Author", value=ctx.message.author.mention)
                embed.add_field(
                    name="Error",
                    value=f"You've been blacklisted from using this bot\nTo see why and or get the blacklist removed, send us an email - `agb@agb-dev.xyz`\nOr contact the owners directly - {me1}, {me2}",
                )
                embed.set_thumbnail(url=ctx.message.author.avatar)
                embed.set_footer(
                    text="If you believe this is a mistake, contact the bot owner or the server owner."
                )
                embed.set_author(
                    name=ctx.message.author.name, icon_url=ctx.message.author.avatar
                )
                embed.set_footer(
                    text="If you believe this is a mistake, contact the bot owner or the server owner."
                )
                bucket = self.message_cooldown.get_bucket(ctx.message)
                retry_after = bucket.update_rate_limit()
                if retry_after:
                    return
                else:
                    try:
                        await ctx.send(embed=embed, delete_after=15)
                        await ctx.message.add_reaction("\u274C")
                    except discord.errors.Forbidden:
                        await ctx.send(
                            f"You don't have permission to run this command.\n***Enable Embed permissions please.***",
                            delete_after=15,
                        )
                        await ctx.message.add_reaction("\u274C")
                        ctx.command.reset_cooldown(ctx)
                        return
            else:
                if self.nword_re.search(ctx.message.content.lower()):
                    await me1.send(
                        f"{ctx.author} is trying to get AGB to say racist things, blacklist that cunt!"
                    )
                    await me2.send(
                        f"{ctx.author} is trying to get AGB to say racist things, blacklist that cunt!"
                    )
                    return
                else:
                    embed = discord.Embed(
                        title="Error",
                        colour=discord.Colour.red(),
                        timestamp=ctx.message.created_at,
                    )
                    embed.add_field(name="Message", value=ctx.message.content)
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
                    embed.set_footer(
                        text="If you believe this is a mistake, contact the bot owner or the server owner."
                    )
                    bucket = self.message_cooldown.get_bucket(ctx.message)
                    retry_after = bucket.update_rate_limit()
                    if retry_after:
                        return
                    else:
                        try:
                            await ctx.send(embed=embed, delete_after=35)
                            await ctx.message.add_reaction("\u274C")
                        except discord.errors.Forbidden:
                            await ctx.send(
                                f"You don't have permission to run this command.\n***Enable Embed permissions please.***",
                                delete_after=15,
                            )
                            await ctx.message.add_reaction("\u274C")
                            ctx.command.reset_cooldown(ctx)
                            return
            mydb_n.commit()


def setup(bot):
    bot.add_cog(Error(bot))
