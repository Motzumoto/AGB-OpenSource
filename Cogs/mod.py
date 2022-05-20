import argparse
import datetime
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
from utils import checks, default, permissions, imports
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
        self.config = imports.get("config.json")
        try:
            self.bot.command_prefix = self.get_prefix
        except Exception:
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
        except Exception:
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
        except Exception:
            pass
        return prefix

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title=f"Error Caught!", color=0xFF0000, description=f"{error}"
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        await ctx.send(
            embed=embed,
        )

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
                except Exception:
                    pass

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_guild=True)
    async def toggle(self, ctx, *, command: str, ephemeral: bool = False):
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
            await ctx.send("I can't find a command with that name!", ephemeral=True)
        elif ctx.command == command:
            await ctx.send("You cannot disable this command.", ephemeral=True)
        elif "help" == command:
            await ctx.send("You cannot disable this command.", ephemeral=True)
        else:
            # commandsEnabled[str(ctx.guild.id)][command.name] = not commandsEnabled[
            #     str(ctx.guild.id)
            # ][command.name]
            try:
                cursor_n.execute(
                    f"SELECT {command} FROM public.commands WHERE guild = '{ctx.guild.id}'"
                )
            except Exception:
                await ctx.send(
                    "Command can not be found or can not be toggled.", ephemeral=True
                )
                return
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
            await ctx.send(
                embed=embed,
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    @commands.bot_has_permissions(embed_links=True, kick_members=True)
    @commands.hybrid_command()
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kicks a user from the current server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await ctx.message.delete()
        except Exception:
            pass
        if await permissions.check_priv(ctx, member):
            return
        await member.kick(reason=default.responsible(ctx.author, reason))
        await ctx.send(default.actionmessage("kicked"))

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_channels=True)
    async def setprefix(self, ctx, new: str = None):
        """Set a custom prefix for the server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

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

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def addrole(self, ctx, user: discord.Member, *, role: discord.Role):
        """Adds a role to a user"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await user.add_roles(role)
        except:
            await ctx.send("I couldn't add that role to that user.")
            return
        await ctx.send(
            f"Aight, gave {role.name} to {user.mention}",
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False
            ),
        )

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    async def removerole(self, ctx, user: discord.Member, *, role: discord.Role):
        """Removes a role from a user"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await ctx.message.delete()
        except Exception:
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
    @commands.hybrid_command()
    async def deleterole(self, ctx, *, role: str):
        """Delete a role from the server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        role = discord.utils.get(ctx.guild.roles, name=role)
        if role is None:
            await ctx.send(f"**{role}** does not exist!")
        else:
            await role.delete()
            await ctx.send(f"**{role}** deleted!")

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command()
    @commands.guild_only()
    async def perms(self, ctx):
        """Tells you what permissions the bot has."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

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
            url=Website,
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(
            text=f"lunardev.group",
            icon_url=ctx.author.avatar,
        )
        await ctx.send(
            embed=embed,
        )

    @permissions.dynamic_ownerbypass_cooldown(1, 500, commands.BucketType.guild)
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.hybrid_command()
    @commands.guild_only()
    async def rainbow(self, ctx):
        """Creates a bunch of color roles for your server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

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
    @commands.hybrid_command()
    @commands.guild_only()
    async def removerainbow(self, ctx):
        """Remove all the rainbow roles in your server so you dont have to do it manually."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

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
    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(embed_links=True, manage_nicknames=True)
    async def nickname(self, ctx, member: discord.Member, *, name: str = None):
        """Nicknames a user from the current server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await ctx.message.delete()
        except Exception:
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
    @commands.hybrid_command()
    async def toggleslow(self, ctx, time: int = 0):
        """
        Slow the chat."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await ctx.message.delete()
        except Exception:
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

    @commands.hybrid_command()
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
            return await ctx.send(":x: This command has been disabled!")

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
                            except Exception:
                                failed += 1
        stats = "\n".join([f"`{char}` - `{amount}`" for char, amount in temp.items()])
        await initial.edit(
            content=f"I have unhoisted `{sum(temp.values())}` nicks and failed to edit `{failed}` nicks.\nHere are some stats:\n\n{stats}"
        )

    @commands.hybrid_command()
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
            return await ctx.send(":x: This command has been disabled!")

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
                except Exception:
                    pass
        await inital.edit(content=f"{count} nicknames have been reset.")

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def bans(self, ctx):
        """Shows the servers bans with the ban reason"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        filename = f"{ctx.guild.id}"
        f = open(f"{str(filename)}.txt", "a", encoding="utf-8")
        async for entry in ctx.guild.bans():
            data = f"{entry.user.id}: {entry.reason}"
            f.write(data + "\n")
            continue
        f.close()
        try:
            await ctx.send(
                content="Sorry if this took a while to send, but here is all of this servers bans!",
                file=discord.File(f"{str(filename)}.txt"),
            )
        except Exception:
            await ctx.send(
                "I couldn't send the file of this servers bans for whatever reason"
            )
        os.remove(f"{filename}.txt")

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=3, type=commands.BucketType.user
    )
    async def banreason(self, ctx, user: discord.User):
        """Shows the ban reason for a user in the current server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        # itterate through the bans and find the one that matches the user
        async for entry in ctx.guild.bans():
            if entry.user.id == user.id:
                await ctx.send(f"{user.mention} has been banned for: `{entry.reason}`")
        else:
            await ctx.send(f"{user.mention} is not banned in this server.")

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def ban(
        self,
        ctx,
        member: MemberID,
        *,
        reason: ActionReason = None,
    ):
        """
        Bans a member from the server.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await ctx.message.delete()
        except Exception:
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
        except Exception:
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

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def sban(
        self,
        ctx,
        member: MemberID,
        *,
        reason: ActionReason = None,
        ephemeral: bool = False,
    ):
        """
        Silently bans a member from the server, the user will not get a dm.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await ctx.message.delete()
        except Exception:
            pass
        # check if the command was used as a slash command
        if ctx.interaction is None:
            if await permissions.check_priv(ctx, member):
                return
        else:
            if await permissions.check_priv(ctx, member, ephemeral=True):
                return
        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        ban_msg = await ctx.author.send(
            f"<:banHammer:875376602651959357> {ctx.author.mention} banned {member}"
        )
        try:
            await ctx.guild.ban(member, reason=reason)
        except Exception as e:
            await ban_msg.edit(content=f"Couldn't ban {member}, Error\n{e}")
            return
        await ban_msg.edit(content="Done.")

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def massban(
        self, ctx, members: commands.Greedy[MemberID], *, reason: ActionReason = None
    ):
        """Ban multiple members at once."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        banned_members = 0
        try:
            await ctx.message.delete()
        except Exception:
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
                        except Exception:
                            pass
                        await ctx.guild.ban(member, reason=reason)
                        banned_members += 1
                await m.edit(content=f"I successfully banned {banned_members} people!")
            else:
                await m.edit(content=default.actionmessage("banned"))

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    @commands.bot_has_permissions(embed_links=True, ban_members=True)
    async def unban(self, ctx, member: BannedMember, *, reason: ActionReason = None):
        """Unbans a member from the server.
        You can pass either the ID of the banned member or the Name#Discrim
        combination of the member. Typically the ID is easiest to use.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

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
    @commands.hybrid_command()
    async def unbanall(self, ctx, *, reason: ActionReason = None):
        """Unbans everyone from the server.
        You can pass an optional reason to be shown in the audit log.
        You must have Ban Members permissions.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")
        unbanned = 0
        if reason is None:
            reason = f"reason: {ctx.author} (ID: {ctx.author.id})"
        async for member in ctx.guild.bans():
            await ctx.guild.unban(member.user, reason=reason)
            unbanned += 1
        await ctx.send(f"Unbanned {unbanned} users.")

    @commands.hybrid_command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(kick_members=True, ban_members=True)
    @commands.bot_has_permissions(embed_links=True, kick_members=True, ban_members=True)
    async def softban(self, ctx, member: MemberID, *, reason: ActionReason = None):
        """Soft bans a member from the server.
        To use this command you must have Kick and Ban Members permissions.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if await permissions.check_priv(ctx, member):
            return

        if reason is None:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"

        await ctx.guild.ban(member, reason=reason)
        await ctx.guild.unban(member, reason=reason)
        await ctx.send(f"Alright, softbanned em, reason: {reason}")

    @commands.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_emojis=True, manage_guild=True)
    @commands.bot_has_permissions(embed_links=True, manage_emojis=True)
    async def stealemoji(self, ctx, emote: discord.PartialEmoji):
        """Clones any emote to the current server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        await ctx.guild.create_custom_emoji(
            name=emote.name,
            image=await emote.read(),
            reason=f"{ctx.author} used steal_emote",
        )
        await ctx.send(f"I successfully cloned {emote.name} to {ctx.guild.name}!")

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_group(case_insensitive=True)
    @commands.guild_only()
    async def find(self, ctx):
        """Finds a user within your search term"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @find.command(name="username", aliases=["name"])
    async def find_name(self, ctx, *, search: str):
        """Find a user by their name

        Args:
            search (str): The name of the user you are searching for
        """
        loop = [
            f"{i} ({i.id})"
            for i in ctx.guild.members
            if search.lower() in i.name.lower() and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="nickname", aliases=["nick"])
    async def find_nickname(self, ctx, *, search: str):
        """Find a user by their nickname

        Args:
            search (str): The nickname to search for
        """
        loop = [
            f"{i.nick} | {i} ({i.id})"
            for i in ctx.guild.members
            if i.nick
            if (search.lower() in i.nick.lower()) and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="id")
    async def find_id(self, ctx, *, search: int):
        """Find a user by their ID

        Args:
            search (int): The ID of the user you are searching for
        """
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (str(search) in str(i.id)) and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="discrim")
    async def find_discrim(self, ctx, *, search: str):
        """Find a user by their discriminator

        Args:
            search (str): The discriminator to search for
        """
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (search.lower() in i.discriminator) and not i.bot
        ]
        await default.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(
        embed_links=True, manage_roles=True, manage_channels=True
    )
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_group()
    async def channel(self, ctx):
        """Group command for channel related things"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return

    @channel.command(name="create")
    @permissions.has_permissions(manage_channels=True)
    async def create(self, ctx, channel: str):
        """Create a channel

        Args:
            channel (str): channel name
        """
        if channel in [i.name for i in ctx.guild.channels]:
            return await ctx.send(f"{channel} already exists!")
        # check if the channel name is below 100 characters
        if len(channel) > 100:
            return await ctx.send(
                "Channel name is too long! Please make it under 100 characters."
            )
        await ctx.guild.create_text_channel(channel)
        await ctx.send(f"{channel} has been created!")

    @channel.command(name="delete")
    @permissions.has_permissions(manage_channels=True)
    async def delete(self, ctx, channel: discord.TextChannel):
        """Delete a channel

        Args:
            channel (discord.TextChannel): the channel to delete
        """
        if channel.name in [i.name for i in ctx.guild.channels]:
            await channel.delete()
            await ctx.send(f"{channel.name} has been deleted!")
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @channel.command()
    @permissions.has_permissions(manage_channels=True)
    async def rename(self, ctx, channel: discord.TextChannel, new_name: str):
        """Rename a channel

        Args:
            channel (str): the channel to rename
            new_name (str): the new name for the channel
        """
        if channel.name in [i.name for i in ctx.guild.channels]:
            if len(new_name) > 100:
                return await ctx.send("Channel name is too long!")
            await channel.edit(name=new_name)
            await ctx.send(f"{channel.name} has been renamed to: `{new_name}`!")
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @channel.group()
    @permissions.has_permissions(manage_channels=True)
    async def edit(self, ctx):
        """Edit a channel

        Args:
            channel (discord.TextChannel): the channel to edit
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return

    @edit.command()
    @permissions.has_permissions(manage_channels=True)
    async def topic(self, ctx, channel: discord.TextChannel, *, topic: str):
        """edit the topic of a channel

        Args:
            channel (discord.TextChannel): the channel to edit
            topic (str): the new topic for the channel
        """
        if channel.name in [i.name for i in ctx.guild.channels]:
            if len(topic) > 1024:
                return await ctx.send("Topic is too long!")
            await channel.edit(topic=topic)
            await ctx.send(f"{channel.name}'s topic has been changed to: `{topic}`!")
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @edit.command()
    @permissions.has_permissions(manage_channels=True)
    async def description(self, ctx, channel: discord.TextChannel, *, description: str):
        """edit the description of a channel

        Args:
            channel (discord.TextChannel): the channel to edit
            description (str): the new description for the channel

        """
        if channel.name in [i.name for i in ctx.guild.channels]:
            if len(description) > 1024:
                return await ctx.send("Description is too long!")
            await channel.edit(description=description)
            await ctx.send(
                f"{channel.name}'s description has been changed to: `{description}`!"
            )
        else:
            return await ctx.send(f"{channel.name} doesn't exist!")

    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_group()
    async def role(self, ctx):
        """A group command for role related commands"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))
            return

    @role.command(name="make")
    @permissions.has_permissions(manage_roles=True)
    async def make(
        self,
        ctx,
        name: str,
        permissions: str or int = None,
        hoist: bool = False,
        mentionable: bool = False,
        hex: str = None,
    ):
        """Creates a role with any name, permissions, hoistable, mentionable, and color
        Example: `tp!role create bruh 8 True True ff0000`
        Look at a permission calculator for more info on permissions: https://finitereality.github.io/permissions-calculator/
        Args:
            name (str): the name of the role
            permissions (str): the permissions for the role
            hoist (bool, optional): set the role to be hoisted. Defaults to False.
            mentionable (bool, optional): set the role to be mentionable. Defaults to False.
            hex (int, optional): the color to set the role. Defaults to None.
        """
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

    @role.command()
    @permissions.has_permissions(manage_roles=True)
    async def remove(self, ctx, role: discord.Role):
        """Deletes a role

        Args:
            role (str): the role to delete
        """
        if role is None:
            return await ctx.send(":x: You need to give a role!")
        # check if a role with the name exists
        if role.name in [i.name for i in ctx.guild.roles]:
            # tell the user that theres roles with the same name
            if len([i for i in ctx.guild.roles if i.name == role.name]) > 1:
                return await ctx.send("There are roles with the same name!")
            else:
                await role.delete()
                await ctx.send("Role deleted!")

    @role.command()
    @permissions.has_permissions(manage_roles=True)
    async def forcedel(self, ctx, role: discord.Role):
        await role.delete(reason=f"{ctx.author} used role forcedel")
        await ctx.send(f"I've successfully deleted {role.name}!")

    @role.command()
    @permissions.has_permissions(manage_roles=True)
    async def change(
        self,
        ctx,
        role: discord.Role,
        name: str,
        permissions: str or int = None,
        hoist: bool = False,
        mentionable: bool = False,
        hex: str or int or hex = None,
    ):
        """Edit any role to add new permissions, make it hoisted, mentionable, and a new color
        Example: `tp!role edit role_name new_name permission_value hoist:True/False mentionable:True/False hex:number`
        **Hint** True and False are case sensitive.

        Args:
            ctx (_type_): _description_
            role (str): the role to edit
            name (str): the new name for the role
            permissions (int, optional): permission value to give the role. Defaults to None.
            hoist (bool, optional): set the role to be hoisted. Defaults to False.
            mentionable (bool, optional): set the role to be mentionable. Defaults to False.
            hex (int, optional): color hex to set the role. Defaults to None.
        """
        if role is None:
            await ctx.send(":x: Specify a role that you want me to edit!")
            return

        if hex is not None:
            try:
                hex = int(hex, 16)
            except:
                pass
        else:
            hex = 0

        if permissions is not None:
            if permissions is not int:
                if permissions == "all":
                    permissions = discord.Permissions.all()
                else:
                    try:
                        permissions = discord.Permissions(int(permissions))
                    except:
                        await ctx.send(
                            "Look at a permission calculator for more info on permissions: https://finitereality.github.io/permissions-calculator/\nWhen you get the permissions that you want, copy the number on the very top of the page. Should look something like this",
                            file=discord.File("permissions.png"),
                        )
                        return
        else:
            permissions = discord.Permissions.none()

        try:
            await role.edit(
                name=name,
                permissions=permissions,
                hoist=hoist,
                mentionable=mentionable,
                color=discord.Color(value=hex),
                reason=f"{ctx.author} used role edit",
            )
            await ctx.send(
                f"Alright, I've edited {role.name} with the following overrides: Permission Value:{permissions.value} Hex:{hex} Hoist:{hoist} Mentionable:{mentionable}"
            )
        except Exception as e:
            await ctx.send(f"I couldn't edit the role because of this error!:\n{e}")

    @commands.hybrid_command()
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
    async def nuke(
        self, ctx, channel: discord.TextChannel = None, ephemeral: bool = False
    ):
        """Deletes a channel and clones it for you to quickly delete all the messages inside of it"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        try:
            await ctx.message.delete()
        except Exception:
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
            return await ctx.send("You took to long to react.", delete_after=10)
        if str(reaction.emoji) == "❌":
            await confirmation.delete()
            await ctx.send("Task cancelled!", ephemeral=True)
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
        try:
            await deleted_channel.delete(reason=f"{ctx.author} used nuke")
        except:
            return await ctx.send(
                f"Couldn't delete {deleted_channel.name}. Give me the permissions to do so."
            )
        try:
            await new_channel.send(embed=embed, delete_after=30)
        except Exception:
            pass
        try:
            await ctx.send("Channel nuked!", delete_after=5)
        except Exception:
            pass

    @commands.hybrid_command()
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
            return await ctx.send(":x: This command has been disabled!")

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

    @commands.hybrid_command()
    @permissions.slash_has_permissions(moderate_members=True)
    @commands.bot_has_permissions(embed_links=True, moderate_members=True)
    @commands.guild_only()
    async def mute(
        self,
        ctx,
        member: discord.Member,
        time: str,
        reason: str,
        ephemeral: bool = False,
    ):
        """Mute someone for a certain amount of time, from 10 seconds to 28 days."""

        # make a tuple of valid time unit strings
        valid_time_units = ("s", "m", "h", "d", "w")
        if not time.endswith(valid_time_units):
            await ctx.send(
                "Invalid time unit! Please use s, m, h, d, or w.", ephemeral=True
            )
            return
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
                "You can't mute someone for more than 28 days! Please use a shorter time.",
                ephemeral=True,
            )
            return
        if await permissions.check_priv(ctx, member=member):
            return
        try:
            await member.timeout(datetime.timedelta(seconds=time), reason=reason)
        except Exception as e:
            # say that the bot needs moderate_members permissions
            await ctx.send(
                f"I couldn't mute {member.mention}! Please make sure I have the `Timeout Members` permission!\nHere's the error: {e}",
                ephemeral=True,
            )
            return

        if time > 86400:
            await ctx.send(
                f"{member.mention} has been muted for {time // 86400} days.",
                ephemeral=ephemeral,
            )
        elif time > 3600:
            await ctx.send(
                f"{member.mention} has been muted for {time // 3600} hours.",
                ephemeral=ephemeral,
            )
        elif time > 60:
            await ctx.send(
                f"{member.mention} has been muted for {time // 60} minutes.",
                ephemeral=ephemeral,
            )
        else:
            await ctx.send(
                f"{member.mention} has been muted for {time} seconds.",
                ephemeral=ephemeral,
            )

    @commands.hybrid_command()
    @permissions.slash_has_permissions(moderate_members=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @commands.guild_only()
    async def unmute(self, ctx, member: discord.Member, *, reason: str = None):
        """Unmute someone"""
        # check if the member is timed out

        if member.is_timed_out:
            try:
                await member.timeout(None, reason=reason)
                await ctx.send(f"{member.mention} has been unmuted.")
            except Exception as e:
                await ctx.send(
                    f"I couldn't unmute {member.mention}! Please make sure I have the `Timeout Members` permission!\nHere's the error: {e}",
                    ephemeral=True,
                )
        else:
            await ctx.send(f"{member.mention} is not timed out!", ephemeral=True)

    # Forked from and edited
    # https://github.com/Rapptz/RoboDanny/blob/715a5cf8545b94d61823f62db484be4fac1c95b1/cogs/mod.py#L1163

    # @commands.hybrid_command(usage="`tp!ss`", aliases=["ss"])
    # @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    # @commands.guild_only()
    # @permissions.has_permissions(manage_roles=True)
    # @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    # async def server_setup(self, ctx):
    #     """Sets up the server for you, makes basic roles, channels, and syncs permissions."""
    #     cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
    #     if cmdEnabled:
    #         await ctx.send(":x: This command has been disabled!")
    #         return
    #     #a list of the new roles with their permissions
    #     new_roles = [
    #         "Muted",
    #         "Member",
    #         "Moderator",
    #         "Admin",
    #         "Owner",
    #     ]
    #     #a list of the channels to create
    #     general_channels = [
    #         "general",
    #         "bots",
    #         "memes",
    #         "media",
    #         "spam",
    #         "nsfw"
    #     ]
    #     #staff channels
    #     staff_channels = [
    #         "staff-announcements",
    #         "staff-chat",
    #         "staff-logs",
    #         "staff-testing"
    #         ]

    #     #logging
    #     logging_channels = [
    #         "message-logs",
    #         "mod-logs",
    #     ]

    #     #wait for the author to make sure they want to do this
    #     def check(m):
    #         return m.author == ctx.author and m.channel == ctx.channel

    #     try:
    #         start = await ctx.send(
    #             "Are you sure you want to do this? This will delete all channels, roles, and permissions.\nType `yes` to continue and `no` to cancel."
    #         )
    #         msg = await self.bot.wait_for("message", check=check, timeout=30)
    #     except asyncio.TimeoutError:
    #         return await ctx.send("Timed out.")
    #     if msg.content.lower() == "yes":
    #         await start.edit("Alright, let's do this!")
    #     else:
    #         return await ctx.send("Aborting.")
    #     #delete the existing roles, channels, and categories
    #     # await asyncio.sleep(3)
    #     # try:
    #     #     for channel in ctx.guild.channels:
    #     #         await channel.delete()
    #     #     for role in ctx.guild.roles:
    #     #         await role.delete()
    #     #     for category in ctx.guild.categories:
    #     #         await category.delete()
    #     # except Exception:
    #     #     pass
    #     await ctx.guild.create_text_channel("temp")
    #     #create the new roles
    #     for role in new_roles:
    #         await ctx.guild.create_role(name=role, mentionable=True)
    #     #edit the new roles to have the correct permissions

    #     #create the new categories
    #     general = await ctx.guild.create_category(name="Communication", reason="Server Setup")
    #     staff = await ctx.guild.create_category(name="Staff", reason="Server Setup")
    #     logging = await ctx.guild.create_category(name="Logging", reason="Server Setup")
    #     #create the new channels in the new categories
    #     for channel in general_channels:
    #         await ctx.guild.create_text_channel(
    #             ctx.guild,
    #             channel,
    #             category=general,
    #             reason="Server Setup"
    #         )
    #     for channel in staff_channels:
    #         await ctx.guild.create_text_channel(
    #             ctx.guild,
    #             channel,
    #             category=staff,
    #             reason="Server Setup"
    #         )
    #     for channel in logging_channels:
    #         await ctx.guild.create_text_channel(
    #             ctx.guild,
    #             channel,
    #             category=logging,
    #             reason="Server Setup"
    #         )
    #     #edit the new channels to sync permissions
    #     for channel in general_channels:
    #         channel = ctx.guild.get_channel(channel)
    #         await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Member")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Moderator")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Admin")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Owner")), send_messages=True)
    #     for channel in staff_channels:
    #         channel = ctx.guild.get_channel(channel)
    #         await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Moderator")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Admin")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Owner")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Member")), send_messages=False)
    #     for channel in logging_channels:
    #         channel = ctx.guild.get_channel(channel)
    #         await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Moderator")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Admin")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Owner")), send_messages=True)
    #         await channel.set_permissions(ctx.guild.get_role(new_roles("Member")), send_messages=False)
    #     #send a final message in the general channel
    #     msg = await ctx.guild.get_channel(general_channels("general")).send(
    #         ":white_check_mark: Server setup complete!\n"
    #         "Please check the channels and roles to make sure everything is set up correctly."
    #     )

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @checks.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True, manage_roles=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 8, commands.BucketType.user)
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
            return await ctx.send(":x: This command has been disabled!")

        if ctx.invoked_subcommand is None:
            # assume we're purging all messages and invoke purge all
            num = int(num) if num is not None else 30
            if num == 0:
                return await ctx.send(
                    ":x: You cannot purge 0 messages.", delete_after=10
                )
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

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def all(self, ctx, search=30):
        """Removes all messages."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.do_removal(ctx, search, lambda e: True)

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def embeds(self, ctx, search=100):
        """Removes messages that have embeds in them."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def files(self, ctx, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def images(self, ctx, search=100):
        """Removes messages that have embeds or attachments."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.do_removal(
            ctx, search, lambda e: len(e.embeds) or len(e.attachments)
        )

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def mentions(self, ctx, search=30):
        """Removes messages that have user mentions."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.do_removal(ctx, search, lambda e: len(e.mentions))

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def user(self, ctx, member: MemberConverter, search=100):
        """Removes all messages by the member."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def startswith(self, ctx, *, substr: str):
        """Removes all messages that start with a keyword"""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        await self.do_removal(ctx, 100, lambda e: e.content.startswith(substr))

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def contains(self, ctx, *, substr: str):
        """Removes all messages containing a substring.
        The substring must be at least 2 characters long.
        """
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @purge.command(name="bot", aliases=["bots"])
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def bot(self, ctx, prefix=None, search=300):
        """Removes a bot user's messages and messages with their optional prefix.
        Example: `tp!purge bots <the bots prefix[this is optional]> <amount[this is also optional]>`"""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        getprefix = prefix if prefix else self.config.prefix

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or m.content.startswith(
                tuple(getprefix)
            )

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        aliases=["emojis", "emote", "emotes"],
    )
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def emoji(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        if search > 2000:
            return await ctx.send(f"Too many messages to search for ({search}/2000)")

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.send(f"Successfully removed {total_reactions} reactions.")

    @purge.command()
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def annoying(self, ctx, search=250, prefix=None):
        """Removes annoying messages.
        This command purges mentions, embeds, files / attachments, and role mentions."""
        try:
            await ctx.message.delete()
        except Exception:
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
