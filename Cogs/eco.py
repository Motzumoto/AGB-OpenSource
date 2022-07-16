import asyncio
import random
from datetime import date, timedelta
from typing import Union

import discord
from discord.ext import commands
from index import config, cursor_n, cursor_n, mydb_n, mydb_n, EMBED_COLOUR
from Manager.commandManager import cmd
from utils import imports, permissions


class Economy(commands.Cog, name="economy"):
    """Money stuff bro"""

    def __init__(self, bot):
        self.bot = bot
        self.config = imports.get("config.json")
        self.tax_rate = 0
        self.tax_collector = None
        self.yes_responses = {
            "yes": True,
            "yea": True,
            "y": True,
            "ye": True,
            "no": False,
            "n": False,
            "na": False,
            "naw": False,
        }

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    async def bank(self, ctx):
        """Check your bank"""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.group(
        alias=["dep"],
        invoke_without_command=True,
        case_insensitive=True,
    )
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    async def deposit(self, ctx, amount=0):
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @deposit.command(name="all")
    async def dep_all(self, ctx):
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        row = cursor_n.fetchall()

        cursor_n.execute(
            f"UPDATE public.usereco SET bank = bank + '{row[0][1]}' WHERE userid = '{ctx.author.id}'"
        )
        cursor_n.execute(
            f"UPDATE public.usereco SET balance = '{row[0][1] - row[0][1]}' WHERE userid = '{ctx.author.id}'"
        )
        embed = discord.Embed(
            color=EMBED_COLOUR,
            title="Bank Deposit",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
        )
        embed.add_field(
            name="Successful Deposit",
            value=f"You have deposited **${int(row[0][1]):,}** into your bank",
        )
        await ctx.send(
            embed=embed,
        )
        mydb_n.commit()

    @commands.group(
        alias=["with"],
        invoke_without_command=True,
    )
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    async def withdraw(self, ctx, amount=0):
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @withdraw.command(name="all")
    async def with_all(self, ctx):
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        row = cursor_n.fetchall()

        cursor_n.execute(
            f"UPDATE public.usereco SET balance = '{row[0][1] + row[0][2]}'' WHERE userid = '{ctx.author.id}'"
        )
        cursor_n.execute(
            f"UPDATE public.usereco SET bank = '{row[0][2] - row[0][2]}'' WHERE userid = '{ctx.author.id}'"
        )
        embed = discord.Embed(
            color=EMBED_COLOUR,
            title="Bank Withdrawal",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
        )
        embed.add_field(
            name="Successful Withdrawal",
            value=f"You have withdrawn **${int(row[0][2]):,}** from your bank!",
        )
        await ctx.send(
            embed=embed,
        )
        mydb_n.commit()

    @commands.command(alias=["steal"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=30, type=commands.BucketType.user
    )
    async def rob(self, ctx, user: Union[discord.Member, discord.User] = None):
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=10, type=commands.BucketType.user
    )
    async def pay(
        self,
        ctx,
        user: Union[discord.Member, discord.User] = None,
        amount: int = 0,
        note: str = None,
    ):
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.command(alias=["job"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=900, type=commands.BucketType.user
    )
    async def work(self, ctx):
        """Work for your shitty 9-5 job for a small wage"""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=30, type=commands.BucketType.user
    )
    async def beg(self, ctx):
        """Beg for money like a homeless man"""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.command(alias=["bal", "$"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=2, type=commands.BucketType.user
    )
    async def balance(self, ctx, user: Union[discord.Member, discord.User] = None):
        """Check your balance to see how much more money you can spend before you have to sell your organs"""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=10, type=commands.BucketType.user
    )
    async def daily(self, ctx):
        """Get a decent amount of money from the air just cause"""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.command(alias=["msearch"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=10, type=commands.BucketType.user
    )
    async def search(self, ctx, place: str = None):
        """Search for money in various places"""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

    @commands.command(alias=["slot", "smachine"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=3.2, type=commands.BucketType.user
    )
    async def slots(self, ctx, amount: int):
        """Play a game of slots, earn some or lose some."""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return


async def setup(bot):
    await bot.add_cog(Economy(bot))
