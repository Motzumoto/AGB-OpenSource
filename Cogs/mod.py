import argparse
import datetime
from datetime import timedelta
import asyncio
import json
import os
import random
import re
from collections import Counter
from typing import Union

import discord
from discord.ext import commands
from index import EMBED_COLOUR, Website, config, delay, cursor_n, mydb_n
from utils import checks, default, permissions
from Manager.commandManager import cmd


def can_execute_action(ctx, user, target):
    return (
        user.id == ctx.bot.owner_id
        or user == ctx.guild.owner
        or user.top_role > target.top_role
    )


class MemberNotFound(Exception):
    pass


# edited from RoboDanny (i had a plan to use this but i just dont remember
# for what)


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


class MemberConverter(commands.MemberConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except commands.BadArgument:
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
                )


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
        try:
            self.bot.command_prefix = self.get_prefix
        except:
            pass
        self.default_prefix = "tp!"
        blist = []
        self.blacklist = blist
        self.prefixes = None

    def get_prefix(self, bot, message):
        prefix = None
        try:
            cursor_n.execute(
                f"SELECT prefix FROM public.guilds WHERE guildId = '{message.guild.id}'"
            )
        except:
            pass
        try:
            for row in cursor_n.fetchall():
                self.prefixes = row[0]
            prefix = (
                self.prefixes
                if getattr(message, "guild", None)
                else self.default_prefix
            )
            mydb_n.commit()
        except:
            pass
        return prefix

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title=f"Error Caught!", color=0xFF0000, description=f"{error}"
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        await ctx.send(embed=embed)

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
                    icon_url=message.author.avatar,
                )
                channel = self.bot.get_channel(730651628302106718)
                if message.author.bot:
                    return
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

    @commands.command(usage="`tp!toggle <command_name>`")
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_guild=True)
    async def toggle(self, ctx, *, command):
        """Toggle commands in your server to be enabled/disabled"""
        # if not commandsEnabled[str(ctx.guild.id)][str(ctx.command.name)]:
        #     await ctx.send(":x: This command has been disabled!")
        #     return

        # if cmdRow[0][0] == "true":
        #     await ctx.send(":x: This command has been disabled!")
        #     return
        # mydb_n.commit() LEAVE THIS COMMENTED OUT

        command = self.bot.get_command(command)

        if command is None:
            await ctx.send("I can't find a command with that name!")
        elif ctx.command == command:
            await ctx.send("You cannot disable this command.")
        elif "help" == command:
            await ctx.send("You cannot disable this command.")
        else:
            # commandsEnabled[str(ctx.guild.id)][command.name] = not commandsEnabled[
            #     str(ctx.guild.id)
            # ][command.name]
            try:
                cursor_n.execute(
                    f"SELECT {command} FROM public.commands WHERE guild = '{ctx.guild.id}'"
                )
            except:
                await ctx.send("Command can not be found or can not be toggled.")
            cmdRow = cursor_n.fetchall()

            # True = command disabled; false = enabled
            cmdBool = bool
            if cmdRow[0][0] == "true":
                cmdBool = True
            else:
                cmdBool = False

            ternary = "enabled" if cmdBool else "disabled"

            if ternary == "enabled":
                cursor_n.execute(
                    f"UPDATE public.commands SET {command.name} = 'false' WHERE guild = '{ctx.guild.id}'"
                )
            else:
                cursor_n.execute(
                    f"UPDATE public.commands SET {command.name} = 'true' WHERE guild = '{ctx.guild.id}'"
                )

            mydb_n.commit()

            embed = discord.Embed(
                title="Command Toggled",
                colour=discord.Colour.green(),
                timestamp=ctx.message.created_at,
            )
            embed.add_field(
                name="Success",
                value=f"The `{command}` command has been **{ternary}**",
            )
            embed.set_thumbnail(url=ctx.message.author.avatar)
            embed.set_author(
                name=ctx.message.author.name, icon_url=ctx.message.author.avatar
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["enabler", "ron"], usage="`tp!ron`")
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=2, type=commands.BucketType.user
    )
    @permissions.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True, manage_guild=True)
    async def raid_on(self, ctx):
        """Enables basic raid mode for your server
        This enables extreme raid prevention, everyone is then required to have a verified phone to be able to talk in your server.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.guild.edit(
                verification_level=discord.VerificationLevel.extreme
            ) or (ctx.guild.edit(verification_level=discord.VerificationLevel.high))
        except discord.HTTPException:
            await ctx.send("\N{WARNING SIGN} Could not set verification level.")
            return

        await ctx.send(
            f"Raid mode enabled. People are now required to have a verified email and phone connected to their account to be able to talk here."
        )

    @commands.command(aliases=["disabler", "roff"], usage="`tp!roff`")
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=2, type=commands.BucketType.user
    )
    @permissions.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True, manage_guild=True)
    async def raid_off(self, ctx):
        """Disables raid mode on the server.
        When disabled, the server verification levels are set
        back to Low levels."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

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

    @commands.command(usage="`tp!cleanup`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
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

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    @commands.bot_has_permissions(embed_links=True, kick_members=True)
    @commands.command(usage="`tp!kick @user`", ignore_extra=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kicks a user from the current server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
            pass
        if await permissions.check_priv(ctx, member):
            return
        await member.kick(reason=default.responsible(ctx.author, reason))
        await ctx.send(default.actionmessage("kicked"))

    @commands.command(usage="`tp!setprefix newprefix`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_channels=True)
    async def setprefix(self, ctx, new=None):
        """Set a custom prefix for the server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        no_prefix = discord.Embed(
            title="Please put a prefix you want.", colour=EMBED_COLOUR
        )
        if not new:
            return await ctx.send(embed=no_prefix)
        else:
            pass
        if len(new) > 5:
            await ctx.send("I don't accept prefixes over 5 characters.")
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
                cursor_n.execute(
                    f"UPDATE public.guilds SET prefix = '{new}' WHERE guildId = '{ctx.guild.id}'"
                )
                mydb_n.commit()
            except discord.errors.Forbidden:
                await ctx.send(
                    "I couldn't update my nickname, the prefix has changed though."
                )

    @commands.command(usage="`tp!prefix`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def prefix(self, ctx):
        """If you don't know what the servers current prefix is, you can check with this command"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        # with open("prefixes.json") as f:
        #     prefixes = json.load(f)

        #     if prefixes == None:
        #         return await ctx.send("There isnt a custom prefix for this server. The default prefix is `tp!`")
        #     else:
        #         pass
        try:
            cursor_n.execute(
                f"SELECT prefix FROM public.guilds WHERE guildId = '{ctx.guild.id}'"
            )
        except:
            pass
        result = cursor_n.fetchall()
        for row in result:
            # prefixes[str(ctx.guild.id)]
            embed = discord.Embed(
                title="AGB",
                url=f"{Website}",
                colour=EMBED_COLOUR,
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                timestamp=ctx.message.created_at,
            )
            embed.add_field(name="Prefix for this server:", value=f"{row[0]}")
            embed.set_footer(
                text="lunardev.group",
                icon_url=ctx.author.avatar,
            )
            await ctx.send(embed=embed)
            mydb_n.commit()

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["ar"], usage="`tp!ar @user role`")
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def addrole(self, ctx, user: discord.Member, *, role: discord.Role):
        """Adds a role to a user"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        await user.add_roles(role)
        await ctx.send(
            f"Aight, gave {role.name} to {user.mention}",
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False
            ),
        )

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["rr"], usage="`tp!rr @user role`")
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    async def removerole(self, ctx, user: discord.Member, *, role: discord.Role):
        """Removes a role from a user"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
            pass
        await user.remove_roles(role)
        await ctx.send(
            f"Aight, removed {role.name} from {user.mention}",
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False
            ),
        )

    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.command(usage="`tp!deleterole role`")
    async def deleterole(self, ctx, *, role: str):
        """Delete a role from the server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        role = discord.utils.get(ctx.guild.roles, name=role)
        if role is None:
            await ctx.send(f"**{role}** does not exist!")
        else:
            await role.delete()
            await ctx.send(f"**{role}** deleted!")

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!perms`")
    @commands.guild_only()
    async def perms(self, ctx):
        """Tells you what permissions the bot has."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        perms = "\n".join(
            [
                f"- {p}".replace("_", " ")
                for p, value in ctx.guild.me.guild_permissions
                if value is True
            ]
        )
        if "administrator" in perms:
            perms = "Administrator ( All permissions )"

        embed = discord.Embed(
            title=f"{self.bot.user.name} has the following permissions:",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})\n**{perms}**",
            url=f"{Website}",
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(
            text=f"lunardev.group",
            icon_url=ctx.author.avatar,
        )
        await ctx.send(embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 500, commands.BucketType.guild)
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.command(usage="`tp!rainbow`")
    async def rainbow(self, ctx):
        """Creates a bunch of color roles for your server.
        This command has a 500 second cooldown for the entire server to prevent rate limit abuse and api spam."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        def check(m):
            return m.author.id == ctx.author.id

        with open("colors.json", "r") as f:
            data = json.load(f)
            message = await ctx.send(
                "***READ THIS BEFORE YOU DO ANYTHING!!!***\nTo STOP making roles send `cancel`! If you say anything before this prompt changes the process will also stop. If you for some reason want to remove the color roles after I get done, please run `tp!rainbowremove`."
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

    @permissions.dynamic_ownerbypass_cooldown(1, 500, commands.BucketType.guild)
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.command(usage="`tp!removerainbow`")
    async def removerainbow(self, ctx):
        """Remove all the rainbow roles in your server so you dont have to do it manually.
        This command has a 500 second cooldown for the entire server to prevent rate limit abuse and api spam."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

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

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["nick"], usage="`tp!nick @user optional:name`")
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(embed_links=True, manage_nicknames=True)
    async def nickname(self, ctx, member: discord.Member, *, name: str = None):
        """Nicknames a user from the current server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
            pass

        try:
            await member.edit(
                nick=name, reason=default.responsible(ctx.author, "Changed by command")
            )
            message = f"Changed **{member.name}'s** nickname to **{name}**"
            if name is None:
                message = f"Reset **{member.name}'s** nickname"
            await ctx.send(message)
        except Exception:
            await ctx.send(
                "I don't have the permission to change that user's nickname."
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True, manage_channels=True)
    @commands.guild_only()
    @commands.command(aliases=["slow", "slowmode", "sm"], usage="`tp!slowmode time`")
    async def toggleslow(self, ctx, time: int = 0):
        """
        Slow the chat."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
            pass
        if time < 0 or time > 21600:
            await ctx.send(
                "Invalid time specified! Time must be between 0 and 21600 (inclusive)"
            )
            return
        try:
            await ctx.channel.edit(slowmode_delay=time)
        except discord.errors.Forbidden:
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

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=10, type=commands.BucketType.user
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(embed_links=True, manage_nicknames=True)
    async def hoist(self, ctx):
        """Changes users names that are hoisting themselves (Ignores Bots)"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

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
        aliases=[
            "ran",
            "resetallnicknames",
            "resetnicks",
            "resetnicknames",
            "resetnames",
        ]
    )
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=10, type=commands.BucketType.user
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(embed_links=True, manage_nicknames=True)
    async def reset_names(self, ctx):
        """Tries to reset all members nicknames in the current server (Ignores bots)"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

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
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def bans(self, ctx):
        """Shows the servers bans with the ban reason"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        filename = f"{ctx.guild.id}"
        f = open(f"{str(filename)}.txt", "a", encoding="utf-8")
        for entry in await ctx.guild.bans():
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
        os.remove(f"{filename}.txt")

    # make a command to see the ban reason for a user in a server
    @commands.command(usage="`tp!banreason <user>`")
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=3, type=commands.BucketType.user
    )
    async def banreason(self, ctx, user: discord.User):
        """Shows the ban reason for a user in the current server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        for entry in ctx.guild.bans:
            if entry.user.id == user.id:
                await ctx.send(
                    f"{entry.user.mention} has been banned for {entry.reason}"
                )

    @commands.command(usage="`tp!ban member:optional ID optional:reason`")
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def ban(self, ctx, member: MemberID, *, reason: ActionReason = None):
        """
        Bans a member from the server.
        You can also use userID's.
        the bot needs have Ban Member permissions.
        You also need Ban Member permissions.
        Example: `tp!ban @Motzumoto#9773`
        Example with reason: `tp!ban @Motzumoto#9773 I'm a bad person`
        Example with userID: `tp!ban 101118549958877184`
        Example with userID and reason: `tp!ban 101118549958877184 I'm a bad person`
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
            pass
        if await permissions.check_priv(ctx, member):
            return
        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        ban_msg = await ctx.send(
            f"<:banHammer:875376602651959357> {ctx.author.mention} banned {member}"
        )
        try:
            await member.send(f"You were banned in **{ctx.guild.name}**\n**{reason}**.")
        except:
            pass
        try:
            await ctx.guild.ban(member, reason=reason)
        except Exception as e:
            await ban_msg.edit(content=f"Error{e}")
        await ban_msg.edit(
            embed=discord.Embed(
                color=EMBED_COLOUR,
                description=f"<a:Banned1:872972866092662794><a:Banned2:872972848354983947><a:Banned3:872972787877314601> **{member}** has been banned: reason {reason}",
            ),
        )

    @commands.command(usage="`tp!sban member:optional ID optional:reason`")
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def sban(self, ctx, member: MemberID, *, reason: ActionReason = None):
        """
        Silently bans a member from the server, this means that the user does not get a dm when they are banned.
        You can also use userID's.
        the bot needs have Ban Member permissions.
        You also need Ban Member permissions.
        Example: `tp!sban @Motzumoto#9773`
        Example with reason: `tp!sban @Motzumoto#9773 I'm a bad person`
        Example with userID: `tp!sban 101118549958877184`
        Example with userID and reason: `tp!sban 101118549958877184 I'm a bad person`
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
            pass
        if await permissions.check_priv(ctx, member):
            return
        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        ban_msg = await ctx.send(
            f"<:banHammer:875376602651959357> {ctx.author.mention} banned {member}"
        )
        try:
            await ctx.guild.ban(member, reason=reason)
        except Exception as e:
            await ban_msg.edit(content=f"Error{e}")
        await ban_msg.edit(content="Done.")

    @commands.command(usage="`tp!massban userMention or userID(s)`")
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        banned_members = 0
        try:
            await ctx.message.delete()
        except:
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

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!unban memberID optional:reason`")
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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

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
    @commands.command(usage="`tp!unbanall optional:reason`")
    async def unbanall(self, ctx, *, reason: ActionReason = None):
        """Unbans everyone from the server.
        You can pass an optional reason to be shown in the audit log.
        You must have Ban Members permissions.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if reason is None:
            reason = f"reason: {ctx.author} (ID: {ctx.author.id})"
        members = await ctx.guild.bans()
        for member in members:
            await ctx.guild.unban(member.user, reason=reason)
        await ctx.send(f"Unbanned everyone in {ctx.guild.name}.")

    @commands.command(usage="`tp!kick member:optional ID optional:reason`")
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(kick_members=True)
    @commands.bot_has_permissions(embed_links=True, kick_members=True)
    async def softban(self, ctx, member: MemberID, *, reason: ActionReason = None):
        """Soft bans a member from the server.
        To use this command you must have Kick Members permissions.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if await permissions.check_priv(ctx, member):
            return

        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"

        await ctx.guild.ban(member, reason=reason)
        await ctx.guild.unban(member, reason=reason)
        await ctx.send(f"Alright, softbanned em, reason: {reason}")

    @commands.command(usage="`tp!se emote`", aliases=["stealemote", "se", "steale"])
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_emojis=True, manage_guild=True)
    @commands.bot_has_permissions(embed_links=True, manage_emojis=True)
    async def steal_emote(self, ctx, emote: discord.PartialEmoji):
        """Clones any emote to the current server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        await ctx.guild.create_custom_emoji(
            name=emote.name,
            image=await emote.read(),
            reason=f"{ctx.author} used steal_emote",
        )
        await ctx.send(f"I successfully cloned {emote.name} to {ctx.guild.name}!")

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.group(case_insensitive=True, usage="`tp!find search`")
    @commands.guild_only()
    async def find(self, ctx):
        """Finds a user within your search term"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return
        try:
            await ctx.message.delete()
        except:
            pass
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @find.command(name="username", aliases=["name"], usage="`tp!find name search`")
    async def find_name(self, ctx, *, search: str):
        loop = [
            f"{i} ({i.id})"
            for i in ctx.guild.members
            if search.lower() in i.name.lower() and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="nickname", aliases=["nick"], usage="`tp!find nickname search`")
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

    @find.command(name="id", usage="`tp!find id search`")
    async def find_id(self, ctx, *, search: int):
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (str(search) in str(i.id)) and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="discrim", usage="`tp!find discrim search`")
    async def find_discrim(self, ctx, *, search: str):
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (search.lower() in i.discriminator) and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.group(usage="`tp!channel")
    async def channel(self, ctx):
        """A group of commands for managing channels"""

        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return

    @channel.command(name="create", usage="`tp!channel create channel_name`")
    async def create(self, ctx, channel):
        """Create a channel"""
        if channel in [i.name for i in ctx.guild.channels]:
            return await ctx.send(f"{channel} already exists!")
        await ctx.guild.create_text_channel(channel)
        await ctx.send(f"{channel} has been created!")

    @channel.command(name="delete", usage="`tp!channel delete channel_name`")
    async def delete(self, ctx, channel: discord.TextChannel):
        """Delete a channel"""
        if channel.name in [i.name for i in ctx.guild.channels]:
            await channel.delete()
            await ctx.send(f"{channel.name} has been deleted!")
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @channel.command(name="rename", usage="`tp!channel rename channel_name new_name`")
    async def rename(self, ctx, channel, new_name):
        """Rename a channel"""
        if channel.name in [i.name for i in ctx.guild.channels]:
            await channel.edit(name=new_name)
            await ctx.send(f"{channel.name} has been renamed to {new_name}!")
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @channel.group(name="edit", usage="`tp!channel edit`")
    async def edit(self, ctx, channel: discord.TextChannel):
        """Edit a channel"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return

    @edit.command(name="topic", usage="`tp!channel edit topic`")
    async def topic(self, ctx, channel: discord.TextChannel, *, topic):
        """Edit a channel's topic"""
        if channel.name in [i.name for i in ctx.guild.channels]:
            await channel.edit(topic=topic)
            await ctx.send(f"{channel.name}'s topic has been changed to {topic}!")
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @edit.command(name="description", usage="`tp!channel edit description`")
    async def description(self, ctx, channel: discord.TextChannel, *, description):
        """Edit a channel's description"""
        if channel.name in [i.name for i in ctx.guild.channels]:
            await channel.edit(description=description)
            await ctx.send(
                f"{channel.name}'s description has been changed to {description}!"
            )
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.group(usage="`tp!role")
    async def role(self, ctx):
        """A group command for role related commands"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return

    @role.command(
        name="create",
        usage="`tp!role create name permissions:number or all hoist:True/False mentionable:True/False hex:number`",
    )
    async def create(
        self,
        ctx,
        name,
        permissions,
        hoist: bool = False,
        mentionable: bool = False,
        hex=None,
    ):
        """Creates a role with any name, permissions, hoistable, mentionable, and color
        Example: `tp!role create bruh 8 True True ff0000`
        Look at a permission calculator for more info on permissions: https://finitereality.github.io/permissions-calculator/"""
        if name is None:
            await ctx.send(":x: You need to give a name for the role!")
            return

        if permissions is not None:
            if permissions is not int:
                if permissions == "all":
                    permissions = discord.Permissions.all()
                else:
                    permissions = discord.Permissions(int(permissions))
            else:
                await ctx.send(
                    "Look at a permission calculator for more info on permissions: https://finitereality.github.io/permissions-calculator/\nWhen you get the permissions that you want, copy the number on the very top of the page. Should look something like this",
                    file=discord.File("permissions.png"),
                )
        else:
            permissions = discord.Permissions.none()

        if hex is not None:
            hex = int(hex, 16)
        else:
            hex = 0

        await ctx.guild.create_role(
            name=name,
            permissions=permissions,
            color=discord.Color(value=hex),
            hoist=hoist,
            mentionable=mentionable,
            reason=f"{ctx.author} used role create",
        )
        await ctx.send(
            f"Alright, I've created {name} with the following overrides: Permission Value:{permissions.value} Hex:{hex} Hoist:{hoist} Mentionable:{mentionable}"
        )

    @role.command(name="delete", usage="`tp!role delete name`")
    async def delete(self, ctx, role):
        """Deletes a role
        Example: `tp!role delete role_name`"""
        loop = [i for i in ctx.guild.roles if role.lower() in i.name.lower()]
        if len(loop) == 0:
            await ctx.send("I couldn't find that role!")
            return
        if len(loop) > 1:
            await default.prettyResults(
                ctx,
                "name",
                f"Found **{len(loop)}** roles with your search for **{role}**\n**Hint** Use tp!role forcedel role_name",
                loop,
            )
            return
        await loop[0].delete(reason=f"{ctx.author} used role delete")
        await ctx.send(f"I've successfully deleted {loop[0].name}!")

    @role.command(name="forcedel", usage="`tp!role forcedel name`")
    async def forcedel(self, ctx, role: discord.Role):
        """Forcefully deletes a role, ignores other roles with the same name (Not recommended to use)
        Example: `tp!role forcedel role_name`"""
        await role.delete(reason=f"{ctx.author} used role forcedel")
        await ctx.send(f"I've successfully deleted {role.name}!")

    @role.command(
        name="change",
        usage="`tp!role edit role_name permissions:number or all hoist:True/False mentionable:True/False hex:number`",
    )
    async def change(
        self,
        ctx,
        role,
        name,
        permissions: int = None,
        hoist: bool = False,
        mentionable: bool = False,
        hex=None,
    ):
        """Edit any role to add new permissions, make it hoisted, mentionable, and a new color
        Example: `tp!role edit role_name new_name permission_value hoist:True/False mentionable:True/False hex:number`
        **Hint** True and False are case sensitive."""
        if role is None:
            await ctx.send(":x: Specify a role that you want me to edit!")
            return

        if hex is not None:
            hex = int(hex, 16)
        else:
            hex = 0

        if permissions is not None:
            if permissions is not int:
                if permissions == "all":
                    permissions = discord.Permissions.all()
                else:
                    permissions = discord.Permissions(int(permissions))
            else:
                await ctx.send(
                    "Look at a permission calculator for more info on permissions: https://finitereality.github.io/permissions-calculator/\nWhen you get the permissions that you want, copy the number on the very top of the page. Should look something like this",
                    file=discord.File("permissions.png"),
                )
        else:
            permissions = discord.Permissions.none()

        try:
            edited = discord.utils.find(
                lambda r: role.lower() in r.name.lower(), ctx.guild.roles
            )
            await edited.edit(
                name=name,
                permissions=permissions,
                hoist=hoist,
                mentionable=mentionable,
                color=discord.Color(value=hex),
                reason=f"{ctx.author} used role edit",
            )
            await ctx.send(
                f"Alright, I've edited {name} with the following overrides: Permission Value:{permissions.value} Hex:{hex} Hoist:{hoist} Mentionable:{mentionable}"
            )
        except Exception as e:
            await ctx.send(
                f"I couldn't edit the role because of this error!:\n{await default.prettyResults(e)}"
            )

    @commands.command(usage="`tp!nuke channel:name`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(
        embed_links=True,
        manage_channels=True,
        manage_guild=True,
        manage_messages=True,
        attach_files=True,
        add_reactions=True,
        read_message_history=True,
        send_messages=True,
        use_external_emojis=True,
        mention_everyone=True,
        external_emojis=True,
        manage_webhooks=True,
        manage_permissions=True,
        manage_nicknames=True,
        change_nickname=True,
        manage_threads=True,
    )
    async def nuke(self, ctx, channel: discord.TextChannel = None):
        """Deletes a channel and clones it for you to quickly delete all the messages inside of it"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        try:
            await ctx.message.delete()
        except:
            pass
        embed = discord.Embed(title="Channel Nuked", color=0x00FF00)
        embed.set_image(url="https://media.giphy.com/media/HhTXt43pk1I1W/giphy.gif")
        if channel is None:
            await ctx.send(f"Please specify a channel to delete!")
            return

        confirmation = await ctx.send(
            f"Are you sure you want to do this? This action cannot be undone!"
        )
        await confirmation.add_reaction("✅")
        await confirmation.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=30, check=check
            )
        except asyncio.TimeoutError:
            await confirmation.delete()
            return
        if str(reaction.emoji) == "❌":
            await confirmation.delete()
            return

        await confirmation.delete()
        deleted_channel = self.bot.get_channel(channel.id)
        new_channel = await ctx.guild.create_text_channel(
            name=deleted_channel.name,
            reason=f"{ctx.author} used nuke",
            overwrites=deleted_channel.overwrites,
            position=deleted_channel.position,
            topic=deleted_channel.topic,
            slowmode_delay=deleted_channel.slowmode_delay,
            nsfw=deleted_channel.nsfw,
            category=deleted_channel.category,
        )
        await deleted_channel.delete(reason=f"{ctx.author} used nuke")
        try:
            await new_channel.send(embed=embed)
        except:
            pass
        await ctx.send("Channel nuked!", delete_after=5)

    @commands.command(usage="`tp!mutesetup`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True, manage_channels=True)
    @commands.bot_has_permissions(
        embed_links=True, manage_roles=True, manage_channels=True
    )
    async def mutesetup(self, ctx):
        """Sets up the muted role for the server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        init = await ctx.send("Setting up the muted role...")
        await asyncio.sleep(1.5)
        muted_role = next(
            (g for g in ctx.guild.roles if g.name.lower() == "muted"), None
        )

        if not muted_role:
            await init.edit(
                content="I couldn't find a muted role!\nI'll create one for you and assign the correct permissions for you!"
            )
            await asyncio.sleep(3)
            muted_role = await ctx.guild.create_role(
                name="muted",
                color=discord.Colour.dark_grey(),
                hoist=False,
                mentionable=False,
            )
        for channel in ctx.guild.channels:
            if channel.type == discord.ChannelType.text:
                # first, check if the channels already have the permissions set
                if channel.permissions_for(muted_role).send_messages is False:
                    continue  # pretty proud of this function
                else:
                    await channel.set_permissions(muted_role, send_messages=False)
        await init.edit(content=f"I've set up the muted role and permissions for you!")

    @commands.command(usage="`tp!mute @member time:time reason:reason`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(embed_links=True, moderate_members=True)
    async def mute(self, ctx, member: discord.Member, time, reason):
        """Mute a user out for a certain amount of time
        Example: `tp!mute @user 1h reason`

        Args:
            member (discord.Member): The user to mute
            time (_type_): The amount of time to mute the user for
            reason (_type_): The reason for the mute
        """
        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        if time.endswith("s"):
            time = int(time[:-1])
        elif time.endswith("m"):
            time = int(time[:-1]) * 60
        elif time.endswith("h"):
            time = int(time[:-1]) * 3600
        elif time.endswith("d"):
            time = int(time[:-1]) * 86400
        elif time.endswith("w"):
            time = int(time[:-1]) * 604800
        else:
            time = int(time)
        if time > int(2419200):
            await ctx.send(
                "You can't mute someone for more than 28 days! Please use a shorter time."
            )
            return
        if await permissions.check_priv(ctx, member):
            return
        await member.timeout(datetime.timedelta(seconds=time), reason=reason)

        if time > 86400:
            await ctx.send(
                f"{member.mention} has been muted out for {time // 86400} days."
            )
        elif time > 3600:
            await ctx.send(
                f"{member.mention} has been muted out for {time // 3600} hours."
            )
        elif time > 60:
            await ctx.send(
                f"{member.mention} has been muted out for {time // 60} minutes."
            )
        else:
            await ctx.send(f"{member.mention} has been muted out for {time} seconds.")

    @commands.command(usage="`tp!massmute member1 member2 member3...`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(embed_links=True, moderate_members=True)
    async def massmute(self, ctx, *member: discord.Member, time, reason):
        """Mute multiple people at the same time
        ex: `tp!massmute @member1 @member2 @member3`
        DOES NOT automatically unmutes in 30 minutes."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        try:
            await ctx.message.delete()
        except:
            pass
        if await permissions.check_priv(ctx, member):
            return
        if time > 2419200:
            await ctx.send(f"You can't mute people for longer than 28 days!")
        # add the muted role to the specified members
        if time.endswith("s"):
            time = int(time[:-1])
        elif time.endswith("m"):
            time = int(time[:-1]) * 60
        elif time.endswith("h"):
            time = int(time[:-1]) * 3600
        elif time.endswith("d"):
            time = int(time[:-1]) * 86400
        elif time.endswith("w"):
            time = int(time[:-1]) * 604800
        else:
            time = int(time)
        if time > int(2419200):
            await ctx.send(
                "You can't timeout someone for more than 28 days! Please use a shorter time."
            )
            return
        for member in member:
            await member.timeout(datetime.timedelta(seconds=time), reason=reason)

        if time > 86400:
            await ctx.send(
                f"{member.mention} has been timed out for {time // 86400} days."
            )
        elif time > 3600:
            await ctx.send(
                f"{member.mention} has been timed out for {time // 3600} hours."
            )
        elif time > 60:
            await ctx.send(
                f"{member.mention} has been timed out for {time // 60} minutes."
            )
        else:
            await ctx.send(f"{len(member)} members have been timed out for {time}")
        await ctx.send(default.actionmessage("mass muted", mass=True))

    @commands.command(usage="`tp!unmute member optional:reason`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = None):
        """Unmutes a user from the current server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except:
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

    # Forked from and edited
    # https://github.com/Rapptz/RoboDanny/blob/715a5cf8545b94d61823f62db484be4fac1c95b1/cogs/mod.py#L1163

    @commands.group(invoke_without_command=True, usage="`tp!help purge`")
    @commands.guild_only()
    @checks.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def purge(self, ctx, num: Union[int, str] = None):
        """Removes messages that meet a criteria.
        In order to use this command, you must have Manage Messages permissions.
        Note that the bot needs Manage Messages as well. These commands cannot
        be used in a private message.
        When the command is done doing its work, you will get a message
        detailing which users got removed and how many messages got removed.
        `tp!purge all` removes 30 messages.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if ctx.invoked_subcommand is None:
            # assume we're purging all messages and invoke purge all
            num = int(num) if num is not None else 30
            await ctx.invoke(self.bot.get_command("purge all"), num)

    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None):
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
        except discord.errors.Forbidden as e:
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

    @purge.command(usage="`tp!purge all optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def all(self, ctx, search=30):
        """Removes all messages."""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.do_removal(ctx, search, lambda e: True)

    @purge.command(usage="`tp!purge embeds optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def embeds(self, ctx, search=100):
        """Removes messages that have embeds in them."""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @purge.command(usage="`tp!purge files optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def files(self, ctx, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @purge.command(usage="`tp!purge images optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def images(self, ctx, search=100):
        """Removes messages that have embeds or attachments."""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.do_removal(
            ctx, search, lambda e: len(e.embeds) or len(e.attachments)
        )

    @purge.command(usage="`tp!purge mentions optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def mentions(self, ctx, search=30):
        """Removes messages that have user mentions."""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.do_removal(ctx, search, lambda e: len(e.mentions))

    @purge.command(usage="`tp!purge @user optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def user(self, ctx, member: MemberConverter, search=100):
        """Removes all messages by the member."""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @purge.command(usage="`tp!purge startswith optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def startswith(self, ctx, *, substr: str):
        """Removes all messages that start with a keyword"""
        try:
            await ctx.message.delete()
        except:
            pass

        await self.do_removal(ctx, 100, lambda e: e.content.startswith(substr))

    @purge.command(usage="`tp!purge contains optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def contains(self, ctx, *, substr: str):
        """Removes all messages containing a substring.
        The substring must be at least 2 characters long.
        """
        try:
            await ctx.message.delete()
        except:
            pass
        await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @purge.command(
        name="bot", aliases=["bots"], usage="`tp!purge bots optional:search`"
    )
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def bot(self, ctx, prefix=None, search=300):
        """Removes a bot user's messages and messages with their optional prefix.
        Example: `tp!purge bots <the bots prefix[this is optional]> <amount[this is also optional]>`"""
        try:
            await ctx.message.delete()
        except:
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
        usage="`tp!purge emotes optional:search`",
    )
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def emoji(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        try:
            await ctx.message.delete()
        except:
            pass
        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(name="reactions", usage="`tp!purge reactions optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""
        try:
            await ctx.message.delete()
        except:
            pass

        if search > 2000:
            return await ctx.send(f"Too many messages to search for ({search}/2000)")

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.send(f"Successfully removed {total_reactions} reactions.")

    @purge.command(usage="`tp!purge annoying optional:search`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def annoying(self, ctx, search=250, prefix=None):
        """Removes annoying messages.
        This command purges mentions, embeds, files / attachments, and role mentions."""
        try:
            await ctx.message.delete()
        except:
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


async def setup(bot):
    await bot.add_cog(Moderator(bot))
