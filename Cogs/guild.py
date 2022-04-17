import asyncio
import json
import re
from datetime import datetime
import urllib.parse
from io import BytesIO
from typing import Union
import xml.etree.ElementTree as ET

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from index import (
    EMBED_COLOUR,
    TOP_GG_TOKEN,
    Vote,
    Website,
    config,
    embed_space,
    emojis,
    suggestion_no,
    suggestion_yes,
)
from Manager.commandManager import cmd
from utils import default, permissions
from .Utils import error_embed, success_embed


class DiscordCmds(commands.Cog, name="discord"):
    """Server related things :D"""

    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")
        self.bot.sniped_messages = {}
        self.session = aiohttp.ClientSession()
        self.bot.edit_sniped_messages = {}
        self.halloween_re = re.compile(r"h(a|4)(l|1)(l|1)(o|0)w(e|3)(e|3)n", re.I)
        # self.october_re = re.compile(r"o(c|4)(t|7)(o|0)(b|2)(e|3)(r|1)", re.I)
        self.spooky_re = re.compile(r"(s|5)(p|7)(o|0)(o|0)(k|9)(y|1)", re.I)
        self.nword_re = re.compile(
            r"\b(n|m|и|й)(i|1|l|!|ᴉ|¡)(g|ƃ|6|б)(g|ƃ|6|б)(e|3|з|u)(r|Я)\b", re.I
        )
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1.0, 3.0, commands.BucketType.user
        )

    # create a discord invite regex

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

    class SlashMemberConverter(commands.MemberConverter):
        async def convert(self, interaction, argument):
            try:
                return await super().convert(interaction, argument)
            except Exception:
                members = [
                    member
                    for member in interaction.guild.members
                    if member.display_name.lower().startswith(argument.lower())
                ]
                if len(members) == 1:
                    return members[0]
                else:
                    raise commands.BadArgument(
                        f"{len(members)} members found, please be more specific."
                    )

    @commands.Cog.listener(name="on_message")
    async def spooky(self, message):
        BotList_Servers = [
            336642139381301249,
            716445624517656727,
            523523486719803403,
            658262945234681856,
            608711879858192479,
            446425626988249089,
            387812458661937152,
            414429834689773578,
            645281161949741064,
            527862771014959134,
            733135938347073576,
            766993740463603712,
            724571620676599838,
            568567800910839811,
            641574644578648068,
            532372609476591626,
            374071874222686211,
            789934742128558080,
            694140006138118144,
            743348125191897098,
            110373943822540800,
            491039338659053568,
            891226286347923506,
        ]
        bucket = self.message_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if datetime.today().month == 10:  # and datetime.today().day == 31:
            if self.halloween_re.search(message.content.lower()):
                if retry_after:
                    return
                if message.guild.id in BotList_Servers:
                    return
                else:
                    try:
                        await message.add_reaction("🎃")
                        await asyncio.sleep(1)
                    except Exception:
                        pass
            if self.spooky_re.search(message.content.lower()):
                if retry_after:
                    return
                if message.guild.id in BotList_Servers:
                    return
                else:
                    try:
                        await message.add_reaction("👻")
                        await asyncio.sleep(1)
                    except Exception:
                        pass

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if self.nword_re.search(message.content.lower()):
            return
        if message.author.bot:
            return
        try:
            self.bot.sniped_messages[message.guild.id, message.channel.id] = (
                message.content,
                message.author,
                message.channel.name,
                message.created_at,
                message.attachments,
            )
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        bad_words = "n word"
        for word in bad_words:
            if word in before.content.lower() or word in after.content.lower():
                return
            if before.author.bot:
                return
            try:
                self.bot.edit_sniped_messages[before.guild.id, before.channel.id] = (
                    before.content,
                    after.content,
                    before.author,
                    before.channel.name,
                )
            except AttributeError:
                pass

    @commands.command(aliases=["s"], usage="`tp!s`")
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def snipe(self, ctx):
        """Snipe recently deleted messages to see what someone said."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            (
                contents,
                author,
                channel_name,
                time,
                attachments,
            ) = self.bot.sniped_messages[ctx.guild.id, ctx.channel.id]

            files = ""
            for file in attachments:
                files += f"[{file.filename}]({file.proxy_url})" + "\n"
            embed = discord.Embed(
                title=f"{self.bot.user.name}",
                url=f"{Website}",
                description=f"`{contents}`",
                color=EMBED_COLOUR,
                timestamp=time,
            )
            embed.set_author(
                name=f"{author.name}#{author.discriminator}", icon_url=author.avatar
            )
            embed.add_field(
                name="Attachments",
                value=files[:-1] if len(attachments) != 0 else "None",
            )
            embed.set_footer(text=f"Deleted in #{channel_name}")

            await ctx.send(
                content="This command is reaching its life expectancy. This command will no longer work after april 30th",
                embed=embed,
            )
        except Exception:
            await ctx.send("Nothing has been recently deleted.")

    @commands.command(aliases=["es"], usage="`tp!es`")
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def editsnipe(self, ctx):
        """Snipe edited messages to see what the message said before."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            (
                before_content,
                after_content,
                author,
                channel_name,
            ) = self.bot.edit_sniped_messages[ctx.guild.id, ctx.channel.id]

            embed = discord.Embed(
                title=f"{self.bot.user.name}",
                url=f"{Website}",
                description=f"**Before:**\n{before_content}\n\n**After:**\n{after_content}",
                color=EMBED_COLOUR,
            )
            embed.set_author(
                name=f"{author.name}#{author.discriminator}", icon_url=author.avatar
            )
            embed.set_footer(text=f"Edited in #{channel_name}")
            embed.add_field(
                name="‎‎‎‎‎‎",
                value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                inline=False,
            )

            await ctx.send(
                content="This command is reaching its life expectancy. This command will no longer work after april 30th",
                embed=embed,
            )
        except Exception:
            await ctx.send("Nothing has been recently edited.")

    @commands.command(usage="`tp!listemoji true/false`")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @permissions.has_permissions(manage_roles=True)
    async def listemoji(self, ctx, ids: bool = False):
        """Lists all available emojis in a server, perfect for an emoji channel
        true shows the emoji ID's.
        false doesnt, false is default."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        try:
            await ctx.message.delete()
        except Exception:
            pass
        description = f"Emojis for {ctx.guild.name}"
        if not ids:
            #  `:{emoji.name}:` <- looks ugly
            text = ", ".join([f"{emoji}" for emoji in ctx.guild.emojis])

            # truncate text to 5750 characters
            if len(text) > 3900:
                text = text[:3900] + "..."
            embed_no_id = discord.Embed(
                title=description, description=text, color=EMBED_COLOUR
            )
            embed_no_id.set_author(
                name=f"{ctx.message.author.name}#{ctx.message.author.discriminator}",
                icon_url=ctx.message.author.avatar,
            )
            await ctx.send(embed=embed_no_id)
        else:
            #  `:{emoji.name}:` <- looks ugly
            text = "\n".join(
                [
                    f"{emoji} (`<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>`)"
                    for emoji in ctx.guild.emojis
                ]
            )
            if len(text) > 3900:
                text = text[:3900] + "..."
            embed_id = discord.Embed(
                title=description, description=text, color=EMBED_COLOUR
            )
            embed_id.set_author(
                name=f"{ctx.message.author.name}#{ctx.message.author.discriminator}",
                icon_url=ctx.message.author.avatar,
            )
            await ctx.send(embed=embed_id)
        # for page in pagify(text):
        #     await ctx.send(page)

    #    @commands.Cog.listener(name='on_message')
    #    @commands.guild_only()
    #    async def imdad(self, message):
    #        """Handle on_message."""
    #        if not isinstance(message.channel, discord.TextChannel):
    #            return
    #        if message.type != discord.MessageType.default:
    #            return
    #        if message.author.id == self.bot.user.id:
    #            return
    #        if message.author.bot:
    #            return
    #        content = message.clean_content
    #        if len(content) == 0:
    #            return
    #        if content.lower().startswith("im ") and not (':' in content) and \
    #                        len(content) < 50:
    #            try:
    #                back = content[3:4].upper() + content[4:]
    #                if back.endswith(':).'):
    #                    back = back[:-1]
    #                back += '!'
    #                await message.channel.send(f"Hi, {back} I'm {self.bot.user.name}.".format(back=back),
    #                               allowed_mentions=discord.AllowedMentions(
    #                               everyone=False, roles=False, users=False))
    #            except (discord.HTTPException, discord.errors.Forbidden, ):
    #                pass

    @app_commands.command()
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def avatar(
        self,
        interaction: discord.Interaction,
        *,
        user: Union[discord.User, discord.Member] = None,
        ephemeral: bool = False,
    ):
        """Get anyones avatar within Discord.

        Args:
            interaction (discord.Interaction): _description_
            user (Union[discord.User, discord.Member], optional): Any userID or user tag. Defaults to None.
            ephemeral (bool, optional): Weather to make the result of the command visable to only you or not. Defaults to False.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        user = user or interaction.user
        embed = discord.Embed(
            title="User Icon", colour=EMBED_COLOUR, description=f"{user}'s avatar is:"
        )
        embed.set_image(url=user.avatar)
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @permissions.has_permissions(manage_roles=True)
    @commands.command(usage="`tp!roles`")
    @commands.bot_has_permissions(attach_files=True)
    @commands.guild_only()
    async def roles(self, ctx):
        """Get all roles in current server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        allroles = ""

        for num, role in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
            allroles += f"[{str(num).zfill(2)}] {role.id}\t{role.name}\t[ Users: {len(role.members)} ]\r\n"

        data = BytesIO(allroles.encode("utf-8"))
        await ctx.send(
            content=f"Roles in **{ctx.guild.name}**",
            file=discord.File(data, filename=f"{default.timetext('Roles')}"),
        )

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(usage="`tp!joinedat @user`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def joinedat(self, ctx, *, user: discord.Member = None):
        """Check when a user joined the current server."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        user = user or ctx.author
        embed = discord.Embed(
            title=f"{self.bot.user.name}",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            url=f"{Website}",
            colour=user.top_role.colour.value,
        )
        embed.set_thumbnail(url=user.avatar)
        embed.description = f"**{user}** joined **`{user.joined_at:%b %d, %Y - %H:%M:%S}`**\nThat was **`{(datetime.utcnow() - user.joined_at).days}`** days ago!"
        await ctx.send(embed=embed)

    @commands.command(usage="`tp!mods`")
    @commands.guild_only()
    async def mods(self, ctx):
        """Check which mods are in current guild"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        mods = []
        for member in ctx.guild.members:
            if member.bot:
                continue
            if (
                member.guild_permissions.manage_guild
                or member.guild_permissions.administrator
                or member.guild_permissions.ban_members
                or member.guild_permissions.kick_members
            ):
                mods.append(member)
        if mods:
            mod_list = ""
            for num, mod in enumerate(mods, start=1):
                mod_list += f"[{num}] {mod.name}#{mod.discriminator} [{mod.id}]\n"
            await ctx.send(f"{default.pycode(mod_list)}")
        else:
            await ctx.send("There are no mods online.")

    @commands.command(usage="`tp!firstmessage`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def firstmessage(self, ctx, channel: discord.TextChannel = None):
        """Provide a link to the first message in current or provided channel."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if channel is None:
            channel = ctx.channel
        try:
            message: discord.Message = (
                await channel.history(limit=1, oldest_first=True).flatten()
            )[0]
        except (discord.errors.Forbidden, discord.HTTPException):
            await ctx.send("Unable to read message history for that channel")
            return

        embed = discord.Embed(
            description=f"[First Message in {channel.mention}]({message.jump_url})"
        )
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.avatar
        )

        await ctx.send(embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=["channelinfo"], usage="`tp!channelinfo`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def channelstats(self, ctx):
        """Gets stats for the current channel you're in."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        channel = ctx.channel

        embed = discord.Embed(
            title=f"Stats for **{channel.name}**",
            description=f"{'Category: {}'.format(channel.category.name) if channel.category else 'This channel is not in a category'}",
            color=EMBED_COLOUR,
        )
        embed.add_field(name="Channel Guild", value=ctx.guild.name)
        embed.add_field(name="Channel Id", value=channel.id)
        embed.add_field(
            name="Channel Topic",
            value=f"{channel.topic if channel.topic else 'No topic.'}",
        )
        embed.add_field(name="Channel Position", value=channel.position)
        embed.add_field(
            name="Amount of pinned messages?", value=(len(await channel.pins()))
        )
        embed.add_field(name="Channel Slowmode Delay", value=channel.slowmode_delay)
        embed.add_field(name="Channel is nsfw?", value=channel.is_nsfw())
        embed.add_field(name="Channel is news?", value=channel.is_news())
        embed.add_field(name="Channel Creation Time", value=channel.created_at)
        embed.add_field(
            name="Channel Permissions Synced", value=channel.permissions_synced
        )
        embed.add_field(name="Channel Hash", value=hash(channel))
        await ctx.send(embed=embed)

    @commands.command(
        aliases=["feedback", "suggestion"], usage="`tp!suggest suggestion`"
    )
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 10, commands.BucketType.user)
    async def suggest(self, ctx, *, suggestion: str):
        """Suggest things this bot should have or not have."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        thanks = discord.Embed(
            title=f"Thank you for contributing to the community {ctx.author.name}.",
            colour=EMBED_COLOUR,
        )
        suggestion_channel = self.bot.get_channel(773904927579701310)
        embed = discord.Embed(
            title=f"New suggestion by {ctx.author}.",
            description=suggestion,
            colour=EMBED_COLOUR,
        )
        embed.set_footer(text=f"ID: {ctx.author.id}", icon_url=ctx.author.avatar)
        message = await suggestion_channel.send(embed=embed)
        await ctx.send(embed=thanks)
        await message.add_reaction(suggestion_no)
        await message.add_reaction(suggestion_yes)

    @commands.command(
        aliases=["reportbug", "sendbug", "bugreport"], usage="`tp!bug bug`"
    )
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 10, commands.BucketType.user)
    async def bug(self, ctx, *, bug: str):
        """Report bugs that you run into
        If you can, paste the error code that might have been sent."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        thanks = discord.Embed(
            title=f"Thank you for contributing to the community {ctx.author.name}.",
            colour=EMBED_COLOUR,
        )

        bug_channel = self.bot.get_channel(791265212429762561)

        embed = discord.Embed(
            title=f"New Bug Submitted By {ctx.author.name}.",
            description=f"```py\n{bug}```",
            colour=EMBED_COLOUR,
        )
        embed.set_footer(
            text=f"Bug reported by: {ctx.author.id}", icon_url=ctx.author.avatar
        )
        await bug_channel.send(embed=embed)
        await ctx.send(embed=thanks)

    @permissions.dynamic_ownerbypass_cooldown(1, 10, commands.BucketType.user)
    @commands.command(usage="`tp!colors`")
    @commands.bot_has_permissions(embed_links=True)
    async def colors(self, ctx):
        """Tells you all the colors this bot can make"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        with open("colors.json", "r") as f:
            data = json.load(f)
        colors = "\n".join(data.keys())
        embed = discord.Embed(
            title="I can give / make the following colours...",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
        )
        embed.add_field(
            name="\u200b",
            value=f"""**{colors}**\nIf you feel there should be more, DM me, our devs will see what you say.
You can give yourself the colors by doing `tp!colorme <color>`. \nExample: `tp!colorme red` \nIf you want to remove a color from yourself, do `tp!colorme` with no arguments.

**If theres no colors at all to begin with, run `tp!rainbow` and follow its instructions.**""",
        )
        await ctx.send(embed=embed)

    class Creamy(commands.RoleConverter):
        async def convert(self, ctx, argument):
            return await super().convert(ctx, argument.lower())

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(
        aliases=["colorme", "colourme", "color"], usage="`tp!colorme color`"
    )
    async def give_color(self, ctx, *, role: Creamy = None):
        """Allows users to give themselves a color role. do `tp!colors` to see what you can add to yourself.
        If there arent any colors, do `tp!rainbow` to create the roles"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        with open("colors.json", "r") as f:
            data = json.load(f)
            color_roles = [discord.utils.get(ctx.guild.roles, name=x) for x in data]
            if role is None:
                for x in color_roles:
                    if x in ctx.author.roles:
                        await ctx.author.remove_roles(x)
                await ctx.send(f"Your color has been removed.")
            elif role in color_roles:
                for x in color_roles:
                    if x in ctx.author.roles:
                        await ctx.send(
                            "You already have a color role. Please remove your previous color role by doing `tp!colorme` first!"
                        )
                        return
                await ctx.author.add_roles(role)
                await ctx.send(
                    f"Alright, {role} was given.\n**Reminder, if you want to remove your colors, just run `tp!colorme` just like that to remove them!**"
                )

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=["icon"], usage="`tp!icon`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def server_avatar_url(self, ctx):
        """Get the current server icon"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if not ctx.guild.icon:
            return await ctx.send("This server does not have a icon...")
        embed = discord.Embed(
            title="Server Icon",
            colour=EMBED_COLOUR,
            description=f"{ctx.guild.name}'s icon is:",
        )
        embed.set_image(url=ctx.guild.icon)
        await ctx.send(embed=embed)

    @commands.command(usage="`tp!banner`")
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def banner(self, ctx):
        """Get the current banner image"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if not ctx.guild.banner:
            return await ctx.send("This server does not have a banner...")
        await ctx.send(f"Banner of **{ctx.guild.name}**\n{ctx.guild.banner}")

    @permissions.dynamic_ownerbypass_cooldown(1, 10, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(help="Check if a user has voted or not!")
    async def checkvote(self, ctx, user: Union[discord.Member, discord.User] = None):
        """Check if you or someone else has voted for AGB in the last 12 hours"""
        user = user or ctx.author
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"https://top.gg/api/bots/723726581864071178/check?userId={user.id}",
                headers={"Authorization": TOP_GG_TOKEN},
            ) as r:
                idkwhattocallthis = await r.json()
                if idkwhattocallthis["voted"] == 1:
                    voted = True
                else:
                    voted = False
                if voted:
                    title = "Poggers!"
                    description = "You have voted in the last **12** hours."
                    embed = success_embed(title, description)
                else:
                    title = "Not pog!"
                    description = f"You haven't voted in the last **12** hours.\nClick **[here]({Vote})** to vote!"
                    embed = error_embed(title, description)
                return await ctx.send(embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(usage="`tp!roleinfo role`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Get information about a role"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        list_members_with_the_role = [
            member.mention for member in ctx.guild.members if role in member.roles
        ]
        if len(list_members_with_the_role) == 0:
            list_members_with_the_role = "None"
        if len(list_members_with_the_role) > 40:
            list_members_with_the_role = "Too many members to list"
        else:
            list_members_with_the_role = ", ".join(list_members_with_the_role)
        perms = ", ".join(
            [
                f"{p.capitalize()}".replace("_", " ")
                for p, value in role.permissions
                if value is True
            ]
        )
        if "administrator" in perms:
            perms = "All of them lol"
        embed = discord.Embed(title=f"**{role.name}**", color=role.colour)
        embed.add_field(
            name="Created",
            value=role.created_at.strftime("%d %b %Y %H:%M"),
            inline=True,
        )
        embed.add_field(name="Color", value=str(role.colour), inline=True)
        embed.add_field(name="Members", value=f"{len(role.members)}", inline=True)
        embed.add_field(name="Who all has this role", value=list_members_with_the_role)
        if int(role.permissions.value) == 0:
            embed.add_field(
                name="Permissions", value="No permissions granted.", inline=False
            )
        else:
            embed.add_field(name="Permissions", value=f"{perms}", inline=False)
        embed.add_field(name="Mentionable", value=role.mentionable, inline=True)
        embed.add_field(name="Hoist", value=role.hoist, inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        embed.add_field(name="Managed", value=role.managed, inline=True)
        embed.add_field(name="Mention", value=f"{role.mention}", inline=True)
        embed.add_field(
            name="Created",
            value=role.created_at.strftime("%d %b %Y %H:%M"),
            inline=True,
        )
        embed.set_footer(text=f"{role.__hash__()}")
        await ctx.send(embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(alias=["ms"], usage="`tp!massrole role`", hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def massrole(self, ctx, *, role: discord.Role):
        """Mass give a role to all users in the server (Ignores bots)"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        added = 0
        if role.is_default():
            return await ctx.send(f"Cant give a default role to users! {role.mention}")
        if role.position > ctx.author.top_role.position:
            return await ctx.send(
                f"You cant give a role that is higher than your top role! {role.mention}"
            )
        async with ctx.channel.typing():
            msg_1 = await ctx.send("Working...")
            for member in ctx.guild.members:
                if not member.bot:
                    if role not in member.roles:
                        await member.add_roles(role)
                        added += 1
            await msg_1.edit(
                content=f"**{role.name}** role was given to {added} users in the server!"
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(alias=["msr"], usage="`tp!massrole_remove role`", hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def massrole_remove(self, ctx, *, role: discord.Role):
        """Mass removes a role from everyone in the server (Doesn't ignore bots)"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        removed = 0
        if role.is_default():
            return await ctx.send(f"Cant remove a default role from all users!")
        if role.position > ctx.author.top_role.position:
            return await ctx.send(
                f"You cant remove a role that is higher than your top role!"
            )
        async with ctx.channel.typing():
            msg_1 = await ctx.send("Working...")
            for member in ctx.guild.members:
                if role in member.roles:
                    await member.remove_roles(role)
                    removed += 1
            await msg_1.edit(
                content=f"**{role.name}** role was removed from {removed} users in this server!"
            )

    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=["serverinfo"], usage="`tp!serverinfo`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def server(self, ctx):
        """Check info about current server"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(
            title=f"{self.bot.user.name}",
            url=f"{Website}",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
        )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon)
        if ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner)

        embed.add_field(name="Server Name", value=f"`{ctx.guild.name}`", inline=True)
        embed.add_field(name="Server ID", value=f"`{ctx.guild.id}`", inline=True)
        embed.add_field(
            name="Bots", value=f"`{len([bot for bot in ctx.guild.members if bot.bot])}`"
        )
        if len(ctx.guild.text_channels) == 69:
            embed.add_field(
                name="Text channels",
                value=f"`{len(ctx.guild.text_channels)}` Nice",
                inline=True,
            )
        else:
            embed.add_field(
                name="Text channels",
                value=f"`{len(ctx.guild.text_channels)}`",
                inline=True,
            )
        embed.add_field(
            name="Voice channels",
            value=f"`{len(ctx.guild.voice_channels)}`",
            inline=True,
        )
        embed.add_field(
            name="Server on shard", value=f"`{ctx.guild.shard_id}`", inline=True
        )
        embed.add_field(
            name="Members", value=f"`{ctx.guild.member_count}`", inline=True
        )
        if len(ctx.guild.roles) == 69:
            embed.add_field(
                name="Roles", value=(f"`{len(ctx.guild.roles)}` Nice"), inline=True
            )
        else:
            embed.add_field(
                name="Roles", value=(f"`{len(ctx.guild.roles)}`"), inline=True
            )
        embed.add_field(
            name="Emoji Count", value=f"`{len(ctx.guild.emojis)}`", inline=True
        )
        embed.add_field(
            name="Emoji Limit", value=f"`{ctx.guild.emoji_limit}` Emojis", inline=True
        )
        embed.add_field(
            name="Filesize Limit",
            value=f"`{str(default.bytesto(ctx.guild.filesize_limit, 'm'))}` mb",
        )
        embed.add_field(
            name="Bitrate Limit",
            value=f"`{str(ctx.guild.bitrate_limit / 1000).split('.', 1)[0]}` Kbps",
        )
        embed.add_field(
            name="Security Level",
            value=f"`{ctx.guild.verification_level}`",
            inline=True,
        )
        try:
            embed.add_field(
                name="Owner/ID",
                value=f"**Name**:`{ctx.guild.owner}`\n**ID**:`{ctx.guild.owner.id}`",
                inline=False,
            )
        except Exception:
            embed.add_field(
                name="Owner/ID",
                value=f"**Name**:`Unable to fetch.`\n**ID**:`Unable to fetch.`",
                inline=False,
            )
        time_guild_existed = discord.utils.utcnow() - ctx.guild.created_at
        embed.add_field(
            name="Created",
            value=f"`{ctx.guild.created_at:%b %d, %Y - %H:%M:%S}`\nThat was `{default.commify(time_guild_existed.days)}` days ago!",
            inline=True,
        )
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
        await ctx.send(embed=embed)

    @app_commands.checks.cooldown(2, 3, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command()
    async def userinfo(
        self, interaction, user: discord.User = None, ephemeral: bool = True
    ):
        """Get user info on anyone in Discord

        Args:
            user (discord.User, optional): The user you want to get info on. Defaults to None.
            ephemeral (bool, optional): Weather to set the message as only visible to you or not. Defaults to True.

        """
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        chunked = []
        for guild in self.bot.guilds:
            if guild.chunked:
                chunked.append(guild)
        discord_version = discord.__version__
        user = user or interaction.user

        hs_class = (
            str(user.public_flags.all())
            .replace("[<UserFlags.", "")
            .replace(">]", "")
            .replace(":", "")
            .replace(">", "")
            .title()
        )
        hs_class = "".join([i for i in hs_class if not i.isdigit()])
        hs_final = (
            hs_class.replace(",", "")
            .replace(" <Userflags.Early", "")
            .replace("Supporter", "")
        )

        es_brilliance = (
            str(user.public_flags.all())
            .replace("[<UserFlags.", "")
            .replace("hypesquad_brilliance", "")
            .replace("[", "")
            .replace(":", "")
            .replace(">,", "")
            .replace("<", "")
            .replace("UserFlags.", "")
            .replace(">]", "")
            .replace("_", " ")
            .title()
        )
        es_brilliance = "".join([i for i in es_brilliance if not i.isdigit()])

        def houseCheck():
            if hs_final.strip() == "Hypesquad Balance":
                return f"{emojis.hs_balance}"
            elif hs_final.strip() == "Hypesquad Brilliance":
                return f"{emojis.hs_brilliance}"
            elif hs_final.strip() == "Hypesquad Bravery":
                return f"{emojis.hs_bravery}"
            else:
                return ""

        def earlySupporter():
            if es_brilliance.strip() == "Early Supporter":
                return f"{emojis.early_supporter}"
            else:
                return ""

        def boosterCheck():
            if user.premium_since is not None:
                return f"{emojis.nitro_booster}"
            else:
                return ""

        banner = await self.bot.fetch_user(user.id)
        if user.bot:
            return await interaction.followup.send(
                "Bots don't have any *useful* information!", ephemeral=True
            )

        embed = discord.Embed()
        embed.title = f"{self.bot.user.name}"
        embed.description = f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) "
        embed.url = f"{Website}"
        embed.add_field(name="User", value=f"`{user}`", inline=True)
        try:
            embed.add_field(
                name="Badges",
                value=f"{embed_space}{houseCheck()}{earlySupporter()}{boosterCheck()}",
                inline=True,
            )
        except Exception:
            pass

        if isinstance(user, discord.Member):
            if user.nick is not None:
                embed.add_field(name="Nickname", value=f"`{user.nick}`", inline=True)

        embed.add_field(
            name="Account created",
            value=f"`{user.created_at:%x\n%b %d (%a), %Y - %H:%M:%S}`\nThat was `{default.commify((discord.utils.utcnow() - user.created_at).days)}` days ago!",
            inline=False,
        )
        if len(chunked) == len(self.bot.guilds):
            embed.add_field(
                name="Mutual Servers",
                value=f"`{len(user.mutual_guilds)} Servers`",
                inline=False,
            )
        else:
            if len(user.mutual_guilds) == 1:
                embed.add_field(
                    name="Mutual Servers",
                    value=f"`1 Server`",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="Mutual Servers",
                    value=f"`{len(user.mutual_guilds)} Servers`\n`(Can be innacurate, requires all servers to be cached)`",
                    inline=True,
                )

        embed.set_thumbnail(url=user.avatar)
        if isinstance(user, discord.Member):
            embed.colour = user.color
            embed.add_field(
                name="Joined Server",
                value=f"`{user.joined_at:%b %d, %Y - %H:%M:%S}`\nThat was `{default.commify((discord.utils.utcnow() - user.joined_at).days)}` days ago!",
                inline=False,
            )

            roles = [x.name for x in user.roles if x.name != "@everyone"]
            if len(user.roles) > 20:
                roles = roles[:20]
                print(roles)
                roles.append("...")
                embed.add_field(
                    name=f"Roles[{len(roles)}]",
                    value=f"{', '.join(roles)}",
                    inline=True,
                )

            if banner.banner:
                try:
                    embed.set_image(url=banner.banner)
                except Exception:
                    pass
                else:
                    pass
        embed.set_footer(
            text=f"lunardev.group | Discord.py {discord_version} | Python 3.9.5"
        )
        await interaction.followup.send(
            content=f"Basic info about **`{user.id} / {user.name}`**", embed=embed
        )

    @app_commands.command()
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def ask(self, interaction, *, question: str, ephemeral: bool = True):
        """Ask a general question

        Args:
            question (str): the question you want answered
            ephemeral (bool, optional): Weather to make the result of the command visable to only you or not. Defaults to True.
        """
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        api_key = config.WolframAlpha
        url = "http://api.wolframalpha.com/v2/query?"
        query = question
        payload = {"input": query, "appid": api_key}
        headers = {"user-agent": "AGB"}
        async with self.session.get(url, params=payload, headers=headers) as r:
            result = await r.text()
        root = ET.fromstring(result)
        a = []
        for pt in root.findall(".//plaintext"):
            if pt.text:
                a.append(pt.text.capitalize())
        if len(a) < 1:
            message = "There is as yet insufficient data for a meaningful answer."
        else:
            message = "\n".join(a[0:3])
            if "Current geoip location" in message:
                message = "There is as yet insufficient data for a meaningful answer."

        await interaction.followup.send(default.box(message))

    @app_commands.command()
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def image(self, interaction, *, thing: str, ephemeral: bool = True):
        """Get an image from wolfram Alpha

        Args:
            thing (str): The thing you want an image of
            ephemeral (bool, optional): Weather to make the result of the command visable to only you or not. Defaults to True.
        """
        api_key = config.WolframAlpha
        if not api_key:
            return await interaction.followup.send(
                "No API key set for Wolfram Alpha. Get one at http://products.wolframalpha.com/api/"
            )
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        width = 500
        font_size = 15
        layout = "divider"
        background = "193555"
        foreground = "white"
        units = "metric"
        query = " ".join(thing)
        query = urllib.parse.quote(query)
        url = f"http://api.wolframalpha.com/v1/simple?appid={api_key}&i={query}%3F&width={width}&fontsize={font_size}&layout={layout}&background={background}&foreground={foreground}&units={units}&ip=127.0.0.1"

        async with self.session.request("GET", url) as r:
            img = await r.content.read()
            if len(img) == 43:
                # img = b'Wolfram|Alpha did not understand your input'
                return await interaction.followup.send(
                    "There is as yet insufficient data for a meaningful answer."
                )
            wolfram_img = BytesIO(img)
            try:
                await interaction.followup.send(
                    file=discord.File(wolfram_img, f"wolfram{interaction.user.id}.gif")
                )
            except Exception as e:
                await interaction.followup.send(f"Oops, there was a problem: {e}")

    @app_commands.command()
    async def solve(self, interaction, *, query: str, ephemeral: bool = True):
        """Solve any math problem

        Args:
            query (str): The math question you want solved
            ephemeral (bool, optional): Weather to make the result of the command visable to only you or not. Defaults to True.
        """
        api_key = config.WolframAlpha
        url = f"http://api.wolframalpha.com/v2/query"
        params = {
            "appid": api_key,
            "input": query,
            "podstate": "Step-by-step solution",
            "format": "plaintext",
        }
        msg = ""
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        async with self.session.request("GET", url, params=params) as r:
            text = await r.content.read()
            root = ET.fromstring(text)
            for pod in root.findall(".//pod"):
                if pod.attrib["title"] == "Number line":
                    continue
                msg += f"{pod.attrib['title']}\n"
                for pt in pod.findall(".//plaintext"):
                    if pt.text:
                        strip = pt.text.replace(" | ", " ").replace("| ", " ")
                        msg += f"- {strip}\n\n"
            if len(msg) < 1:
                msg = "There is as yet insufficient data for a meaningful answer."
            for text in default.pagify(msg):
                await interaction.followup.send(default.box(text))

    #######Baby Shaking Zone Media Only Channel#########

    @commands.Cog.listener(name="on_message")
    async def onlymedia(self, message):
        if (
            message.channel.id in [755722577279713281, 780157565010313258]
            and not message.attachments
        ):
            await message.delete()

    async def cog_unload(self):
        self.bot.loop.create_task(self.session.close())


async def setup(bot):
    await bot.add_cog(DiscordCmds(bot))
