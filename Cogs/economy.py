import asyncio
import datetime
import random
from datetime import date, datetime, timedelta
from typing import Union

import discord
from discord.ext import commands
from index import config, cursor, mydb
from utils import default

from .Utils import *


class Economy(commands.Cog, name='economy'):
    """Money stuff bro <:beta:863514446646870076>"""

    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    def format_number(self, number):
        return ("{:,}".format(number))

    @commands.command(usage="`tp!bank`")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def bank(self, ctx):
        """ Check your bank """
        embed = discord.Embed(
            color=EMBED_COLOUR, title=f"{ctx.author.display_name}'s Bank <:beta:863514446646870076>",
            description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote})")
        cursor.execute(f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        row = cursor.fetchall()
        embed.add_field(
            name="Balance", value=f"You currently have **${int(row[0][2]):,}** in your bank. <:beta:863514446646870076>")
        embed.set_footer(
            text="tp!bank withdraw|deposit <amount>")
        embed.set_thumbnail(url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)
        mydb.commit()

    @commands.group(aliases=['dep'], invoke_without_command=True, case_insensitive=True, usage="`tp!deposit <amount>|all`")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def deposit(self, ctx, amount=0):
        if ctx.invoked_subcommand is None:
            cursor.execute(
                f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
            row = cursor.fetchall()
            bal = row[0][1]

            if amount <= 0:
                await ctx.reply("Please deposit an amount greater than **0**! <:beta:863514446646870076>")
                ctx.command.reset_cooldown(ctx)
                return
            if amount > bal:
                await ctx.reply("You don't have that much to deposit. smh <:beta:863514446646870076>")
                ctx.command.reset_cooldown(ctx)
                return

            embed = discord.Embed(
                color=EMBED_COLOUR, title="Bank Deposit <:beta:863514446646870076>",
                description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote})")
            embed.add_field(name="Successful Deposit",
                            value=f"You have deposited **${int(amount):,}** into your bank <:beta:863514446646870076>")
            cursor.execute(
                f"UPDATE userEco SET bank = bank + {amount} WHERE userId = {ctx.author.id}")
            cursor.execute(
                f"UPDATE userEco SET balance = {bal - amount} WHERE userId = {ctx.author.id}")
            await ctx.reply(embed=embed)
            mydb.commit()
            return

    @deposit.command(name="all", usage="`tp!deposit all`")
    async def dep_all(self, ctx):
        cursor.execute(f"SELECT * FROM userEco WHERE userId= {ctx.author.id}")
        row = cursor.fetchall()

        cursor.execute(
            f"UPDATE userEco SET bank = bank + {row[0][1]} WHERE userId = {ctx.author.id}")
        cursor.execute(
            f"UPDATE userEco SET balance = {row[0][1] - row[0][1]} WHERE userId = {ctx.author.id}")
        embed = discord.Embed(color=EMBED_COLOUR, title="Bank Deposit",
                              description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote})")
        embed.add_field(name="Successful Deposit",
                        value=f"You have deposited **${int(row[0][1]):,}** into your bank <:beta:863514446646870076>")
        await ctx.reply(embed=embed)
        mydb.commit()

    @commands.group(aliases=['with'], invoke_without_command=True, case_insensitive=True, usage="`tp!withdraw <amount>|all`")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def withdraw(self, ctx, amount=0):
        if ctx.invoked_subcommand is None:
            cursor.execute(
                f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
            row = cursor.fetchall()
            bal = row[0][1]
            bank_bal = row[0][2]

            if amount <= 0:
                await ctx.reply("Please withdraw an amount greater than **0**! <:beta:863514446646870076>")
                ctx.command.reset_cooldown(ctx)
                return
            if amount > bank_bal:
                await ctx.reply("You don't have that much in your bank. smh <:beta:863514446646870076>")
                ctx.command.reset_cooldown(ctx)
                return

            embed = discord.Embed(
                color=EMBED_COLOUR, title="Bank Withdrawal <:beta:863514446646870076>",
                description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote})")
            embed.add_field(name="Successful Withdrawal",
                            value=f"You have withdrawn **${int(amount):,}** from your bank! <:beta:863514446646870076>")
            cursor.execute(
                f"UPDATE userEco SET balance = {bal + amount} WHERE userId = {ctx.author.id}")
            cursor.execute(
                f"UPDATE userEco SET bank = {bank_bal - amount} WHERE userId = {ctx.author.id}")
            await ctx.reply(embed=embed)
            mydb.commit()
            return

    @withdraw.command(name="all", usage="`tp!withdraw all`")
    async def with_all(self, ctx):
        cursor.execute(f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        row = cursor.fetchall()

        cursor.execute(
            f"UPDATE userEco SET balance = {row[0][1] + row[0][2]} WHERE userId = {ctx.author.id}")
        cursor.execute(
            f"UPDATE userEco SET bank = {row[0][2] - row[0][2]} WHERE userId = {ctx.author.id}")
        embed = discord.Embed(color=EMBED_COLOUR, title="Bank Withdrawal",
                              description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote})")
        embed.add_field(name="Successful Withdrawal",
                        value=f"You have withdrawn **${int(row[0][2]):,}** from your bank! <:beta:863514446646870076>")
        await ctx.reply(embed=embed)
        mydb.commit()

    @commands.command(aliases=['steal'], usage="`tp!rob <user>`")
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def rob(self, ctx, user: Union[discord.Member, discord.User] = None):
        usr = user
        if usr == None:
            await ctx.reply("Please mention a user to rob. smh. <:beta:863514446646870076>")
            ctx.command.reset_cooldown(ctx)
            return
        if usr.id == ctx.author.id:
            await ctx.reply("You can't rob yourself, idiot.")
            ctx.command.reset_cooldown(ctx)
            return

        cursor.execute(f"SELECT * FROM userEco WHERE userId = {usr.id}")
        row = cursor.fetchall()

        if row[0][1] <= 0:
            await ctx.reply(f"You can't rob **{usr.display_name}**. \nThey don't have any money in their wallet! <:beta:863514446646870076>")
            ctx.command.reset_cooldown(ctx)
            return

        chance = random.randint(45, 100)
        rob_amount = row[0][1] / 10
        mydb.commit()

        if chance > 65:
            cursor.execute(
                f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
            row2 = cursor.fetchall()
            # apply the robbed amount to the message author
            cursor.execute(
                f"UPDATE userEco SET balance = {row2[0][1] + rob_amount} WHERE userId = {ctx.author.id}")
            embed = discord.Embed(
                title=f"Robbed **{usr.display_name}** <:beta:863514446646870076>", description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote})",
                color=EMBED_COLOUR)
            embed.add_field(name="Successfully Robbed",
                            value=f"You succeeded and got **${int(rob_amount):,}**! <:beta:863514446646870076>")
            mydb.commit()
            cursor.execute(f"SELECT * FROM userEco WHERE userId = {usr.id}")
            row3 = cursor.fetchall()
            # delete the amount from the victim
            cursor.execute(
                f"UPDATE userEco SET balance = {row3[0][1] - rob_amount} WHERE userId = {usr.id}")
            mydb.commit()
            await ctx.reply(embed=embed)
        else:
            embed2 = discord.Embed(color=EMBED_COLOUR)
            embed2.add_field(
                name="Fail", value=f"You failed to rob **{usr.display_name}**! <:beta:863514446646870076>")
            await ctx.reply(embed=embed2)

    @commands.command(aliases=['job'], usage="`tp!work`")
    @commands.cooldown(rate=1, per=900, type=commands.BucketType.user)
    async def work(self, ctx):
        """ Work for your shitty 9-5 job for a small wage """
        earned = random.randint(500, 10000)
        cursor.execute(f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        # 0 = userId, 1 = balance, 2 = bank, 3 = userTag, 4 = lastDaily, 5 = isBot
        row = cursor.fetchone()[1]
        cursor.execute(
            f"UPDATE userEco SET balance = {row + earned} WHERE userId = {ctx.author.id}")
        mydb.commit()
        await ctx.reply(f"You finshed work and earned **${int(earned):,}** <:beta:863514446646870076>")

    @commands.command(usage="`tp!beg`")
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def beg(self, ctx):
        """ Beg for money like a homeless man """
        chance = random.randint(1, 10)  # 1/10 chance to fail
        earned = random.randint(50, 1000)
        cursor.execute(f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        row = cursor.fetchall()

        if chance > 1:
            cursor.execute(
                f"UPDATE userEco SET balance = {row[0][1] + earned} WHERE userId = {ctx.author.id}")
            mydb.commit()
            await ctx.reply(f"After pathetically begging for money, you earned **${int(earned):,}** <:beta:863514446646870076>")
            return
        else:
            await ctx.reply(f"You spent the entire day begging hopelessly, but nobody gave you anything! Better luck next time loser. <:beta:863514446646870076>")
            return

    @commands.command(aliases=['bal', '$'], usage="`tp!balance`")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def balance(self, ctx, user: Union[discord.Member, discord.User] = None):
        """ Check your balance to see how much more money you can spend before you have to sell your organs """
        usr = user or ctx.author
        cursor.execute(f"SELECT * FROM userEco WHERE userId = {usr.id}")
        row = cursor.fetchall()
        embed = discord.Embed(
            title=f"User Balance <:beta:863514446646870076>",
            description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote})", color=EMBED_COLOUR)
        embed.add_field(
            name="Wallet", value=f"{usr.display_name}'s wallet currently has **${int(row[0][1]):,}**", inline=True)
        embed.add_field(
            name="Bank", value=f"{usr.display_name}'s bank currently has **${int(row[0][2]):,}**", inline=True)
        embed.set_thumbnail(url=usr.avatar_url)
        await ctx.reply(embed=embed)
        mydb.commit()

    @commands.command(usage="`tp!daily`")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def daily(self, ctx):
        """ Get a decent amount of money from the air just cause """
        dailyAmount = 10000
        cursor.execute(
            f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        row = cursor.fetchall()
        if row[0][3] != date.today():
            cursor.execute(
                f"UPDATE userEco SET balance = {row[0][1] + dailyAmount} WHERE userId = {ctx.author.id}")
            cursor.execute(
                f"UPDATE userEco SET lastDaily = '{date.today()}' WHERE userId = {ctx.author.id}")
            mydb.commit()
            await ctx.reply(f"You claimed your daily and earned **${dailyAmount}**! <:beta:863514446646870076>")
        else:
            currentDate = date.today()
            nextDate = currentDate + timedelta(days=1)

            def secs():
                """Get the number of seconds until midnight."""
                n = datetime.now()
                return ((24 - n.hour - 1) * 60 * 60) + ((60 - n.minute - 1) * 60) + (60 - n.second)

            converted_h = str(secs() / 3600)
            hours_left = converted_h.split(".", 1)

            converted_s = str(secs() / 60)
            mins_left = converted_s.split(".", 1)
            total_mins = ""
            if int(mins_left[0]) <= 60:
                total_mins += f", {int(mins_left[0]):,} mins"
            await ctx.reply(f'You have already claimed your daily today.\nYou can claim your next daily on: **{nextDate}** ({hours_left[0]}h{total_mins}) <:beta:863514446646870076>')

    @commands.command(aliases=['msearch'], usage="`tp!search`")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def search(self, ctx, place=None):
        """ Search for money in various places """
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        await ctx.send('Where tf do you wanna search for money?\nYou can search: `car`, `couch`, `tree`, `drawer` (or anywhere u want).\n*Please respond with one of these below*')
        try:
            search_place = await self.bot.wait_for("message", check=check, timeout=45)
        except asyncio.TimeoutError:
            return await ctx.send(f"Timeout exceeded, please re-run {ctx.command} <:beta:863514446646870076>")

        search_place = str(search_place.content)
        earned = random.randint(10, 150)
        cursor.execute(f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        row = cursor.fetchall()
        bal = row[0][1]
        edescription = f"You searched `{search_place}` and found **${int(earned):,}**"
        cursor.execute(
            f"UPDATE userEco SET balance = {bal + earned} WHERE userId = {ctx.author.id}")
        mydb.commit()
        embed = discord.Embed(title="Searched for money",
                              description=edescription, color=EMBED_COLOUR)
        embed.set_thumbnail(url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.command(aliases=['slot', 'smachine'], usage="tp!slots")
    @commands.cooldown(rate=1, per=3.2, type=commands.BucketType.user)
    async def slots(self, ctx, amount: int = 0):
        """ Play a game of slots, earn some or lose some. """

        cursor.execute(f"SELECT * FROM userEco WHERE userId = {ctx.author.id}")
        row = cursor.fetchall()
        amount = int(str(amount))
        bal = row[0][1]

        if amount is None:
            await ctx.reply("Please specify a number to bet on slots!")
            return

        if amount > bal:
            await ctx.reply("You don't have that much money. <:beta:863514446646870076>")
            ctx.command.reset_cooldown(ctx)
            return

        if amount <= 9:
            await ctx.reply("Please specify a number greater than 10 :> <:beta:863514446646870076>")
            ctx.command.reset_cooldown(ctx)
            return

        if amount > 15000:
            await ctx.reply("You cannot bet more than **$15,000** on slots! <:beta:863514446646870076>")
            ctx.command.reset_cooldown(ctx)
            return

        slots = ["🍇", "🍉", "🍊", "🍎", "🎰", "🍍"]
        slot1 = slots[random.randint(0, 5)]
        slot2 = slots[random.randint(0, 5)]
        slot3 = slots[random.randint(0, 5)]

        slotOutput = f"| {slot1} | {slot2} | {slot3} |"

        decent = discord.Embed(
            title="Slots - You Won <:beta:863514446646870076>", color=EMBED_COLOUR)
        decent.add_field(name=f"{slotOutput}",
                         value=f"You won **${int(2*amount):,}**")

        great = discord.Embed(
            title="Slots - You Won <:beta:863514446646870076>", color=EMBED_COLOUR)
        great.add_field(name=f"{slotOutput}",
                        value=f"You won **${int(5*amount):,}**")

        ok = discord.Embed(
            title="Slots - You Won <:beta:863514446646870076>", color=EMBED_COLOUR)
        ok.add_field(name=f"{slotOutput}",
                     value=f"You won **${int(1.5*amount):,}**")

        lost = discord.Embed(
            title="Slots - You Lost <:beta:863514446646870076>", color=EMBED_COLOUR)
        lost.add_field(name=f"{slotOutput}",
                       value=f"You lost **${int(1*amount):,}**")

        if slot1 == slot2 == slot3:
            cursor.execute(
                f"UPDATE userEco SET balance = '{amount * 11.5 + bal}' WHERE userId = {ctx.author.id}")
            mydb.commit()
            await ctx.reply(embed=great)
            return

        if slot1 == slot2:
            cursor.execute(
                f"UPDATE userEco SET balance = '{amount * 2 + bal}' WHERE userId = {ctx.author.id}")
            mydb.commit()
            await ctx.reply(embed=decent)
            return

        if slot2 == slot3:
            cursor.execute(
                f"UPDATE userEco SET balance = '{amount * 1.5 + bal}' WHERE userId = {ctx.author.id}")
            mydb.commit()
            await ctx.reply(embed=ok)
            return

        else:
            cursor.execute(
                f"UPDATE userEco SET balance = '{bal - amount}' WHERE userId = {ctx.author.id}")
            mydb.commit()
            await ctx.reply(embed=lost)
            return


def setup(bot):
    bot.add_cog(Economy(bot))
