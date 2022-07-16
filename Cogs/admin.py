from __future__ import annotations

import asyncio
import concurrent
import datetime
import importlib
import io
import os
import re
import subprocess
import textwrap
import traceback
from contextlib import redirect_stdout, suppress
from subprocess import check_output
from typing import TYPE_CHECKING, Literal, Optional, Union

import aiohttp
import discord
import speedtest
from discord.ext import commands
from index import colors, config, delay, logger
from Manager.database import Connection
from Manager.logger import formatColor
from sentry_sdk import capture_exception
from utils import default, http, imports, permissions
from utils.default import log

from .Utils import random

# from utils.checks import InteractiveMenu

if TYPE_CHECKING:
    from index import Bot


class PersistentView(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(
        label="Report to Developers",
        style=discord.ButtonStyle.blurple,
        custom_id="AGBCustomID",
    )
    async def report(self, i: discord.Interaction, b: discord.ui.Button):
        guild = await i.client.fetch_guild(975810661709922334)
        bruh = await guild.fetch_channel(990187200656322601)
        # get the embeds image url
        await bruh.send(f"{i.message.embeds[0].image.url} reported by {i.user.id}")
        # disable the button once its been used
        b.disabled = True
        await i.response.edit_message(view=self)
        await i.followup.send(
            "Report sent successfully.\nIf the reported image follows our image report guidelines it will be removed shortly, if it does not, you will be getting a DM.",
            ephemeral=True,
        )


class InteractiveMenu(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=30)
        self.ctx = ctx

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.errors.NotFound:
            return

    @discord.ui.button(label="Report to Developers", style=discord.ButtonStyle.blurple)
    async def report(self, i, b: discord.ui.Button):
        guild = await i.client.fetch_guild(975810661709922334)
        bruh = await guild.fetch_channel(990187200656322601)
        # get the embeds image url
        await bruh.send(f"{i.message.embeds[0].image.url}")
        # disable the button once its been used
        await i.response.send_message("Report sent successfully", ephemeral=True)
        b.disabled = True
        await i.message.edit(view=self)

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.blurple)
    async def close(self, i, b: discord.ui.Button):
        await i.message.delete()

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message("Not your command", ephemeral=True)


class Admin(commands.Cog, name="admin", command_attrs=dict()):
    """Commands that arent for you lol"""

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.config = imports.get("config.json")
        os.environ.setdefault("JISHAKU_HIDE", "1")
        self._last_result = None
        self.last_change = None
        self.tax_rate = 0
        self.tax_collector = None
        self.lunar_headers = {
            f"{self.config.lunarapi.header}": f"{self.config.lunarapi.token}"
        }
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
        self.email_re = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
        self.blacklisted = False

        bot.add_check(self.blacklist_check)
        self.nword_re = r"\b(n|m|и|й){1,32}(i|1|l|!|ᴉ|¡){1,32}((g|ƃ|6|б{2,32}|q){1,32}|[gqgƃ6б]{2,32})(a|e|3|з|u)(r|Я|s|5|$){1,32}\b"
        self.nword_re_comp = re.compile(self.nword_re, re.IGNORECASE | re.UNICODE)
        self.afks = {}

        self.errors = (
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
            commands.BadBoolArgument,
        )

    async def blacklist_check(self, ctx: commands.Context):
        bl = self.bot.db.get_blacklist(
            ctx.author.id
        ) or await self.bot.db.fetch_blacklist(ctx.author.id, cache=True)
        return not bl.is_blacklisted if bl else True

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
            with suppress(Exception):
                await channel.send(msg)
                break

    async def add_fail_reaction(self):
        emoji = "\u2705"
        with suppress(Exception):
            await self.add_reaction(emoji)

    async def add_success_reaction(self):
        emoji = "\u2705"
        with suppress(Exception):
            await self.add_reaction(emoji)

    class MemberConverter(commands.MemberConverter):
        async def convert(self, ctx, argument):
            try:
                return await super().convert(ctx, argument)
            except commands.BadArgument as e:
                members = [
                    member
                    for member in ctx.guild.members
                    if member.display_name.lower().startswith(argument.lower())
                ]
                if len(members) == 1:
                    return members[0]
                else:
                    raise commands.BadArgument(
                        f"{len(members)} members found, please be more specific."
                    ) from e

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if self.nword_re_comp.search(guild.name.lower()):
            await self.try_to_send_msg_in_a_channel(
                guild, "im gonna leave cuz of the server name"
            )
            return await guild.leave()
        for channel in guild.channels:
            if self.nword_re_comp.search(guild.name.lower()):
                await self.try_to_send_msg_in_a_channel(
                    guild, f"im gonna leave cuz of the channel name {channel.mention}"
                )
                log(f"{guild.name} / {guild.id} is a racist server.")
                return await guild.leave()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member, guild=None):
        info = self.bot.get_channel(755722577049026562)
        info2 = self.bot.get_channel(776514195465568257)
        info3 = self.bot.get_channel(755722908122349599)
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
                await info.send(f"{member.mention}", delete_after=0)
                await info2.send(f"{member.mention}", delete_after=0)
                await info3.send(f"{member.mention}", delete_after=0)
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
            channel = self.bot.get_channel(755722577049026567)
            await channel.send(
                f"{member.name} left. Guild member count: {guild.member_count}",
                delete_after=5,
            )

    @commands.command(name="userfetch")
    @commands.check(permissions.is_owner)
    async def user_fetch(self, ctx):
        for user in self.bot.users:
            if user.bot:
                continue

            db_user = await self.bot.db.fetch_user(user.id)
            if not db_user:
                await self.bot.db.add_user(user.id)
                log(
                    f"{formatColor(user, 'green')} ({formatColor(str(user.id), 'gray')}) added to the database [{formatColor('users', 'gray')}]"
                )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def servers(self, ctx):
        """Lists all servers the bot is in and sends it to a text file"""
        filename = f"{ctx.guild.id}"
        with open(f"{str(filename)}.txt", "a", encoding="utf-8") as f:
            for guild in self.bot.guilds:
                data = f"{guild.id}: {guild}"
                f.write(data + "\n")
                continue
        try:
            await ctx.send(
                content="Sorry if this took a while to send, but here is all of the servers the bot is in!",
                file=discord.File(f"{str(filename)}.txt"),
            )
        except Exception as e:
            capture_exception(e)
            await ctx.send(
                "I couldn't send the file of this servers bans for whatever reason"
            )
        os.remove(f"{filename}.txt")

    @commands.command()
    @commands.check(permissions.is_owner)
    async def addstatus(self, ctx, *, status: str):
        """Add status to the bots status list

        Args:
            status (string, optional): The status to add

        Opts:
            {server_count} -> The amount of servers the bot is in
            {command_count} -> The amount of commands the bot has
            * Pass these as is in your string

        Ex:
            tp!addstatus Servers: {server_count} | Commands: {command_count}
        """

        row_count = len(self.bot.db._statuses)
        status = status.strip().replace("'", "")
        new_status = await self.bot.db.add_status(row_count, status)
        embed = discord.Embed(color=colors.prim)
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar,
        )
        embed.add_field(
            name="Status",
            value=f"Added status to db:\n```\n{new_status.status}```",
            inline=True,
        )
        embed.set_thumbnail(url=ctx.author.avatar)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def globalblacklist(self, ctx, user):
        id = user
        for guild in self.bot.guilds:
            user = await ctx.bot.fetch_user(id)
            try:
                user = await ctx.bot.fetch_user(id)
                try:
                    entry = await guild.fetch_ban(user)
                    log(f"{user.name} is already banned from {guild.name}")
                except discord.NotFound:
                    await guild.ban(user, reason="AGB Global Blacklist")
                    log(f"Banned {user.name} from {guild.name}")
            except discord.Forbidden:
                log(f"Could not ban {user.name} from {guild.name}")
        await asyncio.sleep(random.randint(0, 6))

    @commands.command(name="dbfetch")
    @commands.check(permissions.is_owner)
    async def db_fetch(self, ctx):
        """Fetch all users and guilds, and store them in the DB"""
        message = await ctx.send(
            "Fetching all servers and users, and adding them to the DB, please wait!"
        )
        log("Chunking servers, please be patient..")
        for guild in self.bot.guilds:
            if not guild.chunked:
                await guild.chunk()
                await asyncio.sleep(0.5)

            ### Server Table Check ###
            serverRows = await self.bot.db.fetch_guild(guild.id)
            if not serverRows:
                await self.bot.db.add_guild(guild.id)
                log(
                    f"{formatColor(ctx.guild.name, 'green')} ({formatColor(str(ctx.guild.id), 'gray')}) added to the database [{formatColor('servers', 'gray')}]"
                )

        for user in self.bot.users:
            if user.bot:
                continue

            ### User Table Check ###
            userRows = await self.bot.db.fetch_user(user.id)
            if not userRows:
                await self.bot.db.add_user(user.id)
                log(
                    f"{formatColor(user, 'green')} ({formatColor(str(user.id), 'gray')}) added to the database [{formatColor('users', 'gray')}]"
                )

            ### Economy Table Check ###
            economyRows = await self.bot.db.fetch_economy_user(user.id)
            if not economyRows:
                await self.bot.db.add_economy_user(user.id)
                log(
                    f"{formatColor(user, 'green')} ({formatColor(str(user.id), 'gray')}) added to the database [{formatColor('economy', 'gray')}]"
                )

            ### Blacklist Table Check ###
            blacklistRows = await self.bot.db.fetch_blacklist(str(user.id))
            if not blacklistRows:
                await self.bot.db.add_blacklist(str(user.id))
                log(
                    f"{formatColor(user, 'green')} ({formatColor(str(user.id), 'gray')}) added to the database [{formatColor('blacklist', 'gray')}]"
                )

        await message.edit(content="Done!")

    @commands.hybrid_command()
    @commands.check(permissions.is_owner)
    async def checkbanperm(self, ctx, member: discord.Member):
        # make a command to check if a user can be banned from a server
        # check if the bot has ban members permission
        await ctx.typing(ephemeral=True)
        try:
            if ctx.guild.me.guild_permissions.ban_members == True:
                # check the role hierarchy
                if ctx.guild.me.top_role > member.top_role:
                    return await ctx.author.send("I can ban this user!")
                if ctx.guild.me.top_role == member.top_role:
                    return await ctx.author.send(
                        "That user has the same role as me, i cant ban them"
                    )
                if ctx.guild.me.top_role < member.top_role:
                    await ctx.author.send(
                        "User has a higher role than me, I can't ban them! but i do have the permission to ban members"
                    )
            else:
                await ctx.author.send("I don't have the permission to ban members")

            await ctx.send("Check DMs", ephemeral=True)
        except Exception:
            await ctx.send("Something happened", ephemeral=True)

    @commands.command(name="chunk")
    @commands.check(permissions.is_owner)
    async def chunk_guilds(self, ctx):
        bruh = await ctx.send("Chunking guilds...")
        # chunk db because why not
        await self.bot.db.chunk(guilds=True)
        chunked_guilds = 0
        chunked = []

        # appends the current count of chunked guilds to a list then adds 1 to the chunked guilds count
        for guild in self.bot.guilds:
            if guild.chunked:
                chunked.append(guild)
                chunked_guilds += 1
        # takes the appended list and starts adding the newly chunked guilds to it
        async with ctx.channel.typing():
            for guild in self.bot.guilds:
                if not guild.chunked:
                    await guild.chunk()
                    chunked_guilds += 1
                    if chunked_guilds % random.randint(1, 15) == 0:
                        await bruh.edit(
                            content=f"Chunked {chunked_guilds}/{len(self.bot.guilds)} guilds"
                        )
                        await asyncio.sleep(random.randint(1, 3))

            log(
                f"Chunked {formatColor(str(chunked_guilds), 'green')} / {formatColor(str(len(self.bot.guilds)), 'green')} guilds"
            )
            await bruh.edit(
                content=f"Done chunking guilds! {chunked_guilds}/{len(self.bot.guilds)} guilds chunked!"
            )

    @commands.command(name="massnick")
    @commands.check(permissions.is_owner)
    async def massnick(self, ctx, *, nick: str):
        initial = await ctx.send("Mass nicking...")
        async with ctx.channel.typing():
            for member in ctx.guild.members:
                if not member.bot:
                    try:
                        await member.edit(nick=nick)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        capture_exception(e)
            await initial.edit(content="Done")

    @commands.command(aliases=["speedtest"])
    @commands.check(permissions.is_owner)
    async def netspeed(self, ctx):
        """Test the servers internet speed."""
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        speed_test = speedtest.Speedtest(secure=True)
        the_embed = await ctx.send(
            embed=self.generate_embed(0, speed_test.results.dict())
        )
        await loop.run_in_executor(executor, speed_test.get_servers)
        await loop.run_in_executor(executor, speed_test.get_best_server)
        await the_embed.edit(embed=self.generate_embed(1, speed_test.results.dict()))
        await loop.run_in_executor(executor, speed_test.download)
        await the_embed.edit(embed=self.generate_embed(2, speed_test.results.dict()))
        await loop.run_in_executor(executor, speed_test.upload)
        await the_embed.edit(embed=self.generate_embed(3, speed_test.results.dict()))

    @staticmethod
    def generate_embed(step: int, results_dict):
        """Generate the embed."""
        measuring = ":mag: Measuring..."
        waiting = ":hourglass: Waiting..."

        color = discord.Color.red()
        title = "Measuring internet speed..."
        message_ping = measuring
        message_down = waiting
        message_up = waiting
        if step > 0:
            message_ping = f"**{results_dict['ping']}** ms"
            message_down = measuring
        if step > 1:
            message_down = f"**{results_dict['download'] / 1_000_000:.2f}** mbps"
            message_up = measuring
        if step > 2:
            message_up = f"**{results_dict['upload'] / 1_000_000:.2f}** mbps"
            title = "NetSpeed Results"
            color = discord.Color.green()
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Ping", value=message_ping)
        embed.add_field(name="Download", value=message_down)
        embed.add_field(name="Upload", value=message_up)
        return embed

    @commands.command(
        name="sqlt",
    )
    @commands.check(permissions.is_owner)
    async def sqlt(self, ctx, *, query: str):
        data = await self.bot.db.execute(f"{query}RETURNING *")
        await ctx.send(data)

    @commands.command(
        name="blacklist",
        invoke_without_command=True,
        pass_context=True,
    )
    @commands.check(permissions.is_owner)
    async def blacklist(self, ctx, user: Optional[discord.User] = None, *, list=None):
        """Blacklist users from using the bot. Pass no args to see a list of blacklisted users"""
        if user is None:
            blist = [
                key
                for key, value in self.bot.db._blacklists.items()
                if value.is_blacklisted
            ]
            conv = commands.UserConverter()
            users = await asyncio.gather(
                *[conv.convert(ctx, str(_id)) for _id in blist]
            )
            join_users = "\n".join(f"{str(user)} ({user.id})" for user in users)
            users = join_users if users else "No one has been blacklisted"
            await ctx.send(f"Blacklisted users: {users}")
            return

        user_blacklist = self.bot.db._blacklists.get(user.id)
        if not user_blacklist or user_blacklist.is_blacklisted is False:
            if not user_blacklist:
                await self.bot.db.add_blacklist(user.id, blacklisted=True)
            else:
                await user_blacklist.modify(blacklisted=True)

            await ctx.send(f"{user} has been added to the blacklist.", delete_after=5)
            await self.add_success_reaction()
            try:
                await user.send(
                    (
                        "You have been blacklisted from using the bot.\n\n"
                        "This blacklist is permenant unless you can email us a good reason "
                        "why you should be whitelisted - `contact@lunardev.group`"
                    )
                )
            except Exception as e:
                capture_exception(e)
                await ctx.send(
                    "I was unable to DM them, they may have DMs disabled, however they will still be blacklisted.",
                    delete_after=10,
                )
            return
        elif user_blacklist.is_blacklisted is True:
            await user_blacklist.modify(blacklisted=False)
            await ctx.send(
                f"{user} has been removed from the blacklist.", delete_after=5
            )
            await self.add_success_reaction()
            try:
                await user.send(
                    "Good job, you've been whitelisted. You can now use this bot."
                )
            except Exception as e:
                capture_exception(e)
                await ctx.send(
                    "I couldn't DM the user, they may have DMs disabled, however they can still use the bot.",
                    delete_after=10,
                )

    @commands.group(
        aliases=["eco"],
    )
    @commands.check(permissions.is_owner)
    async def economy(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please use a subcommand. (eco)")

    @economy.command(
        aliases=["give"],
    )
    @commands.check(permissions.is_owner)
    async def add(
        self,
        ctx: commands.Context,
        amount: int,
        user: Optional[Union[discord.User, discord.Member]] = None,
        account: Literal["bank", "wallet", "balance"] = "bank",
    ):
        if amount == 0:
            await ctx.send("Please enter a non-zero amount.")
            return
        elif amount < 0:
            await ctx.send(f"Please use tp!eco remove {abs(amount)}")
            return

        user = user or ctx.author
        account = account
        if account == "balance":
            account = "wallet"

        # Fetch user's banking information
        economy_user = self.bot.db.get_economy_user(user.id)
        if not economy_user:
            await ctx.send("User has no economy account.")
            return

        account_to_change = getattr(economy_user, account)
        final_amount = account_to_change + amount
        await economy_user.modify(**{account: final_amount})
        await ctx.send(
            f"Gave ${amount} to {str(user)}, their {account} is now at ${final_amount}"
        )

    @economy.command(
        aliases=["take"],
    )
    @commands.check(permissions.is_owner)
    async def remove(
        self,
        ctx: commands.Context,
        amount: int,
        user: Optional[Union[discord.User, discord.Member]] = None,
        account: Literal["bank", "wallet", "balance"] = "bank",
    ):
        if amount == 0:
            await ctx.send("Please enter a non-zero amount.")
            return
        elif amount < 0:
            await ctx.send(f"Please use tp!eco remove {abs(amount)}")
            return

        user = user or ctx.author
        account = account
        if account == "balance":
            account = "wallet"

        # Fetch user's banking information
        economy_user = self.bot.db.get_economy_user(user.id)
        if not economy_user:
            await ctx.send("User has no economy account.")
            return

        account_to_change = getattr(economy_user, account)

        final_balance = account_to_change - amount
        if final_balance < 0:
            await ctx.send(
                f"This would cause the user's balance to be a negative number.\nYou may take a max of ${account_to_change}."
            )
            return

        await economy_user.modify(**{account: final_balance})
        await ctx.send(
            f"Took ${amount} from {str(user)}, their {account} is now at ${account_to_change + amount}"
        )

    @economy.command()
    @commands.check(permissions.is_owner)
    async def set(
        self,
        ctx: commands.Context,
        amount: int,
        user: Optional[Union[discord.User, discord.Member]] = None,
        account: Literal["bank", "wallet", "balance"] = "bank",
    ):
        user = user or ctx.author
        if amount == 0:
            await ctx.send(f"Please use `tp!eco reset {user.id} {account}`")
            return
        elif amount < 0:
            await ctx.send("Please enter a positive, non-zero number.")
            return

        account = account
        if account == "balance":
            account = "wallet"

        # Fetch user's banking information
        economy_user = self.bot.db.get_economy_user(user.id)
        if not economy_user:
            await ctx.send("User has no economy account.")
            return

        account_to_change = getattr(economy_user, account)

        await economy_user.modify(**{account_to_change: amount})
        await ctx.send(f"Set {account} to ${amount} for {str(user)}")

    @economy.command(
        aliases=["clear", "wipe"],
    )
    @commands.check(permissions.is_owner)
    async def reset(
        self,
        ctx: commands.Context,
        user: Optional[Union[discord.User, discord.Member]] = None,
        account: Literal["bank", "wallet", "balance", "both"] = "both",
    ):
        user = user or ctx.author
        account = account
        if account == "balance":
            account = "wallet"

        def check(m):
            return (
                m.channel == ctx.channel
                and m.author == ctx.author
                and m.content in self.yes_responses
            )

        # Fetch user's banking information
        economy_user = self.bot.db.get_economy_user(user.id)
        if not economy_user:
            await ctx.send("User has no economy account.")
            return

        await ctx.send(
            f"Are you sure you want to erase {str(user)}'s {account}?\n**This action cannot be undone.**"
        )
        try:
            response = await self.bot.wait_for("message", check=check, timeout=15)
        except asyncio.TimeoutError:
            await ctx.send("Canceled.")
            return
        else:
            if not self.yes_responses[response.content]:
                await ctx.send("Canceled")
                return

        to_reset = {}
        if account == "bank":
            to_reset["bank"] = 0
        elif account == "wallet":
            to_reset["wallet"] = 0
        else:
            to_reset["bank"] = 0
            to_reset["wallet"] = 0

        await economy_user.modify(**to_reset)
        await ctx.send(f"Cleared {account} for {str(user)}")

    @economy.error
    async def economy_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.BadLiteralArgument):
            await ctx.send(
                "You can only set/give/take to either the `bank` or `wallet`."
            )
            return

        # might not work
        return await self.bot.on_command_error(ctx, error)

    @economy.group(
        pass_context=True,
    )
    @commands.check(permissions.is_owner)
    async def setting(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please use a subcommand. (set)")

    @setting.command(
        aliases=["tax", "change_tax"],
    )
    @commands.check(permissions.is_owner)
    async def set_tax(self, ctx, new_tax: float):
        """Set a tax rate - Must be a decimal, such that `12%` would be `0.12`"""
        global_var = self.bot.db.get_global_var("taxData")
        if not global_var:
            global_var = await self.bot.db.add_global_var("taxData", new_tax)

        await ctx.send(f"Tax rate changed to {int(global_var.variableData * 100)}%.")

    @setting.command(
        aliases=["collector", "bastard"],
    )
    @commands.check(permissions.is_owner)
    async def set_collector(
        self, ctx, user: Optional[Union[discord.User, discord.Member]] = None
    ):
        """Sets everyone's least favorite person in the world."""
        global_var = self.bot.db.get_global_var("taxData")
        if not global_var:
            # ?
            global_var = await self.bot.db.add_global_var("taxData", 0, "None")

        user = user.id if user else None  # type: ignore

        global_var = await global_var.modify(variableData2=user)
        if not global_var.variableData2:
            await ctx.send(
                "Tax collector cleared. User might still be taxed, but no one will collect it."
            )

            return

        await ctx.send(
            f"Tax collector set to {str(user)} (ID: {global_var.variableData2})"
        )

    @commands.check(permissions.is_owner)
    @commands.hybrid_command()
    async def eval(self, ctx, *, body: str):
        """Evaluates a code"""
        await ctx.typing(ephemeral=True)

        async def filter_eval(search: str, to_filter: str):
            if to_filter in search:
                return search.replace(to_filter, "[REDACTED]")
            else:
                return search

        env = {
            "self": self.bot,
            "bot": self.bot,
            "db": self.bot.db,
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
            colour=colors.prim,
        )

        try:
            exec(to_compile, env)
        except Exception as e:
            capture_exception(e)
            await self.add_fail_reaction()
            embed.add_field(
                name="Error",
                value=f"```py\n{e.__class__.__name__}: {e}\n```",
                inline=True,
            )
            try:
                await ctx.send(embed=embed, ephemeral=True)
            except Exception:
                await ctx.send("Done and returned no output.")
            return

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            _value_p1 = await filter_eval(stdout.getvalue(), config.token)
            value = await filter_eval(_value_p1, config.lunarapi.token)
            embed.add_field(
                name="Output",
                value=f"```py\n{value}{traceback.format_exc()}\n```",
                inline=True,
            )
            try:
                await ctx.send(embed=embed, ephemeral=True)
            except Exception:
                await ctx.send("Done and returned no output.")

        else:
            _value_p1 = await filter_eval(stdout.getvalue(), config.token)
            value = await filter_eval(_value_p1, config.lunarapi.token)
            await self.add_success_reaction()
            if ret is None:
                if value:
                    embed.add_field(
                        name="Result", value=f"```py\n{value}\n```", inline=True
                    )
                    try:
                        await ctx.send(embed=embed, ephemeral=True)
                    except Exception:
                        await ctx.send("Done and returned no output.")
            else:
                self._last_result = ret
                embed.add_field(
                    name="Result", value=f"```py\n{value}{ret}\n```", inline=True
                )
                try:
                    await ctx.send(embed=embed, ephemeral=True)
                except Exception:
                    await ctx.send("Done and returned no output.")

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
                            content=f"We're in {channel.name} now, we've gathered {len(channel_messages)} messages"
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
        most_messages_users = [
            user for user, value in speaker_count.items() if value == most_messages
        ]

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
        channel_list = "".join(
            f"{channel.mention}\n" for channel in ctx.guild.text_channels
        )

        await ctx.send(f"Here are the channels I can see:\n{channel_list}")

    @commands.command()
    async def owner(self, ctx):
        """Did you code me?"""
        async with ctx.channel.typing():
            with suppress(discord.NotFound):
                await ctx.message.delete()
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

        for name in names:
            try:
                await self.bot.load_extension(f"Cogs.{name}")
            except Exception as e:
                capture_exception(e)
                await ctx.send(default.traceback_maker(e))
                await self.add_fail_reaction()
                return
            await self.add_success_reaction()
            await ctx.send(f"Loaded extension **{name}.py**", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def sync(self, ctx):
        arg = ctx.guild.id
        await ctx.invoke(self.bot.get_command("jsk sync"), command_string=arg)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def unload(self, ctx, *names):
        """Unloads an extension."""

        for name in names:
            try:
                await self.bot.unload_extension(f"Cogs.{name}")
            except Exception as e:
                capture_exception(e)
                return await ctx.send(default.traceback_maker(e))
            await ctx.send(
                f"Unloaded extension **{name}.py** {ctx.author.mention}",
                delete_after=delay,
            )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reload(self, ctx, *names):
        """Reloads an extension."""

        for name in names:
            try:
                await self.bot.reload_extension(f"Cogs.{name}")
            except Exception as e:
                capture_exception(e)
                await ctx.send(default.traceback_maker(e))
                await self.add_fail_reaction()
                return
            await self.add_success_reaction()
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

        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    await self.bot.load_extension(
                        f"Cogs.{name}",
                    )
                except Exception as e:
                    capture_exception(e)
                    error_collection.append(
                        [file, default.traceback_maker(e, advance=False)]
                    )
        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            await self.add_fail_reaction()
            return await ctx.send(
                f"Attempted to load all extensions, was able to but... "
                f"the following failed...\n\n{output}"
            )
        await self.add_success_reaction()
        await ctx.send(
            f"Successfully loaded all extensions {ctx.author.mention}",
            delete_after=delay,
        )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadall(self, ctx):
        """Reloads all extensions."""

        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    await self.bot.reload_extension(
                        f"Cogs.{name}",
                    )
                except Exception as e:
                    capture_exception(e)
                    error_collection.append(
                        [file, default.traceback_maker(e, advance=False)]
                    )
        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            await self.add_fail_reaction()
            return await ctx.send(
                f"Attempted to reload all extensions, was able to reload, "
                f"however the following failed...\n\n{output}"
            )
        await self.add_success_reaction()
        await ctx.send(
            f"Successfully reloaded all extensions {ctx.author.mention}",
            delete_after=delay,
        )

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadutils(self, ctx, *names):
        """Reloads a utils module."""

        for name in names:
            try:
                module_name = importlib.import_module(f"utils.{name}")
                importlib.reload(module_name)
            except Exception as e:
                capture_exception(e)
                await ctx.send(default.traceback_maker(e))
                await self.add_fail_reaction()
                return
            await self.add_success_reaction()
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

    # make a command to pull updates from git
    @commands.command()
    @commands.check(permissions.is_owner)
    async def pull(self, ctx):
        """Pulls the latest updates from git."""

        with suppress(Exception):
            bruh = await ctx.send("Pulling updates...")
            await asyncio.create_subprocess_shell("git pull")
        # get the output of the subprocess, get the github stats of the commit
        output = subprocess.check_output(["git", "log", "-1"]).decode("utf-8")
        # get total deletions
        deletions = subprocess.check_output(["git", "diff", "--shortstat"]).decode(
            "utf-8"
        )
        # get total additions
        additions = subprocess.check_output(
            ["git", "diff", "--shortstat", "--cached"]
        ).decode("utf-8")
        # check if its already up to date
        if "Already up to date." in output:
            await bruh.edit("Already up-to-date.")  # this doesnt even work lol
            return
        await bruh.edit(
            content=f"Updates Pulled:\n{output}\n\n{deletions}\n{additions}"
        )

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
    async def restart(self, ctx):
        await ctx.send("Restarting all services...")
        os.system("cd ../ && ./restart.sh")

    @commands.command()
    @commands.check(permissions.is_owner)
    async def crash_debug(self, ctx):
        # cause divide by zero error
        await ctx.send("Crashing the bot for debug puroposes...")

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
        with suppress(Exception):
            await ctx.message.delete()
        embed2 = discord.Embed(title=f"New message to {user}", description=message)
        embed2.set_footer(
            text=f"tp!dm {user.id}",
            icon_url=ctx.author.avatar,
        )
        embed = discord.Embed(
            title=f"New message From {ctx.author.name} | {self.bot.user.name} DEV",
            description=message,
        )
        embed.set_footer(
            text="To contact me, just DM the bot", icon_url=ctx.author.avatar
        )

        # check if the command was ran in the log channel
        log_dm = self.bot.get_channel(986079167944749057)
        if ctx.channel.id == log_dm.id:
            try:
                await user.send(embed=embed)
                await log_dm.send(embed=embed2)
            except Exception:
                await ctx.send("Cannot DM user.")
                return
        else:
            try:
                await user.send(embed=embed)
                await log_dm.send(embed=embed2)
            except Exception:
                await ctx.send("Cannot dm user.")

    @commands.group(case_insensitive=True)
    @commands.check(permissions.is_owner)
    async def change(self, ctx):

        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @change.command(name="username")
    @commands.check(permissions.is_owner)
    async def change_username(self, ctx, *, name: str):
        """Change username."""
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
            await ctx.guild.me.edit(nick=name)
            if name:
                await ctx.send(
                    f"Successfully changed nickname to **{name}**", delete_after=delay
                )
            else:
                await ctx.send("Successfully removed nickname", delete_after=delay)
        except Exception as err:
            capture_exception(err)
            await ctx.send(err)

    @change.command(name="avatar")
    @commands.check(permissions.is_owner)
    async def change_avatar_url(self, ctx, url: str = None):
        """Change avatar."""
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


async def setup(bot: Bot) -> None:
    await bot.add_cog(Admin(bot))
