import json
import os
import discord
import psutil

from discord.ext import commands
from discord.ext.commands import errors
from index import Vote, mydb_n, cursor_n
from utils.checks import NotVoted


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
            discord.Forbidden,
            discord.HTTPException,
            errors.DisabledCommand,
        )

    async def create_embed(self, ctx, error):
        embed = discord.Embed(title="Error", colour=discord.Colour.red())
        embed.add_field(name="Message", value=ctx.message.content)
        embed.add_field(name="Author", value=ctx.message.author.mention)
        embed.add_field(name="Error", value=error)
        embed.set_thumbnail(url=ctx.message.author.avatar_url)
        embed.set_footer(
            text="{} | {}".format(
                ctx.message.created_at, self.process.memory_info().rss
            )
        )
        embed.set_author(
            name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url
        )
        embed.set_footer(
            text="{} | {}".format(
                ctx.message.created_at, self.process.memory_info().rss
            )
        )
        bucket = self.message_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return
        else:
            try:
                await ctx.send(embed=embed, delete_after=15)
                await ctx.message.add_reaction("\u274C")
            except discord.Forbidden:
                await ctx.send(
                    f"`{error}`\n***Enable Embed permissions please.***",
                    delete_after=15,
                )
                await ctx.message.add_reaction("\u274C")
                ctx.command.reset_cooldown(ctx)
                return

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
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
            embed.set_thumbnail(url=self.bot.user.avatar_url_as(static_format="png"))
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
                f"SELECT * FROM public.blacklist WHERE \"userID\" = '{ctx.message.author.id}'"
            )
            rows = cursor_n.fetchall()
            if rows[0][1] == "true":
                embed = discord.Embed(title="Error", colour=discord.Colour.red())
                embed.add_field(name="Message", value=ctx.message.content)
                embed.add_field(name="Author", value=ctx.message.author.mention)
                embed.add_field(name="Channel", value=ctx.message.channel.mention)
                embed.add_field(name="Guild", value=ctx.message.guild.name)
                embed.add_field(
                    name="Error",
                    value=f"You've been blacklisted from using this bot\nTo see why and or get the blacklist removed, send us an email - `contact@agb-dev.xyz` or contact the owners directly - {me1}, {me2}",
                )
                embed.set_thumbnail(url=ctx.message.author.avatar_url)
                embed.set_footer(
                    text="{} | {}".format(
                        ctx.message.created_at, self.process.memory_info().rss
                    )
                )
                embed.set_author(
                    name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url
                )
                embed.set_footer(
                    text="{} | {}".format(
                        ctx.message.created_at, self.process.memory_info().rss
                    )
                )
                bucket = self.message_cooldown.get_bucket(ctx.message)
                retry_after = bucket.update_rate_limit()
                if retry_after:
                    return
                else:
                    try:
                        await ctx.send(embed=embed, delete_after=15)
                        await ctx.message.add_reaction("\u274C")
                    except discord.Forbidden:
                        await ctx.send(
                            f"You don't have permission to run this command.\n***Enable Embed permissions please.***",
                            delete_after=15,
                        )
                        await ctx.message.add_reaction("\u274C")
                        ctx.command.reset_cooldown(ctx)
                        return
            else:
                embed = discord.Embed(title="Error", colour=discord.Colour.red())
                embed.add_field(name="Message", value=ctx.message.content)
                embed.add_field(name="Author", value=ctx.message.author.mention)
                embed.add_field(name="Channel", value=ctx.message.channel.mention)
                embed.add_field(name="Guild", value=ctx.message.guild.name)
                embed.add_field(
                    name="Error", value="You don't have permission to run this command."
                )
                embed.set_thumbnail(url=ctx.message.author.avatar_url)
                embed.set_footer(
                    text="{} | {}".format(
                        ctx.message.created_at, self.process.memory_info().rss
                    )
                )
                embed.set_author(
                    name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url
                )
                embed.set_footer(
                    text="{} | {}".format(
                        ctx.message.created_at, self.process.memory_info().rss
                    )
                )
                bucket = self.message_cooldown.get_bucket(ctx.message)
                retry_after = bucket.update_rate_limit()
                if retry_after:
                    return
                else:
                    try:
                        await ctx.send(embed=embed, delete_after=15)
                        await ctx.message.add_reaction("\u274C")
                    except discord.Forbidden:
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
