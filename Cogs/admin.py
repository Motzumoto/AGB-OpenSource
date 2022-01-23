import nekos
import asyncio
import concurrent
import importlib
import io
import json
import os
import re
import subprocess
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import Union

import aiohttp
import discord
from datetime import datetime

from psycopg import cursor
import requests
import speedtest
from discord.ext import commands
from discord.ext.buttons import Paginator
from index import EMBED_COLOUR, cursor_n, delay, logger, mydb_n
from Manager.logger import formatColor
from Manager.commandManager import cmd
from utils import default, http, permissions

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

    class Pag(Paginator):
        async def teardown(self):
            try:
                await self.page.clear_reactions()
            except discord.HTTPException:
                pass

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
                await me.send(
                    f"A bot was just added to Lunar Development... {member.bot.name} / {member.bot.mention}"
                )
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
        me = self.bot.get_user(101118549958877184)
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
            await ctx.reply("Please use a subcommand. (eco)")

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
            await ctx.reply("Please enter a non-zero amount.")
            return
        elif amount < 0:
            await ctx.reply(f"Please use tp!eco remove {abs(amount)}")
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
            await ctx.reply("You can only give to either the `bank` or `wallet`.")
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
        await ctx.reply(
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
            await ctx.reply("Please enter a non-zero amount.")
            return
        elif amount < 0:
            await ctx.reply(f"Please use tp!eco add {abs(amount)}")
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
            await ctx.reply("You can only take from either the `bank` or `wallet`.")
            return

        final_balance = account_to_change - amount
        if final_balance < 0:
            await ctx.reply(
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
        await ctx.reply(
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
            await ctx.reply(f"Please use `tp!eco reset {user.id} {account}`")
            return
        elif amount < 0:
            await ctx.reply(f"Please enter a positive, non-zero number.")
            return

        if account == "bank":
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '{amount}' WHERE userid = '{user.id}'"
            )
            await ctx.reply(f"Set bank to ${amount} for {str(user)}.")
        elif account == "wallet" or account == "balance":
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '{amount}' WHERE userid = '{user.id}'"
            )
            await ctx.reply(f"Set wallet to ${amount} for {str(user)}.")
        else:
            await ctx.reply("Please choose either `bank` or `wallet`.")

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

        await ctx.reply(
            f"Are you sure you want to erase {str(user)}'s {to_erase}?\n**This action cannot be undone.**"
        )
        try:
            response = await self.bot.wait_for("message", check=check, timeout=15)
        except asyncio.TimeoutError:
            await ctx.reply("Canceled.")
            return
        if not self.yes_responses[response.content]:
            ctx.reply("Canceled")
            return

        if account == "both" or account == "bank":
            cursor_n.execute(
                f"UPDATE public.usereco SET bank = '0' WHERE userid = '{user.id}'"
            )
        if account == "both" or account == "wallet" or account == "balance":
            cursor_n.execute(
                f"UPDATE public.usereco SET balance = '0' WHERE userid = '{user.id}'"
            )
        await ctx.reply(f"Cleared {to_erase} for {str(user)}")

    @economy.group(pass_context=True, hidden=True)
    @commands.check(permissions.is_owner)
    async def setting(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please use a subcommand. (set)")

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
        await ctx.reply(f"Tax rate changed to {int(row[0][1] * 100)}%.")

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
            await ctx.reply(
                f"Tax collector cleared. User might still be taxed, but no one will collect it."
            )
        else:
            await ctx.reply(f"Tax collector set to {str(user)} (ID: {row[0][2]})")

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
        except Exception as e:
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
    @commands.command(hidden=True)
    async def ghost(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound:
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
            await ctx.message.delete(delay=delay)
        except:
            pass
        for name in names:
            try:
                self.bot.load_extension(f"Cogs.{name}")
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
            await ctx.message.delete(delay=delay)
        except:
            pass
        for name in names:
            try:
                self.bot.unload_extension(f"Cogs.{name}")
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
            await ctx.message.delete(delay=delay)
        except:
            pass
        for name in names:
            try:
                self.bot.reload_extension(f"Cogs.{name}")
            except Exception as e:
                await ctx.send(default.traceback_maker(e))
                await ctx.message.add_reaction("\u274C")
                return
            await ctx.message.add_reaction("\u2705")
            await ctx.send(
                f"Reloaded extension **{name}.py** {ctx.author.mention}",
                delete_after=delay,
            )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def loadall(self, ctx):
        """Loads all extensions"""
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    self.bot.load_extension(
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
            await ctx.message.delete(delay=delay)
        except:
            pass
        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    self.bot.reload_extension(
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
    async def reloadutils(self, ctx, name: str):
        """Reloads a utils module."""
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        name_maker = f"utils/{name}.py"
        try:
            module_name = importlib.import_module(f"utils.{name}")
            importlib.reload(module_name)
        except ModuleNotFoundError:
            return await ctx.send(f"Couldn't find module named **{name_maker}**")
        except Exception as e:
            error = default.traceback_maker(e)
            return await ctx.send(
                f"Module **{name_maker}** returned error and was not reloaded...\n{error}"
            )
        await ctx.send(f"Reloaded module **{name_maker}**")

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reboot(self, ctx):
        """Reboot the bot"""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.bot.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(
                type=discord.ActivityType.playing, name="Restarting..."
            ),
        )
        embed = discord.Embed(
            title="Cya, lmao.", color=EMBED_COLOUR, description="Rebooting... 👌"
        )
        await ctx.send(embed=embed)
        await os.system("chmod +x * && ./reboot.sh")

    @commands.command()
    @commands.check(permissions.is_owner)
    async def shutdown(self, ctx):
        """completely shut the bot down"""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.playing, name="Shutting down..."
            ),
        )
        embed = discord.Embed(
            title="Cya, lmao.", color=EMBED_COLOUR, description="Shutting Down...👌"
        )
        await ctx.send(embed=embed)
        url = "https://panel.ponbus.com/api/client/servers/1acee413/power"

        payload_kill = json.dumps({"signal": "kill"})
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{self.config.ponbus}",
        }

        response2 = requests.request("POST", url, headers=headers, data=payload_kill)
        print(response2.text)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def pull(self, ctx):
        try:
            await ctx.message.delete(delay=delay)
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
            await ctx.message.delete(delay=delay)
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
        except discord.NotFound:
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
        except discord.NotFound:
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
        except discord.NotFound:
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

    @commands.check(permissions.is_owner)
    @commands.command()
    async def ownersay(self, ctx, *, message):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await ctx.send(message)

    @commands.Cog.listener(name="on_message")
    async def linkblacklist(self, message):
        if message.guild is None:
            return
        me = self.bot.get_user(101118549958877184)
        blacklisted_links = [
            "cehfhc.dateshookp.com",
            "streancommunnity.",
            "steancomunnity.",
            "steancomunlty.",
            "stearncomminuty.",
            "steamcommunytu.",
            "steamconmmuntiy.",
            "steamcomminytu.",
            "steamcommutiny.",
            "streancommunnity.",
            "steancomunnity.",
            "steancomunlty.",
            "stearncomminuty.",
            "steamcommunytu.",
            "steamconmmuntiy.",
            "steamcomminytu.",
            "bit.ly/Discord--Nitro-Generator",
            "store-steampowered.",
            "steamnconnmunity.",
            "discordgivenitro.",
            "freenitros.",
            "freenitros.",
            "discordgift.",
            "discordgift.",
            "discordgift.",
            "steamcomminuty.",
            "discord.giveawey.",
        ]

        if any(elem in message.content for elem in blacklisted_links):
            await me.send(
                f"**New Scammer**\n**{message.guild.id}** | **{message.guild.name}**\n{message.author.id}\n`{message.content}`\n"
            )
            try:
                await message.delete()
            except:
                pass


def setup(bot):
    bot.add_cog(Admin(bot))
