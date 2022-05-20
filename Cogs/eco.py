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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        embed = discord.Embed(
            color=EMBED_COLOUR,
            title=f"{ctx.author.display_name}'s Bank",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
        )
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        row = cursor_n.fetchall()
        embed.add_field(
            name="`Balance`",
            value=f"You currently have **${int(row[0][2]):,}** in your bank.",
        )
        embed.set_footer(text="tp!bank withdraw|deposit amount")
        embed.set_thumbnail(url=ctx.author.avatar)
        await ctx.send(
            embed=embed,
        )
        mydb_n.commit()

    @commands.group(
        alias=["dep"],
        invoke_without_command=True,
        case_insensitive=True,
    )
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    async def deposit(self, ctx, amount=0):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        if ctx.invoked_subcommand is None:
            cursor_n.execute(
                f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
            )
            row = cursor_n.fetchall()
            bal = row[0][1]

            if amount <= 0:
                await ctx.send("Please deposit an amount greater than **0**!")

                return
            if amount > bal:
                await ctx.send("You don't have that much to deposit. smh")

                return

            embed = discord.Embed(
                color=EMBED_COLOUR,
                title="Bank Deposit",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            )
            embed.add_field(
                name="Successful Deposit",
                value=f"You have deposited **${int(amount):,}** into your bank",
            )
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = bank + '{amount}' WHERE userid = '{ctx.author.id}'"
            )
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{bal - amount}' WHERE userid = '{ctx.author.id}'"
            )
            await ctx.send(
                embed=embed,
            )
            mydb_n.commit()

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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        if ctx.invoked_subcommand is None:
            cursor_n.execute(
                f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
            )
            row = cursor_n.fetchall()
            bal = row[0][1]
            bank_bal = row[0][2]
            mydb_n.commit()
            if amount <= 0:
                await ctx.send("Please withdraw an amount greater than **0**!")

                return
            if amount > bank_bal:
                await ctx.send("You don't have that much in your bank. smh")

                return

            embed = discord.Embed(
                color=EMBED_COLOUR,
                title="Bank Withdrawal",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            )
            embed.add_field(
                name="Successful Withdrawal",
                value=f"You have withdrawn **${int(amount):,}** from your bank!",
            )
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{bal + amount}' WHERE userid = '{ctx.author.id}'"
            )
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '{bank_bal - amount}' WHERE userid = '{ctx.author.id}'"
            )
            mydb_n.commit()
            await ctx.send(
                embed=embed,
            )

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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        usr = user
        if usr is None:
            await ctx.send("Please mention a user to rob. smh.")

            return
        if usr.id == ctx.author.id:
            await ctx.send("You can't rob yourself, idiot.")

            return

        cursor_n.execute(f"SELECT * FROM public.usereco WHERE \"userid\" = '{usr.id}'")
        row = cursor_n.fetchall()

        if row[0][1] <= 0:
            await ctx.send(
                f"You can't rob **{usr.display_name}**. \nThey don't have any money in their wallet!"
            )

            return

        chance = random.randint(45, 100)
        rob_amount = row[0][1] / 10
        mydb_n.commit()

        if chance > 65:
            cursor_n.execute(
                f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
            )
            row2 = cursor_n.fetchall()
            # apply the robbed amount to the message author
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{row2[0][1] + rob_amount}' WHERE userid = '{ctx.author.id}'"
            )
            embed = discord.Embed(
                title=f"Robbed **{usr.display_name}**",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                color=EMBED_COLOUR,
            )
            embed.add_field(
                name="Successfully Robbed",
                value=f"You succeeded and got **${int(rob_amount):,}**!",
            )
            mydb_n.commit()
            cursor_n.execute(
                f"SELECT * FROM public.usereco WHERE \"userid\" = '{usr.id}'"
            )
            row3 = cursor_n.fetchall()
            # delete the amount from the victim
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{row3[0][1] - rob_amount}' WHERE userid = '{usr.id}'"
            )
            mydb_n.commit()
            await ctx.send(
                embed=embed,
            )
        else:
            embed2 = discord.Embed(color=EMBED_COLOUR)
            embed2.add_field(
                name="Fail",
                value=f"You failed to rob **{usr.display_name}**!",
            )
            await ctx.send(embed=embed2)

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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        await ctx.channel.typing()()

        if user is None:
            await ctx.send("Please mention a user to pay.")

            return
        elif user.id == ctx.author.id:
            await ctx.send("You can't pay yourself.")

            return

        def yes_check(m):
            return (
                m.channel == ctx.channel
                and m.author.id == ctx.author.id
                and m.content in self.yes_responses
            )

        # Fetch the author's banking information.
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        row = cursor_n.fetchall()

        # Check if they have enough in their account.
        print(row[0][2])
        if row[0][2] < amount:
            total = row[0][1] + row[0][2]
            # If they don't have enough money combined, tell them they can't do
            # the transaction.
            if total < amount:
                await ctx.send(
                    f"You don't have enough to pay - you only have ${total}."
                )

                return

            else:  # If they do have enough money in total, tell them it is possible but they need to do a bank transfer.
                to_transfer = amount - row[0][2]
                # await ctx.send(f"You don't have enough in your bank\nTry
                # transfering from your wallet into the bank with `tp!dep
                # {to_transfer}`")
                await ctx.send(
                    f"You don't have enough money in your bank.\nWould you like to transfer ${to_transfer} into your bank from your wallet and continue? [y/N]"
                )

                try:  # If they do have enough, ask them if they want to transfer.
                    response = await self.bot.wait_for(
                        "message", check=yes_check, timeout=30
                    )

                except asyncio.TimeoutError:
                    await ctx.send(
                        f"Took too long to respond. If you still want to transfer, you can still do `tp!dep {to_transfer}`."
                    )

                    return

                else:
                    # If they say yes, then complete the transfer.
                    if self.yes_responses[response.content]:
                        new_wallet = row[0][1] - to_transfer
                        cursor_n.execute(
                            f"UPDATE public.usereco SET balance = '{new_wallet}' WHERE userid = '{ctx.author.id}'"
                        )
                        cursor_n.execute(
                            f"UPDATE public.usereco SET bank = '{new_wallet}' WHERE userid = '{ctx.author.id}'"
                        )

                        cursor_n.execute(
                            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
                        )
                        row = cursor_n.fetchall()

                    else:
                        return

        cursor_n.execute(
            "SELECT * FROM public.globalvars WHERE variablename = 'taxData'"
        )
        tax_info = cursor_n.fetchall()
        taxed_amount = int(amount * (1 - tax_info[0][1]))
        # await ctx.send(tax_info[0][1])

        # Fetch the recipient's bank information
        cursor_n.execute(f"SELECT * FROM public.usereco WHERE \"userid\" = '{user.id}'")
        row2 = cursor_n.fetchall()

        # Give the taxed amount to the recipient's bank
        new_balance = row2[0][2] + taxed_amount
        cursor_n.execute(
            f"UPDATE public.usereco SET bank = '{new_balance}' WHERE userid = '{user.id}'"
        )

        # Take the (non-taxed) money from the author's account
        new_balance = row[0][2] - amount
        cursor_n.execute(
            f"UPDATE public.usereco SET bank = '{new_balance}' WHERE userid = '{ctx.author.id}'"
        )

        if tax_info[0][2] is not None and tax_info[0][1] != 0:
            cursor_n.execute(
                f"SELECT * FROM public.usereco WHERE \"userid\" = '{tax_info[0][2]}'"
            )
            tax_collect_bank = cursor_n.fetchall()
            new_balance = tax_collect_bank[0][2] + (amount - taxed_amount)
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '{new_balance}' WHERE userid = '{tax_info[0][2]}'"
            )

        if note is None:
            try:
                await user.send(
                    f"{str(ctx.author)} just paid you ${taxed_amount}, with a tax rate of {int(tax_info[0][1] * 100)}%."
                )
            except discord.errors.Forbidden:
                await ctx.send(
                    f"You just paid {user.mention} ${taxed_amount}, with a tax rate of {int(tax_info[0][1] * 100)}%."
                )
            else:
                await ctx.send(
                    f"You just paid {str(user)} ${taxed_amount}, with a tax rate of {int(tax_info[0][1] * 100)}%."
                )
        else:
            try:
                await user.send(
                    f"{str(ctx.author)} just paid you ${taxed_amount}, with a tax rate of {int(tax_info[0][1] * 100)}%.\nNote from {str(ctx.author)}:\n{note}"
                )
            except discord.errors.Forbidden:
                await ctx.send(
                    f"You just paid {user.mention} ${taxed_amount}, with a tax rate of {int(tax_info[0][1] * 100)}%.\nNote from {str(ctx.author)}:\n{note}"
                )
            else:
                await ctx.send(
                    f"You just paid {str(user)} ${taxed_amount}, with a tax rate of {int(tax_info[0][1] * 100)}%."
                )

    @commands.command(alias=["job"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=900, type=commands.BucketType.user
    )
    async def work(self, ctx):
        """Work for your shitty 9-5 job for a small wage"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        earned = random.randint(500, 10000)
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        # 0 = userid, 1 = balance, 2 = bank, 3 = userTag, 4 = lastDaily, 5 =
        # isBot
        row = cursor_n.fetchone()[1]
        cursor_n.execute(
            f"UPDATE public.usereco SET balance = '{row + earned}' WHERE userid = '{ctx.author.id}'"
        )
        mydb_n.commit()
        await ctx.send(f"You finshed work and earned **${int(earned):,}**")

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=30, type=commands.BucketType.user
    )
    async def beg(self, ctx):
        """Beg for money like a homeless man"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        chance = random.randint(1, 10)  # 1/10 chance to fail
        earned = random.randint(50, 1000)
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        row = cursor_n.fetchall()

        if chance > 1:
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{row[0][1] + earned}' WHERE userid = '{ctx.author.id}'"
            )
            mydb_n.commit()
            await ctx.send(
                f"After pathetically begging for money, you earned **${int(earned):,}**"
            )
        else:
            await ctx.send(
                f"You spent the entire day begging hopelessly, but nobody gave you anything! Better luck next time loser."
            )

    @commands.command(alias=["bal", "$"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=2, type=commands.BucketType.user
    )
    async def balance(self, ctx, user: Union[discord.Member, discord.User] = None):
        """Check your balance to see how much more money you can spend before you have to sell your organs"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        usr = user or ctx.author
        cursor_n.execute(f"SELECT * FROM public.usereco WHERE \"userid\" = '{usr.id}'")
        row = cursor_n.fetchall()
        embed = discord.Embed(
            title=f"User Balance",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            color=EMBED_COLOUR,
        )
        embed.add_field(
            name="Wallet",
            value=f"{usr.display_name}'s wallet currently has **${int(row[0][1]):,}**",
            inline=True,
        )
        embed.add_field(
            name="Bank",
            value=f"{usr.display_name}'s bank currently has **${int(row[0][2]):,}**",
            inline=True,
        )
        embed.set_thumbnail(url=usr.avatar)
        await ctx.send(
            embed=embed,
        )
        mydb_n.commit()

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=10, type=commands.BucketType.user
    )
    async def daily(self, ctx):
        """Get a decent amount of money from the air just cause"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        dailyAmount = 10000
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        row = cursor_n.fetchall()
        if row[0][3] != date.today():
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{row[0][1] + dailyAmount}' WHERE userid = '{ctx.author.id}'"
            )
            cursor_n.execute(
                f"UPDATE public.usereco SET lastdaily = '{date.today()}' WHERE userid = '{ctx.author.id}'"
            )
            mydb_n.commit()
            await ctx.send(f"You claimed your daily and earned **${dailyAmount}**!")
        else:
            currentDate = date.today()
            nextDate = currentDate + timedelta(days=1)

            def secs():
                """Get the number of seconds until midnight."""
                n = discord.utils.now()
                return (
                    ((24 - n.hour - 1) * 60 * 60)
                    + ((60 - n.minute - 1) * 60)
                    + (60 - n.second)
                )

            converted_h = str(secs() / 3600)
            h_left_string = float(converted_h)
            f_string = ""

            if float(h_left_string) < 10:
                f_string += (
                    str(int(converted_h[0]))
                    + str(converted_h[1])
                    + str(int(converted_h[2]))
                )
            else:
                f_string += (
                    str(int(converted_h[0]))
                    + str(converted_h[1])
                    + str(converted_h[2])
                    + str(int(converted_h[3]))
                )

            final = f"{f_string}" if float(h_left_string) < 10 else f"{f_string}"

            await ctx.send(
                f"You have already claimed your daily today.\nYou can claim your next daily on: **{nextDate}** ({final}h)"
            )

    @commands.command(alias=["msearch"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=10, type=commands.BucketType.user
    )
    async def search(self, ctx, place: str = None):
        """Search for money in various places"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        await ctx.send(
            "Where tf do you wanna search for money?\nYou can search: `car`, `couch`, `tree`, `drawer` (or anywhere u want).\n*Please respond with one of these below*"
        )
        try:
            search_place = await self.bot.wait_for("message", check=check, timeout=45)
        except asyncio.TimeoutError:
            return await ctx.send(f"Timeout exceeded, please re-run {ctx.command}")

        search_place = str(search_place.content)
        earned = random.randint(10, 150)
        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )
        row = cursor_n.fetchall()
        bal = row[0][1]
        edescription = f"You searched `{search_place}` and found **${int(earned):,}**"
        cursor_n.execute(
            f"UPDATE public.usereco SET balance = '{bal + earned}' WHERE userid = '{ctx.author.id}'"
        )
        mydb_n.commit()
        embed = discord.Embed(
            title="Searched for money",
            description=edescription,
            color=EMBED_COLOUR,
        )
        embed.set_thumbnail(url=ctx.author.avatar)
        await ctx.send(
            embed=embed,
        )

    @commands.command(alias=["slot", "smachine"])
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=3.2, type=commands.BucketType.user
    )
    async def slots(self, ctx, amount: int):
        """Play a game of slots, earn some or lose some."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.send(
            "This command has been encountering an errors as of late, please try again later."
        )
        return

        cursor_n.execute(
            f"SELECT * FROM public.usereco WHERE \"userid\" = '{ctx.author.id}'"
        )

        if amount is None:
            amount = int(0)

        row = cursor_n.fetchall()
        amount = int(str(amount))
        bal = row[0][1]

        if amount is None:
            await ctx.send("Please specify a number to bet on slots!")
            return

        if amount > bal:
            await ctx.send("You don't have that much money.")

            return

        if amount <= 9:
            await ctx.send("Please specify a number greater than 10 :>")

            return

        if amount > 15000:
            await ctx.send("You cannot bet more than **$15,000** on slots!")

            return

        slots = ["🍇", "🍉", "🍊", "🍎", "🎰", "🍍"]
        slot1 = slots[random.randint(0, 5)]
        slot2 = slots[random.randint(0, 5)]
        slot3 = slots[random.randint(0, 5)]

        slotOutput = f"| {slot1} | {slot2} | {slot3} |"

        startOutput = f"| <a:slots:952031344324657162> | <a:slots:952031344324657162> | <a:slots:952031344324657162> |"

        start = discord.Embed(
            title="Slots", description=startOutput, color=EMBED_COLOUR
        )

        rolling = await ctx.send(embed=start)

        await asyncio.sleep(1)

        decent = discord.Embed(
            title="Slots - You Won",
            color=EMBED_COLOUR,
        )
        decent.add_field(name=f"{slotOutput}", value=f"You won **${int(5*amount):,}**")
        decent.set_footer(text=f"You have {bal + (5*amount):,} left")

        great = discord.Embed(
            title="Slots - You Won",
            color=EMBED_COLOUR,
        )
        great.add_field(name=f"{slotOutput}", value=f"You won **${int(10*amount):,}**")
        great.set_footer(text=f"You have {bal + (10*amount):,} left")

        ok = discord.Embed(
            title="Slots - You Won",
            color=EMBED_COLOUR,
        )
        ok.add_field(name=f"{slotOutput}", value=f"You won **${int(2*amount):,}**")
        ok.set_footer(text=f"You have {bal + (2*amount):,} left")

        lost = discord.Embed(
            title="Slots - You Lost",
            color=EMBED_COLOUR,
        )
        lost.add_field(name=f"{slotOutput}", value=f"You lost **${int(1*amount):,}**")
        lost.set_footer(text=f"You have {bal - amount:,} left")

        if slot1 == slot2 == slot3:
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{amount * 10 + bal}' WHERE userid = '{ctx.author.id}'"
            )
            mydb_n.commit()
            await rolling.edit(embed=great)
            return

        if slot1 == slot2:
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{amount * 5 + bal}' WHERE userid = '{ctx.author.id}'"
            )
            mydb_n.commit()
            await rolling.edit(embed=decent)
            return

        if slot2 == slot3:
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{amount * 2 + bal}' WHERE userid = '{ctx.author.id}'"
            )
            mydb_n.commit()
            await rolling.edit(embed=ok)

        else:
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{bal - amount}' WHERE userid = '{ctx.author.id}'"
            )
            mydb_n.commit()
            await rolling.edit(embed=lost)


async def setup(bot):
    await bot.add_cog(Economy(bot))
