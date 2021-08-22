import json
import os

import discord
import psutil
from discord.ext import commands
from discord.ext.commands import errors
from index import Vote, config, delay
from utils import default
from utils.checks import NotVoted


class Error(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process(os.getpid())
        with open('blacklist.json') as f:
            self.blacklist = json.load(f)
        self.default_prefix = 'tp!'
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1.0, 3.0, commands.BucketType.user)

    async def create_embed(self, ctx, error):
        embed = discord.Embed(title='Error', colour=discord.Colour.red())
        embed.add_field(name='Message', value=ctx.message.content)
        embed.add_field(name='Author', value=ctx.message.author.mention)
        embed.add_field(name='Channel', value=ctx.message.channel.mention)
        embed.add_field(name='Guild', value=ctx.message.guild.name)
        embed.add_field(name='Error', value=error)
        embed.set_thumbnail(url=ctx.message.author.avatar_url)
        embed.set_footer(text='{} | {}'.format(ctx.message.created_at, self.process.memory_info().rss))
        embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
        embed.set_footer(text='{} | {}'.format(ctx.message.created_at, self.process.memory_info().rss))
        bucket = self.message_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return
        else:
            try:
                await ctx.send(embed=embed, delete_after=15)
                await ctx.message.add_reaction('\u274C')
            except:
                await ctx.send(f"`{error}`\n***Enable Embed permissions please.***", delete_after=15)
                await ctx.message.add_reaction('\u274C')
                ctx.command.reset_cooldown(ctx)
                return


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if hasattr(ctx.command, "on_error"):
            return
        else:
            pass

        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            helper = str(ctx.invoked_subcommand) if ctx.invoked_subcommand else str(
                ctx.command)
            await ctx.send_help(helper)
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.CommandInvokeError):
            error = default.traceback_maker(error.original)
            if "2000 or fewer" in str(error) and len(ctx.message.clean_content) > 1900:
                return await ctx.send(
                    "You attempted to make the command display more than 2,000 characters...\n"
                    "Both error and command will be ignored."
                )
            await ctx.send(f"There was an error processing the command\n{error}")

        elif isinstance(error, commands.NSFWChannelRequired):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.ChannelNotReadable):
            await self.create_embed(ctx, error)
            
        elif isinstance(error, commands.CommandInvokeError):
            await self.create_embed(ctx, error)

        elif isinstance(error, discord.Forbidden):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.NoPrivateMessage):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.CheckAnyFailure):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.MaxConcurrencyReached):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.BotMissingPermissions):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.MissingPermissions):
            await self.create_embed(ctx, error)
            
        elif isinstance(error, errors.DisabledCommand):
            await self.create_embed(ctx, error)

        elif isinstance(error, NotVoted):
            bucket = self.message_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            embed = discord.Embed(title="Hey now...",
                                  color=discord.Colour.red(), description=f"This command `({ctx.command})` is for voters only!\n Vote **[here]({Vote})**")
            embed.set_thumbnail(
                url=self.bot.user.avatar_url_as(static_format="png"))
            if retry_after:
                return
            else:
                await ctx.send(embed=embed)
                ctx.command.reset_cooldown(ctx)

        elif isinstance(error, commands.NotOwner):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.CheckFailure):
            pass
        
        elif isinstance(error, commands.NoPrivateMessage):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.CommandOnCooldown):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.TooManyArguments):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.MessageNotFound):
            await self.create_embed(ctx, error)

        elif isinstance(error, commands.UserInputError):
            await self.create_embed(ctx, error)


def setup(bot):
    bot.add_cog(Error(bot))
