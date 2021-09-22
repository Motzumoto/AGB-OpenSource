import argparse
import asyncio
import json
import os
import random
import re
import time
from collections import Counter
from typing import Union

import discord
from discord.ext import commands
from index import EMBED_COLOUR, Website, config, cursor, delay, mydb
from utils import checks, default, permissions, time


def can_execute_action(ctx, user, target):
    return (
        user.id == ctx.bot.owner_id
        or user == ctx.guild.owner
        or user.top_role > target.top_role
    )


class MemberNotFound(Exception):
    pass


# edited from RoboDanny (i had a plan to use this but i just dont remember for what)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


# URL_REG = re.compile(r'https?://(?:www\.)?.+')


async def resolve_member(guild, member_id):
    member = guild.get_member(member_id)
    if member is None:
        if guild.chunked:
            raise MemberNotFound()
        try:
            member = await guild.fetch_member(member_id)
        except discord.NotFound:
            raise MemberNotFound() from None
    return member


# Edited from robo danny


class MemberID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
                m = await resolve_member(ctx.guild, member_id)
            except ValueError:
                raise commands.BadArgument(
                    f"{argument} is not a valid member or member ID."
                ) from None
            except MemberNotFound:
                # hackban case
                return type(
                    "_Hackban",
                    (),
                    {"id": member_id, "__str__": lambda s: f"Member ID {s.id}"},
                )()

        if not can_execute_action(ctx, ctx.author, m):
            raise commands.BadArgument(
                "You cannot do this action on this user due to role hierarchy."
            )
        return m


# class taken from robo danny. Hackbanning is really nice


class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument(
                    "This member has not been banned before."
                ) from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument("This member has not been banned before.")
        return entity


# edited from robo danny


class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f"{ctx.author} (ID: {ctx.author.id}): {argument}"

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(
                f"Reason is too long ({len(argument)}/{reason_max})"
            )
        return ret


def safe_reason_append(base, to_append):
    appended = base + f"({to_append})"
    if len(appended) > 512:
        return base
    return appended


# i also had a plan to use this but i dont remember for what


class CooldownByContent(commands.CooldownMapping):
    def _bucket_key(self, message):
        return (message.channel.id, message.content)


class NoMuteRole(commands.CommandError):
    def __init__(self):
        super().__init__("This server does not have a mute role set up.")


def can_mute():
    async def predicate(ctx):
        is_owner = await ctx.bot.is_owner(ctx.author)
        if ctx.guild is None:
            return False

        if not ctx.author.guild_permissions.manage_roles and not is_owner:
            return False

        # This will only be used within this cog.
        ctx.guild_config = config = await ctx.cog.get_guild_config(ctx.guild.id)
        role = config and config.mute_role
        if role is None:
            raise NoMuteRole()
        return ctx.author.top_role > role

    return commands.check(predicate)


class Moderator(commands.Cog, name="mod"):
    """Commands for moderators to keep your server safe"""

    def __init__(self, bot):
        self.bot = bot
        self.last_messages = {}
        self.config = default.get("config.json")
        # with open('prefixes.json') as f:
        #     self.prefixes = json.load(f)
        # cursor.execute(f"SELECT * FROM guilds WHERE guildId = {ctx.guild.id}")
        # r = cursor.fetchall()
        # for row in r:
        #     self.prefixes = row[2]
        try:
            self.bot.command_prefix = self.get_prefix
        except:
            pass
        self.default_prefix = "tp!"
        cursor.execute(f"SELECT userId FROM users WHERE blacklisted = 'true'")
        res = cursor.fetchall()
        blist = []
        for row in res:
            blist.append(int(row[0]))
        self.blacklist = blist

        # with open('blacklist.json') as f:
        #     self.blacklist = json.load(f)

    def get_prefix(self, bot, message):
        try:
            cursor.execute(
                f"SELECT prefix FROM guilds WHERE guildId = {message.guild.id}"
            )
        except:
            pass
        for row in cursor.fetchall():
            self.prefixes = row[0]
        prefix = (
            self.prefixes if getattr(message, "guild", None) else self.default_prefix
        )
        mydb.commit()
        return commands.when_mentioned_or(prefix)(bot, message)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            if message.author == self.bot.user:
                return
            if message.author.id in self.blacklist:
                return
            # if message.author.id in self.config.owners:
            #     return
            if message.author.id != self.bot.user:
                if message.content.startswith("tp!"):
                    return
                embed = discord.Embed(colour=EMBED_COLOUR)
                embed.add_field(
                    name=f"DM - From {message.author} ({message.author.id})",
                    value=f"{message.content}",
                )
                embed.set_footer(
                    text=f"tp!dm {message.author.id} ",
                    icon_url=message.author.avatar_url,
                )
                channel = self.bot.get_channel(758459079059701800)
                files = []
                for attachment in message.attachments:
                    files.append(await attachment.to_file())
                if len(files) > 0:
                    await channel.send(
                        content=f"File - from {message.author} ({message.author.id})",
                        files=files,
                    )
                try:
                    await channel.send(embed=embed)
                except:
                    pass

    @commands.command(aliases=["enabler", "ron"], usage="`tp!ron`")
    @permissions.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True, manage_guild=True)
    async def raid_on(self, ctx):
        """Enables basic raid mode for your server
        This enables extreme raid prevention, everyone is then required to have a verified phone to be able to talk in your server.
        """
        try:
            await ctx.guild.edit(verification_level=discord.VerificationLevel.extreme)
        except discord.HTTPException:
            await ctx.send("\N{WARNING SIGN} Could not set verification level.")
            return

        await ctx.send(
            f"Raid mode enabled. People are now required to have a verified email and phone connected to their account to be able to talk here."
        )

    @commands.command(aliases=["disabler", "roff"], usage="`tp!roff`")
    @permissions.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True, manage_guild=True)
    async def raid_off(self, ctx):
        """Disables raid mode on the server.
        When disabled, the server verification levels are set
        back to Low levels."""
        try:
            await ctx.guild.edit(verification_level=discord.VerificationLevel.low)
        except discord.HTTPException:
            await ctx.send("\N{WARNING SIGN} Could not set verification level.")
            return

        await ctx.send("Raid mode disabled.")

    async def _basic_cleanup_strategy(self, ctx, search):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me:
                await asyncio.sleep(0.10)
                await msg.delete()
                count += 1
        return {"Bot": count}

        # async def _complex_cleanup_strategy(self, ctx, search):
        #    prefixes = self.config.prefix # thanks startswith

        def check(m):
            return m.author == ctx.me or m.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    @commands.command(usage="`tp!cleanup`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @permissions.has_permissions(manage_messages=True)
    async def cleanup(self, ctx, search=300):
        """Cleans up the bot's messages from the channel.
        If a search number is specified, it searches that many messages to delete.
        If the bot has Manage Messages permissions then it will try to delete
        messages that look like they invoked the bot as well.
        After the cleanup is completed, the bot will send you a message with
        which people got their messages deleted and their count. This is useful
        to see which users are spammers.
        You must have Manage Messages permission to use this.
        """
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        strategy = self._basic_cleanup_strategy
        # if ctx.me.permissions_in(ctx.channel).manage_messages:
        #    strategy = self._complex_cleanup_strategy

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"- **{author}**: {count}" for author, count in spammers)

        await ctx.send("\n".join(messages), delete_after=delay)

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    @commands.bot_has_permissions(embed_links=True, kick_members=True)
    @commands.command(usage="`tp!kick <user>`", ignore_extra=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kicks a user from the current server."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if await permissions.check_priv(ctx, member):
            return
        await member.kick(reason=default.responsible(ctx.author, reason))
        await ctx.send(default.actionmessage("kicked"))

    @commands.command(usage="`tp!setprefix <newprefix>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_channels=True)
    async def setprefix(self, ctx, new=None):
        """Set a custom prefix for the server"""
        no_prefix = discord.Embed(
            title="Please put a prefix you want.", colour=EMBED_COLOUR
        )
        if not new:
            return await ctx.send(embed=no_prefix)
        else:
            pass
        if len(new) > 3:
            await ctx.send("I don't accept prefixes over 3 characters.")
            return
        else:
            # self.prefixes[str(ctx.guild.id)] = new
            # with open('prefixes.json', 'w') as f:
            #     json.dump(self.prefixes, f, indent=4)
            new_prefix = discord.Embed(
                description=f"The new prefix is `{new}`",
                color=EMBED_COLOUR,
                timestamp=ctx.message.created_at,
            )
            await ctx.send(embed=new_prefix)
            try:
                await ctx.guild.me.edit(nick=f"[{new}] {self.bot.user.name}")
                cursor.execute(
                    f"UPDATE guilds SET prefix = '{new}' WHERE guildID = {ctx.guild.id}"
                )
                mydb.commit()
            except discord.Forbidden:
                await ctx.send(
                    "I couldn't update my nickname, the prefix has changed though."
                )

    @commands.command(usage="`tp!prefix`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix(self, ctx):
        """If you don't know what the servers current prefix is, you can check with this command"""
        # with open("prefixes.json") as f:
        #     prefixes = json.load(f)

        #     if prefixes == None:
        #         return await ctx.send("There isnt a custom prefix for this server. The default prefix is `tp!`")
        #     else:
        #         pass
        try:
            cursor.execute(f"SELECT * FROM guilds WHERE guildId = {ctx.guild.id}")
        except:
            pass
        result = cursor.fetchall()
        for row in result:
            # prefixes[str(ctx.guild.id)]
            embed = discord.Embed(
                title=f"AGB",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                timestamp=ctx.message.created_at,
            )
            embed.add_field(name="Prefix for this server:", value=f"{row[2]}")
            embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.command(aliases=["ar"], usage="`tp!ar <user> <role>`")
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def addrole(self, ctx, user: discord.Member, *, role: discord.Role):
        """Adds a role to a user"""
        await user.add_roles(role)
        await ctx.send(f"Aight, gave {role.name} to {user.mention}")

    # make a delete role command
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.command(aliases=["dr"], usage="`tp!dr <role>`")
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def delrole(self, ctx, *, role: discord.Role):
        """Delete a role in the server"""
        await role.delete()
        await ctx.send(f"Aight, deleted {role.name}")

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.command(aliases=["rr"], usage="`tp!rr <user> <role>`")
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    async def removerole(self, ctx, user: discord.Member, *, role: discord.Role):
        """Removes a role from a user"""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await user.remove_roles(role)
        await ctx.send(f"Aight, removed {role.name} from {user.mention}")

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.command(usage="`tp!perms`")
    @commands.guild_only()
    async def perms(self, ctx):
        """Tells you what permissions the bot has."""
        embed = discord.Embed(
            title=f"{self.bot.user.name}",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            url=f"{Website}",
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
        )
        perms = "\n".join(
            [
                f"- {p}".replace("_", " ")
                for p, value in ctx.guild.me.guild_permissions
                if value is True
            ]
        )
        if "administrator" in perms:
            perms = "All of them lol"
        embed.add_field(
            name=f"{self.bot.user.name} has the following permissions:",
            value=f"{perms}",
        )
        embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.cooldown(1, 500, commands.BucketType.guild)
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.command(usage="`tp!rainbow`")
    async def rainbow(self, ctx):
        """Creates a bunch of color roles for your server.
        This command has a 500 second cooldown for the entire server to prevent rate limit abuse and api spam."""

        def check(m):
            return m.author.id == ctx.author.id

        with open("colors.json", "r") as f:
            data = json.load(f)
            message = await ctx.send(
                "READ THIS BEFORE YOU DO ANYTHING!!!\nTo STOP making roles send `cancel`!! You have 20 seconds.\nWAIT UNTIL I GET DONE MAKING COLOR ROLES BEFORE YOU START REMOVING THEM!!!\n**If you want to REMOVE color roles, WAIT until I get DONE. When I'm DONE, send `removerainbow`!**"
            )
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=20)
            if msg.content == "cancel":
                return await message.edit(content="Okay, cancled.")
            else:
                pass
        except asyncio.TimeoutError:
            await message.edit(
                content="Okay, 20 seconds has passed. Time to make roles!"
            )
            await asyncio.sleep(3)
            for role in ctx.guild.roles:
                if role.name == "red":
                    return await message.edit(
                        content="Seems as though the color roles have already been made in this server, or there are already color roles present. Please remove those roles. \nSpecifically, I saw that there was a role named `red` in this server, therefor I cannot tell if thats a color role or some other type of role, please either rename it or remove it."
                    )
                else:
                    pass
            for color, hexcode in data.items():
                await ctx.guild.create_role(
                    name=color, colour=discord.Colour(int(hexcode, 0))
                )
                await message.edit(content=f"Created {color}.")
                await asyncio.sleep(0.5)
            await message.edit(
                content=f"Alright, I've made all the colors, have fun.\nTo give yourself a color role, run `{ctx.prefix}help colorme` and follow its instructions."
            )

    @commands.cooldown(1, 500, commands.BucketType.guild)
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.command(usage="`tp!removerainbow`")
    async def removerainbow(self, ctx):
        """Remove all the rainbow roles in your server so you dont have to do it manually.
        This command has a 500 second cooldown for the entire server to prevent rate limit abuse and api spam."""

        def check(m):
            return m.author.id == ctx.author.id and ctx.message.content

        with open("colors.json", "r") as f:
            data = json.load(f)
        async with ctx.channel.typing():
            m = await ctx.send(
                "Alright, I'm about to delete all the color roles. You have 10 seconds to send `cancel` to stop me."
            )
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=10)
                if msg.content == "cancel":
                    return await m.edit(content="Okay, cancled.")
            except asyncio.TimeoutError:
                await m.edit(
                    content="Alright, 10 seconds has passed, time to start deleting roles!"
                )
                await asyncio.sleep(3)
                await m.edit(content="Alright, deleting roles...")
                await asyncio.sleep(0.5)
                for color, hexcode in data.items():
                    reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
                    role = discord.utils.get(ctx.guild.roles, name=color)
                    await role.delete(reason=reason)
                    await m.edit(content=f"Deleted {color}.")
                    await asyncio.sleep(1.1)
                await m.edit(content=f"Alright, all rainbow roles have been deleted.")

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.command(aliases=["nick"], usage="`tp!nick <user> <optional:name>`")
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(embed_links=True, manage_nicknames=True)
    async def nickname(self, ctx, member: discord.Member, *, name: str = None):
        """Nicknames a user from the current server."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        try:
            await member.edit(
                nick=name, reason=default.responsible(ctx.author, "Changed by command")
            )
            message = f"Changed **{member.name}'s** nickname to **{name}**"
            if name is None:
                message = f"Reset **{member.name}'s** nickname"
            await ctx.send(message)
        except Exception as e:
            await ctx.send(
                "I don't have the permission to change that user's nickname."
            )

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @permissions.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True, manage_channels=True)
    @commands.guild_only()
    @commands.command(aliases=["slow", "slowmode", "sm"], usage="`tp!slowmode <time>`")
    async def toggleslow(self, ctx: commands.Context, time: int = 0):
        """
        Slow the chat."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if time < 0 or time > 21600:
            await ctx.send(
                "Invalid time specified! Time must be between 0 and 21600 (inclusive)"
            )
            return
        try:
            await ctx.channel.edit(slowmode_delay=time)
        except discord.Forbidden:
            await ctx.send("I don't have manage channel permissions.")
            return
        if time > 0:
            await ctx.send(
                (
                    "{0.mention} is now in slow mode. You may send 1 message "
                    "every {1} seconds".format(ctx.channel, time)
                )
            )
        else:
            await ctx.send(
                ("Slow mode has been disabled for {0.mention}".format(ctx.channel))
            )

    @commands.command(aliases=["newmembers"], usage="`tp!newusers <optional:count>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.guild_only()
    async def newusers(self, ctx, *, count=5):
        """Tells you the newest members of the server.
        This is useful to check if any suspicious members have
        joined.
        The count parameter can only be up to 25.
        """
        count = max(min(count, 25), 5)

        if not ctx.guild.chunked:
            await self.bot.request_offline_members(ctx.guild)

        members = sorted(ctx.guild.members, key=lambda m: m.joined_at, reverse=True)[
            :count
        ]

        embed = discord.Embed(title="New Members", colour=discord.Colour.green())

        for member in members:
            body = f"Joined {time.human_timedelta(member.joined_at)}\nCreated {time.human_timedelta(member.created_at)}"
            embed.add_field(
                name=f"{member} (ID: {member.id})", value=body, inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(embed_links=True, manage_nicknames=True)
    async def hoist(self, ctx: commands.Context):
        """Changes users names that are hoisting themselves (Ignores Bots)"""
        chars = [
            "!",
            ".",
            "-",
            "_",
            "*",
            "(",
            ")",
            "=",
            "+",
            "^",
            "&",
            "~",
            "#",
            "$",
            ":",
            ";",
            "?",
            "<",
            ">",
            "{",
            "}",
            "[",
            "]",
            "|",
        ]
        temp = {}
        failed = 0

        initial = await ctx.send(
            "Kk, changing peoples names. This'll take some time so please be patient!"
        )
        async with ctx.typing():
            for member in ctx.guild.members:
                if not member.bot:
                    for char in chars:
                        if member.display_name.startswith(char):
                            try:
                                await member.edit(nick="No Hoisting")
                                await asyncio.sleep(random.randint(1, 5))
                            except discord.HTTPException:
                                failed += 1
                                pass
                            temp.update({char: temp.get(char, 0) + 1})
                        if member.display_name[0].isdigit():
                            try:
                                await member.edit(nick="No Hoisting")
                                await asyncio.sleep(random.randint(1, 5))
                                temp.update({"numbers": temp.get("numbers", 0) + 1})
                            except:
                                failed += 1
        stats = "\n".join([f"`{char}` - `{amount}`" for char, amount in temp.items()])
        await initial.edit(
            content=f"I have unhoisted `{sum(temp.values())}` nicks and failed to edit `{failed}` nicks.\nHere are some stats:\n\n{stats}"
        )

    @commands.command(
        aliases=["ran", "resetallnicknames", "resetnicks", "resetnicknames"]
    )
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(embed_links=True, manage_nicknames=True)
    async def reset_names(self, ctx):
        """Tries to reset all members nicknames in the current server (Ignores bots)"""
        inital = await ctx.send(
            "Reseting all nicknames. This'll take some time so please be patient!"
        )
        count = 0
        for member in ctx.guild.members:
            if member.nick is None:
                continue
            if not member.bot:
                try:
                    await member.edit(nick=None)
                    await asyncio.sleep(random.randint(1, 5))
                    count += 1
                except:
                    pass
        await inital.edit(content=f"{count} nicknames have been reset.")

    @commands.command(usage="`tp!bans`")
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True, ban_members=True)
    async def bans(self, ctx):
        """Shows the servers bans with the ban reason"""
        filename = f"{ctx.guild.id}"
        f = open(f"{str(filename)}.txt", "a", encoding="utf-8")
        for entry in await ctx.guild.bans():
            user = entry.user
            data = f"{entry.user.id}: {entry.reason}"
            f.write(data + "\n")
            continue
        f.close()
        try:
            await ctx.send(
                content="Sorry if this took a while to send, but here is all of this servers bans!",
                file=discord.File(f"{str(filename)}.txt"),
            )
        except:
            await ctx.send(
                "I couldn't send the file of this servers bans for whatever reason"
            )
            pass
        os.remove(f"{filename}.txt")

    @commands.command(usage="`tp!ban <member:optional ID> <optional:reason>`")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def ban(self, ctx, member: MemberID, *, reason: ActionReason = None):
        """
        Bans a member from the server.
        You can also use userID's.
        the bot needs have Ban Member permissions.
        You also need Ban Member permissions.
        Example: `tp!ban @Motzumoto#9773`
        """
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        if await permissions.check_priv(ctx, member):
            return
        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        ban_msg = await ctx.send(
            f"<:banHammer:875376602651959357> {ctx.author.mention} banned {member}"
        )
        try:
            await member.send(
                f"You were banned in **{ctx.guild.name}** : **{reason}**."
            )
        except:
            pass
        try:
            await ctx.guild.ban(member, reason=reason)
        except Exception as e:
            await ban_msg.edit(content=f"Error{e}")
        await ban_msg.edit(
            content=f"<a:Banned1:872972866092662794><a:Banned2:872972848354983947><a:Banned3:872972787877314601> {ctx.author.mention} banned {member}",
            embed=discord.Embed(
                color=EMBED_COLOUR,
                description=f"**{member}** has been banned from {ctx.guild.name}.",
            ),
        )

    @commands.command(usage="`tp!massban <userMention or userID(s)>`")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def massban(
        self, ctx, members: commands.Greedy[MemberID], *, reason: ActionReason = None
    ):
        """Bans a member from the server.
        You can also use userID's.
        the bot needs have Ban Member permissions.
        You also need Ban Member permissions.
        You can ban multiple people at the same time.
        Example: `tp!ban userID\nuserID2\nuserID3`
        It can also be used with a mention.
        """
        banned_members = 0
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if not members:
            if len(members) < 1:
                await ctx.send(
                    "this command can only be used on multiple people\neg: `tp!ban userID\nuserID2\nuserID3`"
                )
                return
            else:
                return await ctx.send(
                    "Please either put a user mention or multiple user ID's to ban!"
                )
        m = await ctx.send("Working...")
        async with ctx.channel.typing():
            if len(members) > 1:
                for member in members:
                    if await permissions.check_priv(ctx, member):
                        return
                    else:
                        try:
                            if reason is None:
                                reason = (
                                    f"Action done by {ctx.author} (ID: {ctx.author.id})"
                                )
                        except:
                            pass
                        await ctx.guild.ban(member, reason=reason)
                        banned_members += 1
                await m.edit(content=f"I successfully banned {banned_members} people!")
            else:
                await m.edit(content=default.actionmessage("banned"))

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.command(usage="`tp!unban <memberID> <optional:reason>`")
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def unban(self, ctx, member: BannedMember, *, reason: ActionReason = None):
        """Unbans a member from the server.
        You can pass either the ID of the banned member or the Name#Discrim
        combination of the member. Typically the ID is easiest to use.
        In order for this to work, the bot must have Ban Member permissions.
        To use this command you must have Ban Members permissions.
        """
        if await permissions.check_priv(ctx, member):
            return

        if reason is None:
            reason = f"reason: {ctx.author} (ID: {ctx.author.id})"

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.send(
                f"Unbanned {member.user}\n(ID: {member.user.id}) {member.reason}."
            )
        else:
            await ctx.send(f"Unbanned {member.user} (ID: {member.user.id}).")

    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    @commands.command(usage="`tp!unbanall <optional:reason>`")
    async def unbanall(self, ctx, *, reason: ActionReason = None):
        """Unbans everyone from the server.
        You can pass an optional reason to be shown in the audit log.
        You must have Ban Members permissions.
        """
        if reason is None:
            reason = f"reason: {ctx.author} (ID: {ctx.author.id})"
        members = await ctx.guild.bans()
        for member in members:
            await ctx.guild.unban(member.user, reason=reason)
        await ctx.send(f"Unbanned everyone in {ctx.guild.name}.")

    @commands.command(usage="`tp!kick <member:optional ID> <optional:reason>`")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @permissions.has_permissions(kick_members=True)
    @commands.bot_has_permissions(embed_links=True, kick_members=True)
    async def softban(self, ctx, member: MemberID, *, reason: ActionReason = None):
        """Soft bans a member from the server.
        To use this command you must have Kick Members permissions.
        """
        if await permissions.check_priv(ctx, member):
            return

        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"

        await ctx.guild.ban(member, reason=reason)
        await ctx.guild.unban(member, reason=reason)
        await ctx.send(f"Alright, softbanned em, reason: {reason}")

    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.group(case_insensitive=True, usage="`tp!find <search>`")
    @commands.guild_only()
    async def find(self, ctx):
        """Finds a user within your search term"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @find.command(name="username", aliases=["name"], usage="`tp!find name <search>`")
    async def find_name(self, ctx, *, search: str):
        loop = [
            f"{i} ({i.id})"
            for i in ctx.guild.members
            if search.lower() in i.name.lower() and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(
        name="nickname", aliases=["nick"], usage="`tp!find nickname <search>`"
    )
    async def find_nickname(self, ctx, *, search: str):
        loop = [
            f"{i.nick} | {i} ({i.id})"
            for i in ctx.guild.members
            if i.nick
            if (search.lower() in i.nick.lower()) and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="id", usage="`tp!find id <search>`")
    async def find_id(self, ctx, *, search: int):
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (str(search) in str(i.id)) and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.command(
        usage="`tp!makerole <member:optional ID> <role:optional name> <reason:optional>`"
    )
    async def makerole(self, ctx, *, role: str, reason: ActionReason = None):
        """Create a new role on the server."""
        if reason is None:
            reason = f"reason: {ctx.author} (ID: {ctx.author.id})"
        if role in [r.name for r in ctx.guild.roles]:
            await ctx.send(f"**{role}** already exists!")
        else:
            await ctx.guild.create_role(
                name=role,
                reason=f"{reason} | {ctx.author} (ID: {ctx.author.id})",
                color=discord.Color.red(),
                permissions=discord.Permissions.none(),
            )
            await ctx.send(f"**{role}** created!")

    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.command(usage="`tp!deleterole <role>`")
    async def deleterole(self, ctx, *, role: str):
        """Delete a role from the server."""
        role = discord.utils.get(ctx.guild.roles, name=role)
        if role is None:
            await ctx.send(f"**{role}** does not exist!")
        else:
            await role.delete()
            await ctx.send(f"**{role}** deleted!")

    @commands.command(usage="`tp!mute <member> <optional:reason>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = None):
        """Mutes a user from the current server.
        The user will be unmuted automatically in 30 minutes.
        If you don't want the user to be unmuted automatically, do `tp!permamute`"""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if await permissions.check_priv(ctx, member):
            return

        muted_role = next(
            (g for g in ctx.guild.roles if g.name.lower() == "muted"), None
        )

        if not muted_role:
            await ctx.send(
                "This server doesn't have a muted role set, create one with `tp!role`"
            )
            return
        try:
            await member.add_roles(
                muted_role, reason=default.responsible(ctx.author, reason)
            )
            await ctx.send(default.actionmessage("muted"))
        except Exception as e:
            await ctx.send(e)
        try:
            await asyncio.sleep(1800)
            if not muted_role in member.roles:
                return
            else:
                await member.remove_roles(
                    muted_role, reason=default.responsible(ctx.author, reason)
                )
        except discord.Forbidden:
            return

    #        @tasks.loop(count=None)
    #        async def mute_task(user, time, ctx):
    #            await mute_loop(user, time, ctx)

    #        async def mute_loop(user, time, ctx):
    #            muted_role = next((g for g in ctx.guild.roles if g.name.lower() == "muted"), None) # Name of role
    #            await user.add_roles(muted_role)
    #            await asyncio.sleep(time*1800)
    #            await user.remove_roles(muted_role)
    #            await user.send(f"You have been unmuted in {ctx.guild}")

    @commands.command(usage="`tp!permamute <member> <optional:reason>`", aliases=["pm"])
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    async def permamute(self, ctx, member: discord.Member, *, reason: str = None):
        """Mute someone forever. They do not get automatically unmuted.
        Unlike regular mute, this one is a one and done command."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if await permissions.check_priv(ctx, member):
            return

        muted_role = next(
            (g for g in ctx.guild.roles if g.name.lower() == "muted"), None
        )

        if not muted_role:
            return await ctx.send(
                "It looks like this server doesn't have a muted role, please go make one."
            )
        await member.add_roles(
            muted_role, reason=default.responsible(ctx.author, reason)
        )
        await ctx.send(default.actionmessage("muted"))

    @commands.command(usage="`tp!unmute <member> <optional:reason>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = None):
        """Unmutes a user from the current server."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        muted_role = next(
            (g for g in ctx.guild.roles if g.name.lower() == "muted"), None
        )

        if not muted_role:
            return await ctx.send(
                "This technically shouldn't happen... Did you delete your muted role?"
            )

        await member.remove_roles(
            muted_role, reason=default.responsible(ctx.author, reason)
        )
        await ctx.send(default.actionmessage("unmuted"))

    # Forked from and edited https://github.com/Rapptz/RoboDanny/blob/715a5cf8545b94d61823f62db484be4fac1c95b1/cogs/mod.py#L1163

    @commands.group(invoke_without_command=True, usage="`tp!help purge`")
    @commands.guild_only()
    @checks.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def purge(self, ctx, num: Union[int, str] = None):
        """Removes messages that meet a criteria.
        In order to use this command, you must have Manage Messages permissions.
        Note that the bot needs Manage Messages as well. These commands cannot
        be used in a private message.
        When the command is done doing its work, you will get a message
        detailing which users got removed and how many messages got removed.
        `tp!purge all` removes 30 messages.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

    async def do_removal(
        self,
        ctx,
        limit,
        predicate,
        *,
        before=None,
        after=None,
        oldest_first=True,
        bulk=True,
    ):
        if limit > 2000:
            return await ctx.send(f"Too many messages to search given ({limit}/2000)")

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(
                limit=limit, before=before, after=after, check=predicate
            )
        except discord.Forbidden as e:
            return await ctx.send("I do not have permissions to delete messages.")
        except discord.HTTPException as e:
            return await ctx.send(f"Error: {e} (try a smaller search?)")

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"**{name}**: {count}" for name, count in spammers)

        to_send = "\n".join(messages)

        if len(to_send) > 2000:
            await ctx.send(
                f"Successfully removed {deleted} messages.", delete_after=delay
            )
        else:
            await ctx.send(to_send, delete_after=delay)

    @purge.command(usage="`tp!purge all <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def all(self, ctx, search=30):
        """Removes all messages."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.do_removal(ctx, search, lambda e: True)

    @purge.command(usage="`tp!purge embeds <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def embeds(self, ctx, search=100):
        """Removes messages that have embeds in them."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @purge.command(usage="`tp!purge files <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def files(self, ctx, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @purge.command(usage="`tp!purge images <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def images(self, ctx, search=100):
        """Removes messages that have embeds or attachments."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.do_removal(
            ctx, search, lambda e: len(e.embeds) or len(e.attachments)
        )

    @purge.command(usage="`tp!purge mentions <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def mentions(self, ctx, search=30):
        """Removes messages that have user mentions."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.do_removal(ctx, search, lambda e: len(e.mentions))

    @purge.command(usage="`tp!purge <user> <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def user(self, ctx, member: discord.Member, search=100):
        """Removes all messages by the member."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @purge.command(usage="`tp!purge contains <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def startswith(self, ctx, *, substr: str):
        """Removes all messages that start with a keyword"""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        await self.do_removal(ctx, 100, lambda e: e.content.startswith(substr))

    @purge.command(usage="`tp!purge contains <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def contains(self, ctx, *, substr: str):
        """Removes all messages containing a substring.
        The substring must be at least 2 characters long.
        """
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @purge.command(
        name="bot", aliases=["bots"], usage="`tp!purge bots <optional:search>`"
    )
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def bot(self, ctx, prefix=None, search=300):
        """Removes a bot user's messages and messages with their optional prefix."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        getprefix = prefix if prefix else self.config.prefix

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or m.content.startswith(
                tuple(getprefix)
            )

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="emoji",
        aliases=["emojis", "emote", "emotes"],
        usage="`tp!purge emotes <optional:search>`",
    )
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def emoji(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(name="reactions", usage="`tp!purge reactions <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        if search > 2000:
            return await ctx.send(f"Too many messages to search for ({search}/2000)")

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.send(f"Successfully removed {total_reactions} reactions.")

    @purge.command(usage="`tp!purge annoying <optional:search>`")
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def annoying(self, ctx, search=250, prefix=None):
        """Removes annoying messages.
        This command purges mentions, embeds, files / attachments, and role mentions."""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await self.do_removal(
            ctx,
            search,
            lambda e: len(e.mentions)
            and len(e.embeds)
            and len(e.attachments)
            and len(e.role_mentions),
        )
        getprefix = prefix if prefix else self.config.prefix

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or m.content.startswith(
                tuple(getprefix)
            )

        await self.do_removal(ctx, search, predicate)


def setup(bot):
    bot.add_cog(Moderator(bot))
