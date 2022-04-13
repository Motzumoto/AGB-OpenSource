import asyncio
import concurrent
import importlib
import io
import datetime
from datetime import timedelta
import os
import re
import subprocess
import textwrap
import traceback
from contextlib import redirect_stdout
from subprocess import check_output
from typing import Union

import aiohttp
import discord
import nekos
import psycopg
import speedtest
from discord import app_commands
from discord.ext import commands
from index import EMBED_COLOUR, cursor_n, delay, logger, mydb_n
from Manager.database import pool
from Manager.logger import formatColor
from matplotlib.pyplot import contour
from psycopg import cursor
from utils import default, http, permissions
from utils.default import log

from .Utils import *


class Admin(commands.Cog, name="admin", command_attrs=dict(hidden=True)):
    """Commands that arent for you lol"""

    def __init__(self, bot: commands.Bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = default.get("config.json")
        os.environ.setdefault("JISHAKU_HIDE", "1")
        self._last_result = None
        self.last_change = None
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
            "nah": False,
        }
        self.modules = [
            "nsfw_neko_gif",
            "anal",
            "les",
            "hentai",
            "bj",
            "cum_jpg",
            "tits",
            "pussy_jpg",
            "pwankg",
            "classic",
            "spank",
            "boobs",
            "random_hentai_gif",
        ]
        self.email_re = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
        self.blacklisted = False
        self.blacklist = self.blacklisted_users()
        bot.add_check(self.blacklist_check)
        self.nword_re = re.compile(
            r"\b(n|m|и|й)(i|1|l|!|ᴉ|¡)(g|ƃ|6|б)(g|ƃ|6|б)(e|3|з|u)(r|Я)\b", re.I
        )
        self.afks = {}

    # this is mainly to make sure that the code is loading the json file if
    # new data gets added

    async def get_hentai_img(self):
        if random.randint(1, 2) == 1:
            url = nekos.img(random.choice(self.modules))
        else:
            other_stuff = ["bondage", "hentai", "thighs"]
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://api.dbot.dev/images/nsfw/{random.choice(other_stuff)}"
                ) as r:
                    j = await r.json()
                    url = j["url"]
        return url

    def blacklisted_users(self) -> list:
        cursor_n.execute(
            f"SELECT userid FROM public.blacklist WHERE blacklisted = 'true'"
        )

        return [int(row[0]) for row in cursor_n.fetchall()]

    def blacklist_check(self, ctx):
        try:
            cursor_n.execute(
                f"SELECT blacklisted FROM public.blacklist WHERE userid = '{ctx.author.id}'"
            )
        except:
            pass
        for row in cursor_n.fetchall():
            self.blacklisted = row[0]
        if self.blacklisted == "false":
            return True
        elif self.blacklisted == None:
            return True
        else:
            return False

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await self.bot.loop.run_in_executor(None, process.communicate)
        return [output.decode() for output in result]

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        # remove `foo`
        return content.strip("` \n")

    async def try_to_send_msg_in_a_channel(self, guild, msg):
        for channel in guild.channels:
            try:
                await channel.send(msg)
                break
            except:
                pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if "n word" in guild.name.lower():
            await self.try_to_send_msg_in_a_channel(
                guild, "im gonna leave cuz of the server name"
            )
            return await guild.leave()
        for channel in guild.channels:
            if "n word" in channel.name.lower():
                await self.try_to_send_msg_in_a_channel(
                    guild, f"im gonna leave cuz of the channel name {channel.mention}"
                )
                return await guild.leave()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member, guild=None):
        me = self.bot.get_user(101118549958877184)
        guild = member.guild
        embed = discord.Embed(title="User Joined", colour=discord.Colour.green())
        embed.add_field(
            name=f"Welcome {member}",
            value=f"Welcome {member.mention} to {guild.name}!\nPlease read <#776514195465568257> to get color roles for yourself and common questions about AGB!",
        )
        embed.add_field(
            name="Account Created",
            value=member.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"),
            inline=False,
        )
        embed.set_thumbnail(url=member.avatar)
        if member.guild.id == 755722576445046806:
            if member.bot:
                role = discord.utils.get(guild.roles, name="Bots")
                await member.add_roles(role)
                return
            else:
                role = discord.utils.get(guild.roles, name="Members")
                await member.add_roles(role)
                channel = self.bot.get_channel(755722577049026567)
                await channel.send(
                    content=f"Guild member count: {guild.member_count}",
                    embed=embed,
                    delete_after=10,
                )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member, guild=None):
        guild = member.guild
        if member.guild.id == 755722576445046806:
            if member.bot:
                return
            else:
                channel = self.bot.get_channel(755722577049026567)
                await channel.send(
                    f"{member.name} left. Guild member count: {guild.member_count}",
                    delete_after=5,
                )

    @commands.group(aliases=["eco"], pass_context=True, hidden=True)
    @commands.check(permissions.is_owner)
    async def economy(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please use a subcommand. (eco)")

    @economy.command(aliases=["give"], hidden=True)
    @commands.check(permissions.is_owner)
    async def add(
        self,
        ctx,
        amount: int,
        user: Union[discord.User, discord.Member] = None,
        account: str = "bank",
    ):
        if amount == 0:
            await ctx.send("Please enter a non-zero amount.")
            return
        elif amount < 0:
            await ctx.send(f"Please use tp!eco remove {abs(amount)}")
            return

        if user is None:
            user = ctx.author

        # Fetch user's banking information
        cursor_n.execute("SELECT * FROM userEco WHERE userid = %s", (user.id,))
        row = cursor_n.fetchall()

        if account == "bank":
            account_to_change = row[0][2]
        elif account == "wallet" or account == "balance":
            account_to_change = row[0][1]
            account = "balance"
        else:
            await ctx.send("You can only give to either the `bank` or `wallet`.")
            return

        final_amount = account_to_change + amount
        if account == "bank":
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '{final_amount}' WHERE userid = '{user.id}'"
            )
        elif account == "wallet" or account == "balance":
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{final_amount}' WHERE userid = '{user.id}'"
            )
        await ctx.send(
            f"Gave ${amount} to {str(user)}, their {account} is now at ${account_to_change + amount}"
        )

    @economy.command(aliases=["take"], hidden=True)
    @commands.check(permissions.is_owner)
    async def remove(
        self,
        ctx,
        amount: int,
        user: Union[discord.User, discord.Member] = None,
        account: str = "bank",
    ):
        if amount == 0:
            await ctx.send("Please enter a non-zero amount.")
            return
        elif amount < 0:
            await ctx.send(f"Please use tp!eco add {abs(amount)}")
            return

        if user is None:
            user = ctx.author

        # Fetch user's banking information
        cursor_n.execute(f"SELECT * FROM public.usereco WHERE \"userid\" = '{user.id}'")
        row = cursor_n.fetchall()

        if account == "bank":
            account_to_change = row[0][2]
        elif account == "wallet" or account == "balance":
            account_to_change = row[0][1]
            account = "balance"
        else:
            await ctx.send("You can only take from either the `bank` or `wallet`.")
            return

        final_balance = account_to_change - amount
        if final_balance < 0:
            await ctx.send(
                f"This would cause the user's balance to be a negative number.\nYou may take a max of ${account_to_change}."
            )
            return

        if account == "bank":
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '{amount}' WHERE userid = '{user.id}'",
                (
                    final_balance,
                    user.id,
                ),
            )
        elif account == "balance" or account == "wallet":
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{amount}' WHERE userid = '{user.id}'",
                (
                    final_balance,
                    user.id,
                ),
            )
        await ctx.send(
            f"Took ${amount} from {str(user)}, their {account} is now at ${account_to_change + amount}"
        )

    @economy.command(hidden=True)
    @commands.check(permissions.is_owner)
    async def set(
        self,
        ctx,
        amount: int,
        user: Union[discord.User, discord.Member] = None,
        account: str = "bank",
    ):
        if user is None:
            user = ctx.author
        if amount == 0:
            await ctx.send(f"Please use `tp!eco reset {user.id} {account}`")
            return
        elif amount < 0:
            await ctx.send(f"Please enter a positive, non-zero number.")
            return

        if account == "bank":
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '{amount}' WHERE userid = '{user.id}'"
            )
            await ctx.send(f"Set bank to ${amount} for {str(user)}.")
        elif account == "wallet" or account == "balance":
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{amount}' WHERE userid = '{user.id}'"
            )
            await ctx.send(f"Set wallet to ${amount} for {str(user)}.")
        else:
            await ctx.send("Please choose either `bank` or `wallet`.")

    @economy.command(aliases=["clear", "wipe"], hidden=True)
    @commands.check(permissions.is_owner)
    async def reset(
        self,
        ctx,
        user: Union[discord.User, discord.Member] = None,
        account: str = "both",
    ):
        if user is None:
            user = ctx.author

        def check(m):
            return (
                m.channel == ctx.channel
                and m.author == ctx.author
                and m.content in self.yes_responses
            )

        if account == "both":
            to_erase = "bank and wallet"
        elif account == "bank":
            to_erase = account
        elif account == "wallet" or account == "balance":
            to_erase = "balance"

        await ctx.send(
            f"Are you sure you want to erase {str(user)}'s {to_erase}?\n**This action cannot be undone.**"
        )
        try:
            response = await self.bot.wait_for("message", check=check, timeout=15)
        except asyncio.TimeoutError:
            await ctx.send("Canceled.")
            return
        if not self.yes_responses[response.content]:
            ctx.send("Canceled")
            return

        if account == "both" or account == "bank":
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '0' WHERE userid = '{user.id}'"
            )
        if account == "both" or account == "wallet" or account == "balance":
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '0' WHERE userid = '{user.id}'"
            )
        await ctx.send(f"Cleared {to_erase} for {str(user)}")

    @economy.group(pass_context=True, hidden=True)
    @commands.check(permissions.is_owner)
    async def setting(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please use a subcommand. (set)")

    @setting.command(aliases=["tax", "change_tax"], hidden=True)
    @commands.check(permissions.is_owner)
    async def set_tax(self, ctx, new_tax: float):
        """Set a tax rate - Must be a decimal, such that `12%` would be `0.12`"""

        cursor_n.execute(
            f"UPDATE public.globalvars SET variableData = '{new_tax}' WHERE variableName = 'taxData'"
        )
        cursor_n.execute(
            f"SELECT * FROM public.globalvars WHERE variableName = 'taxData'"
        )
        row = cursor_n.fetchall()
        await ctx.send(f"Tax rate changed to {int(row[0][1] * 100)}%.")

    @setting.command(aliases=["collector", "bastard"], hidden=True)
    @commands.check(permissions.is_owner)
    async def set_collector(
        self, ctx, user: Union[discord.User, discord.Member] = None
    ):
        """Sets everyone's least favorite person in the world."""
        if user is not None:
            cursor_n.execute(
                f"UPDATE public.globalvars SET variableData2 = '{user.id}' WHERE variableName = 'taxData'"
            )
        else:
            cursor_n.execute(
                f"UPDATE public.globalvars SET variableData2 = '{None}' WHERE variableName = 'taxData'"
            )

        cursor_n.execute(
            "SELECT * FROM public.globalvars WHERE variableName = 'taxData'"
        )
        row = cursor_n.fetchall()
        if row[0][2] is None:
            await ctx.send(
                f"Tax collector cleared. User might still be taxed, but no one will collect it."
            )
        else:
            await ctx.send(f"Tax collector set to {str(user)} (ID: {row[0][2]})")

    @commands.check(permissions.is_owner)
    @commands.command()
    async def eval(self, ctx, *, body: str):
        """Evaluates a code"""
        async with ctx.channel.typing():
            if "token" in body:
                await ctx.send(
                    "We're no strangers to love \nYou know the rules and so do I \nA full commitment's what I'm thinking of \nYou wouldn't get this from any other guy \nI just wanna tell you how I'm feeling\nGotta make you understand\nNever gonna give you up\nNever gonna let you down\nNever gonna run around and desert you\nNever gonna make you cry\nNever gonna say goodbye\nNever gonna tell a lie and hurt you"
                )
                return
        env = {
            "self": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
        }
        env.update(globals())
        body = self.cleanup_code(body)
        stdout = io.StringIO()
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        embed = discord.Embed(
            title="Evaluation",
            colour=EMBED_COLOUR,
            description=f"Input\n```py\n{ctx.message.content[8:]}\n```",
        )

        try:
            exec(to_compile, env)
        except Exception as e:
            await ctx.message.add_reaction("\u274C")
            embed.add_field(
                name="Error",
                value=f"```py\n{e.__class__.__name__}: {e}\n```",
                inline=True,
            )
            # await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
            await ctx.send(embed=embed)
            return

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            embed.add_field(
                name="Output",
                value=f"```py\n{value}{traceback.format_exc()}\n```",
                inline=True,
            )
            # await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
            await ctx.send(embed=embed)
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except:
                pass
            if ret is None:
                if value:
                    embed.add_field(
                        name="Result", value=f"```py\n{value}\n```", inline=True
                    )
                    # await ctx.send(f'```py\n{value}\n```')
                    await ctx.send(embed=embed)
            else:
                self._last_result = ret
                embed.add_field(
                    name="Result", value=f"```py\n{value}{ret}\n```", inline=True
                )
                # await ctx.send(f'```py\n{value}{ret}\n```')
                await ctx.send(embed=embed)

    @commands.check(permissions.is_owner)
    @commands.command()
    async def spokemost(self, ctx):
        """Shows the user who has spoken the most in the server"""
        # iterate through the servers channels and messages and collect the messages
        channel_messages = []
        what_channel_we_are_in = await ctx.send("Getting messages...")
        for channel in ctx.guild.text_channels:
            async for message in channel.history(limit=None):
                if not message.author.bot:
                    channel_messages.append(message)
                    if len(channel_messages) % 50 == 0:
                        await what_channel_we_are_in.edit(
                            f"We're in {channel.name} now, we've gathered {len(channel_messages)} messages"
                        )

        # iterate through the messages and count the number of times each user has spoken
        speaker_count = {}
        for message in channel_messages:
            if message.author.id in speaker_count:
                speaker_count[message.author.id] += 1
            else:
                speaker_count[message.author.id] = 1

        # find the user with the most messages
        most_messages = max(speaker_count.values())
        most_messages_users = []
        for user in speaker_count:
            if speaker_count[user] == most_messages:
                most_messages_users.append(user)

        # find the user with the most messages
        most_messages_user = most_messages_users[0]
        for user in most_messages_users:
            if (
                ctx.guild.get_member(user).display_name
                > ctx.guild.get_member(most_messages_user).display_name
            ):
                most_messages_user = user

        # find the user with the most messages
        most_messages_user = ctx.guild.get_member(most_messages_user)

        # send the message
        await ctx.send(
            f"{most_messages_user.mention} has spoken the most in the server! ({most_messages} messages)"
        )

    @commands.check(permissions.is_owner)
    @commands.command()
    async def whatcanyousee(self, ctx):
        """Displays what channels the bot can see"""
        channel_list = ""
        for channel in ctx.guild.text_channels:
            channel_list += f"{channel.mention}\n"
        await ctx.send(f"Here are the channels I can see:\n{channel_list}")

    @commands.check(permissions.is_owner)
    @commands.command(hidden=True)
    async def ghost(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command()
    async def owner(self, ctx):
        """Did you code me?"""
        async with ctx.channel.typing():
            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass
            if ctx.author.id in self.config.owners:
                return await ctx.send(
                    f"Yes **{ctx.author.name}** \nYou Coded Me ", delete_after=delay
                )
            if ctx.author.id == 632753468896968764:
                return await ctx.send(
                    f"**{ctx.author.name}**Hi there :)", delete_after=delay
                )
            await ctx.send(f"no, heck off {ctx.author.name}", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def load(self, ctx, *names):
        """Loads an extension."""
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        for name in names:
            try:
                await self.bot.load_extension(f"Cogs.{name}")
            except Exception as e:
                await ctx.send(default.traceback_maker(e))
                await ctx.message.add_reaction("\u274C")
                return
            await ctx.message.add_reaction("\u2705")
            await ctx.send(f"Loaded extension **{name}.py**", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def unload(self, ctx, *names):
        """Unloads an extension."""
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        for name in names:
            try:
                await self.bot.unload_extension(f"Cogs.{name}")
            except Exception as e:
                return await ctx.send(default.traceback_maker(e))
            await ctx.send(
                f"Unloaded extension **{name}.py** {ctx.author.mention}",
                delete_after=delay,
            )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reload(self, ctx, *names):
        """Reloads an extension."""
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        for name in names:
            try:
                await self.bot.reload_extension(f"Cogs.{name}")
            except Exception as e:
                await ctx.send(default.traceback_maker(e))
                await ctx.message.add_reaction("\u274C")
                return
            await ctx.message.add_reaction("\u2705")
        if len(names) == 1:
            await ctx.send(
                f"Reloaded extension **{name}.py** {ctx.author.mention}",
                delete_after=delay,
            )
        else:
            await ctx.send(
                f"Reloaded the following extensions\n"
                + "\n".join(f"**{name}.py**" for name in names),
                delete_after=delay,
            )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def loadall(self, ctx):
        """Loads all extensions"""
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    await self.bot.load_extension(
                        f"Cogs.{name}",
                    )
                except Exception as e:
                    error_collection.append(
                        [file, default.traceback_maker(e, advance=False)]
                    )
        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            await ctx.message.add_reaction("\u274C")
            return await ctx.send(
                f"Attempted to load all extensions, was able to but... "
                f"the following failed...\n\n{output}"
            )
        await ctx.message.add_reaction("\u2705")
        await ctx.send(
            f"Successfully loaded all extensions {ctx.author.mention}",
            delete_after=delay,
        )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadall(self, ctx):
        """Reloads all extensions."""
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    await self.bot.reload_extension(
                        f"Cogs.{name}",
                    )
                except Exception as e:
                    error_collection.append(
                        [file, default.traceback_maker(e, advance=False)]
                    )
        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            await ctx.message.add_reaction("\u274C")
            return await ctx.send(
                f"Attempted to reload all extensions, was able to reload, "
                f"however the following failed...\n\n{output}"
            )
        await ctx.message.add_reaction("\u2705")
        await ctx.send(
            f"Successfully reloaded all extensions {ctx.author.mention}",
            delete_after=delay,
        )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadutils(self, ctx, *names):
        """Reloads a utils module."""
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        for name in names:
            try:
                module_name = importlib.import_module(f"utils.{name}")
                importlib.reload(module_name)
            except Exception as e:
                await ctx.send(default.traceback_maker(e))
                await ctx.message.add_reaction("\u274C")
                return
            await ctx.message.add_reaction("\u2705")
        if len(names) == 1:
            await ctx.send(
                f"Reloaded extension **{name}.py** {ctx.author.mention}",
                delete_after=delay,
            )
        else:
            await ctx.send(
                f"Reloaded the following extensions\n"
                + "\n".join(f"**{name}.py**" for name in names),
                delete_after=delay,
            )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def pull(self, ctx):
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        async with ctx.channel.typing():
            # this a real pain in the ass
            await asyncio.create_subprocess_shell("git pull")
            await ctx.send("Code has been pulled from github.", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def debug(self, ctx, *, arg):
        await ctx.invoke(self.bot.get_command("jsk debug"), command_string=arg)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def source(self, ctx, arg):
        await ctx.invoke(self.bot.get_command("jsk source"), command_name=arg)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def dm(self, ctx, user: discord.User, *, message):
        """DMs the user of your choice.
        If you somehow found out about this command, it is owner ONLY
        you cannot use it."""
        if user.bot:
            return await ctx.send(
                "I can't DM bots.\nI mean I can, I just don't want to..."
            )
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        embed2 = discord.Embed(title=f"New message to {user}", description=message)
        embed2.set_footer(
            text=f"tp!dm {user.id}",
            icon_url=ctx.author.avatar,
        )
        embed = discord.Embed(
            title=f"New message From {ctx.author.name}", description=message
        )
        embed.set_footer(
            text=f"To contact me, just DM the bot",
            icon_url=ctx.author.avatar,
        )
        try:
            await user.send(embed=embed)
            await ctx.send(embed=embed2)
        except discord.Forbidden:
            await ctx.send("This user might be having DMs blocked.", delete_after=delay)

    @commands.group(case_insensitive=True)
    @commands.check(permissions.is_owner)
    async def change(self, ctx):
        try:
            await ctx.message.delete(delete_after=delay)
        except:
            pass
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @change.command(name="username")
    @commands.check(permissions.is_owner)
    async def change_username(self, ctx, *, name: str):
        """Change username."""
        try:
            await ctx.message.delete()
        except:
            pass
        try:
            await self.bot.user.edit(username=name)
            await ctx.send(
                f"Successfully changed username to **{name}** {ctx.author.mention}. Lets hope I wasn't named something retarded",
                delete_after=delay,
            )
        except discord.HTTPException as err:
            await ctx.send(err)

    @change.command(name="nickname")
    @commands.check(permissions.is_owner)
    async def change_nickname(self, ctx, *, name: str = None):
        """Change nickname."""
        try:
            await ctx.message.delete()
        except:
            pass
        try:
            await ctx.guild.me.edit(nick=name)
            if name:
                await ctx.send(
                    f"Successfully changed nickname to **{name}**", delete_after=delay
                )
            else:
                await ctx.send("Successfully removed nickname", delete_after=delay)
        except Exception as err:
            await ctx.send(err)

    @change.command(name="avatar")
    @commands.check(permissions.is_owner)
    async def change_avatar_url(self, ctx, url: str = None):
        """Change avatar."""
        try:
            await ctx.message.delete()
        except:
            pass
        if url is None and len(ctx.message.attachments) == 1:
            url = ctx.message.attachments[0].url
        else:
            url = url.strip("<>") if url else None
        try:
            bio = await http.get(url, res_method="read")
            await self.bot.user.edit(avatar=bio)
            await ctx.send(
                f"Successfully changed the avatar. Currently using:\n{url}",
                delete_after=delay,
            )
        except aiohttp.InvalidURL:
            await ctx.send("The URL is invalid...", delete_after=delay)
        except discord.InvalidArgument:
            await ctx.send(
                "This URL does not contain a useable image", delete_after=delay
            )
        except discord.HTTPException as err:
            await ctx.send(err)
        except TypeError:
            await ctx.send(
                "You need to either provide an image URL or upload one with the command",
                delete_after=delay,
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))
