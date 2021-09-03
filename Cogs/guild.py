import asyncio
import json
from datetime import datetime
from io import BytesIO
from typing import Union
import os

import aiohttp
import discord
from discord.ext import commands
from index import (EMBED_COLOUR, TOP_GG_TOKEN, Vote, Website, config, delay,
                   embed_space, emojis, suggestion_no, suggestion_yes)
from utils import default, permissions

from .Utils import error_embed, success_embed


class DiscordCmds(commands.Cog, name='discord'):
    """Server related things :D"""

    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")
        self.bot.sniped_messages = {}
        self.bot.edit_sniped_messages = {}

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if "nigger" in message.content.lower():
            return
        if message.author.bot:
            return
        try:
            self.bot.sniped_messages[message.guild.id, message.channel.id] = (
                message.content, message.author, message.channel.name,
                message.created_at, message.attachments)
        except:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        bad_words = ["nigger"]
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
                    before.channel.name
                )
            except AttributeError:
                pass

    @commands.command(aliases=['s'], usage="`tp!s`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def snipe(self, ctx):
        """Snipe recently deleted messages to see what someone said."""
        try:
            contents, author, channel_name, time, attachments = self.bot.sniped_messages[
                ctx.guild.id, ctx.channel.id]

            files = ""
            for file in attachments:
                files += f"[{file.filename}]({file.proxy_url})" + "\n"
            embed = discord.Embed(title=f"{self.bot.user.name}", url=f"{Website}",
                                  description=contents, color=EMBED_COLOUR, timestamp=time)
            embed.set_author(
                name=f"{author.name}#{author.discriminator}",
                icon_url=author.avatar_url)
            embed.add_field(
                name="Attachments",
                value=files[:-1] if len(attachments) != 0 else "None"
            )
            embed.set_footer(text=f"Deleted in #{channel_name}")

            await ctx.send(embed=embed)
        except:
            await ctx.send("Nothing has been recently deleted.")

    @commands.command(aliases=['es'], usage="`tp!es`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def editsnipe(self, ctx):
        """Snipe edited messages to see what the message said before."""
        try:
            before_content, after_content, author, channel_name = self.bot.edit_sniped_messages[
                ctx.guild.id, ctx.channel.id]

            embed = discord.Embed(title=f"{self.bot.user.name}", url=f"{Website}",
                                  description=f"**Before:**\n{before_content}\n\n**After:**\n{after_content}", color=EMBED_COLOUR)
            embed.set_author(
                name=f"{author.name}#{author.discriminator}", icon_url=author.avatar_url)
            embed.set_footer(text=f"Edited in #{channel_name}")
            embed.add_field(
                name="‎‎‎‎‎‎", value=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})", inline=False)

            await ctx.send(embed=embed)
        except:
            await ctx.send("Nothing has been recently edited.")
# thanks again nirlep for this

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
#                if back.endswith('.'):
#                    back = back[:-1]
#                back += '!'
#                await message.channel.send(f"Hi, {back} I'm {self.bot.user.name}.".format(back=back),
#                               allowed_mentions=discord.AllowedMentions(
#                               everyone=False, roles=False, users=False))
#            except (discord.HTTPException, discord.Forbidden, ):
#                pass

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=['av'], usage="`tp!av @user`")
    @commands.bot_has_permissions(embed_links=True)
    async def avatar(self, ctx, *,  user: Union[discord.User, discord.Member] = None):
        """Get someones avatar"""
        user = user or ctx.author
        au = "av" + (".gif" if str(user.avatar_url).split("?")
                     [0].endswith(".gif") else ".png")
        embed = discord.Embed(
            title="User Icon",
            colour=EMBED_COLOUR,
            description=f"{user}'s avatar is:"
        )
        embed.set_image(url=user.avatar_url_as(size=1024))
        # await user.avatar_url.save(au)
        # await ctx.reply(file=discord.File(open(au, "rb"), au))
        await ctx.send(embed=embed)
        # os.remove(au)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @permissions.has_permissions(manage_roles=True)
    @commands.command(usage="`tp!roles`")
    @commands.bot_has_permissions(attach_files=True)
    @commands.guild_only()
    async def roles(self, ctx):
        """Get all roles in current server """

        allroles = ""

        for num, role in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
            allroles += f"[{str(num).zfill(2)}] {role.id}\t{role.name}\t[ Users: {len(role.members)} ]\r\n"

        data = BytesIO(allroles.encode('utf-8'))
        await ctx.reply(content=f"Roles in **{ctx.guild.name}**", file=discord.File(data, filename=f"{default.timetext('Roles')}"))

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!joinedat @user`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def joinedat(self, ctx, *, user: discord.Member = None):
        """Check when a user joined the current server."""
        user = user or ctx.author
        embed = discord.Embed(
            title=f"{self.bot.user.name}", description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            url=f"{Website}", colour=user.top_role.colour.value)
        embed.set_thumbnail(url=user.avatar_url)
        embed.description = f"**{user}** joined **`{user.joined_at:%b %d, %Y - %H:%M:%S}`**\nThat was **`{(datetime.utcnow() - user.joined_at).days}`** days ago!"
        await ctx.reply(embed=embed)

    @commands.command(usage='`tp!mods`')
    @commands.guild_only()
    async def mods(self, ctx):
        """Check which mods are online on current guild"""
        message = ""
        all_status = {
            "online": {"users": [], "emoji": "🟢"},
            "idle": {"users": [], "emoji": "🟡"},
            "dnd": {"users": [], "emoji": "🔴"},
            "offline": {"users": [], "emoji": "⚫"}
        }

        for user in ctx.guild.members:
            user_perm = ctx.channel.permissions_for(user)
            if user_perm.kick_members or user_perm.ban_members:
                if not user.bot:
                    all_status[str(user.status)]["users"].append(f"**{user}**")

        for g in all_status:
            if all_status[g]["users"]:
                message += f"{all_status[g]['emoji']} {', '.join(all_status[g]['users'])}\n"

        await ctx.send(f"Mods in **{ctx.guild.name}**\n{message}")

    @commands.command(usage="`tp!firstmessage`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def firstmessage(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Provide a link to the first message in current or provided channel."""
        if channel is None:
            channel = ctx.channel
        try:
            message: discord.Message = (
                await channel.history(limit=1, oldest_first=True).flatten()
            )[0]
        except (discord.Forbidden, discord.HTTPException):
            print(
                f"{default.date()} | Unable to read message history for {channel.id}")
            await ctx.reply("Unable to read message history for that channel")
            return

        em = discord.Embed(
            description=f"[First Message in {channel.mention}]({message.jump_url})")
        em.set_author(name=message.author.display_name,
                      icon_url=message.author.avatar_url)

        await ctx.reply(embed=em)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=['serverinfo'], usage="`tp!serverinfo`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def server(self, ctx):
        """Check info about current server"""

        embed = discord.Embed(title=f"{self.bot.user.name}", url=f"{Website}",
                              description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                              color=ctx.author.color, timestamp=ctx.message.created_at)

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon_url)
        if ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner_url_as(format="png"))

        embed.add_field(name="Server Name", value=ctx.guild.name, inline=True)
        embed.add_field(name="Server ID", value=ctx.guild.id, inline=True)
        embed.add_field(name="Bots", value=len(
            [bot for bot in ctx.guild.members if bot.bot]))
        embed.add_field(name="Text channels", value=len(
            ctx.guild.text_channels), inline=True)
        embed.add_field(name="Voice channels", value=len(
            ctx.guild.voice_channels), inline=True)
        embed.add_field(name="Server on shard",
                        value=ctx.guild.shard_id, inline=True)
        embed.add_field(
            name="Members", value=ctx.guild.member_count, inline=True)
        if len(ctx.guild.roles) == 69:
            embed.add_field(name="Roles", value=(
                f"{len(ctx.guild.roles)} Nice"), inline=True)
        else:
            embed.add_field(name="Roles", value=(
                f"{len(ctx.guild.roles)}"), inline=True)
        embed.add_field(name="Emoji Limit",
                        value=f"{ctx.guild.emoji_limit} Emojis", inline=True)
        embed.add_field(name="Filesize Limit",
                        value=f"{ctx.guild.filesize_limit} Bytes")
        embed.add_field(name="Bitrate Limit",
                        value=f"{str(ctx.guild.bitrate_limit / 1000).split('.', 1)[0]} Kbps")
        embed.add_field(name="Security Level",
                        value=ctx.guild.verification_level, inline=True)
        embed.add_field(
            name="Owner/ID", value=f"**Name**:{ctx.guild.owner} | **ID**:{ctx.guild.owner.id}", inline=False)
        embed.add_field(name="Region", value=ctx.guild.region, inline=True)
        time_guild_existed = datetime.utcnow() - ctx.guild.created_at
        embed.add_field(name="Created", value="{:%b %d, %Y - %H:%M:%S}\nThat was {} days ago!".format(
            ctx.guild.created_at, time_guild_existed.days), inline=True)
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=['channelinfo'], usage="`tp!channelinfo`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def channelstats(self, ctx):
        """Gets stats for the current channel you're in."""
        channel = ctx.channel

        embed = discord.Embed(
            title=f"Stats for **{channel.name}**",
            description=f"{'Category: {}'.format(channel.category.name) if channel.category else 'This channel is not in a category'}",
            color=EMBED_COLOUR,
        )
        embed.add_field(name="Channel Guild",
                        value=ctx.guild.name, inline=False)
        embed.add_field(name="Channel Id", value=channel.id, inline=False)
        embed.add_field(
            name="Channel Topic",
            value=f"{channel.topic if channel.topic else 'No topic.'}",
            inline=False,
        )
        embed.add_field(name="Channel Position",
                        value=channel.position, inline=False)
        embed.add_field(
            name="Channel Slowmode Delay", value=channel.slowmode_delay, inline=False
        )
        embed.add_field(name="Channel is nsfw?",
                        value=channel.is_nsfw(), inline=False)
        embed.add_field(name="Channel is news?",
                        value=channel.is_news(), inline=False)
        embed.add_field(
            name="Channel Creation Time", value=channel.created_at, inline=False
        )
        embed.add_field(
            name="Channel Permissions Synced",
            value=channel.permissions_synced,
            inline=False,
        )
        embed.add_field(name="Channel Hash", value=hash(channel), inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=['feedback', 'suggestion'], usage="`tp!suggest <suggestion>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def suggest(self, ctx, *, suggestion: str):
        """Suggest things this bot should have or not have."""
        thanks = discord.Embed(
            title=f"Thank you for contributing to the community {ctx.author.name}.",
            colour=EMBED_COLOUR)
        suggestion_channel = self.bot.get_channel(773904927579701310)
        embed = discord.Embed(
            title=f"New suggestion by {ctx.author}.", description=suggestion, colour=EMBED_COLOUR)
        embed.set_footer(text=f"ID: {ctx.author.id}",
                         icon_url=ctx.author.avatar_url)
        message = await suggestion_channel.send(embed=embed)
        await ctx.reply(embed=thanks)
        await message.add_reaction(suggestion_no)
        await message.add_reaction(suggestion_yes)

    @commands.command(aliases=["reportbug", "sendbug", "bugreport"], usage="`tp!bug <bug>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bug(self, ctx, *, bug: str):
        """Report bugs that you run into
        If you can, paste the error code that might have been sent."""
        thanks = discord.Embed(
            title=f"Thank you for contributing to the community {ctx.author.name}.",
            colour=EMBED_COLOUR)

        bug_channel = self.bot.get_channel(791265212429762561)

        embed = discord.Embed(
            title=f"New Bug Submitted By {ctx.author.name}.", description=f"```py\n{bug}```", colour=EMBED_COLOUR)
        embed.set_footer(
            text=f"Bug reported by: {ctx.author.id}", icon_url=ctx.author.avatar_url)
        message = await bug_channel.send(embed=embed)
        await ctx.reply(embed=thanks)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(usage="`tp!colors`")
    @commands.bot_has_permissions(embed_links=True)
    async def colors(self, ctx):
        """Tells you all the colors this bot can make"""
        with open('colors.json', 'r') as f:
            data = json.load(f)
        colors = '\n'.join(data.keys())
        embed = discord.Embed(title="I can give / make the following colours...",
                              description=f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})")
        embed.add_field(name="\u200b", value=f"""**{colors}**\nIf you feel there should be more, DM me, our devs will see what you say.
You can give yourself the colors by doing `tp!colorme <color>`. \nExample: `tp!colorme red` \nIf you want to remove a color from yourself, do `tp!colorme` with no arguments.

**If theres no colors at all to begin with, run `tp!rainbow` and follow its instructions.**""")
        await ctx.send(embed=embed)

    class Creamy(commands.RoleConverter):
        async def convert(self, ctx, argument):
            return await super().convert(ctx, argument.lower())

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=['colorme', 'colourme', 'color'], usage="`tp!colorme <color>`")
    async def give_color(self, ctx, *, role: Creamy = None):
        """Allows users to give themselves a color role. do `tp!colors` to see what you can add to Yourself
            If there arent any colors, do `tp!rainbow` to create the roles"""
        with open('colors.json', 'r') as f:
            data = json.load(f)
            color_roles = [discord.utils.get(
                ctx.guild.roles, name=x) for x in data]
            if role is None:
                m = await ctx.send("Okie, starting to remove your roles..")
                for x in color_roles:
                    if x in ctx.author.roles:
                        await asyncio.sleep(0.5)
                        await ctx.author.remove_roles(x)
                await m.edit(content="Role(s) removed.", delete_after=delay)
            elif role in color_roles:
                await ctx.author.add_roles(role)
                await ctx.reply(f"Alright, {role} was given.\n**Reminder, if you want to remove your colors, just run `tp!colorme` just like that to remove them!**")

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=['icon'], usage="`tp!icon`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def server_avatar(self, ctx):
        """Get the current server icon"""

        if not ctx.guild.icon:
            return await ctx.reply("This server does not have a icon...")
        embed = discord.Embed(
            title="Server Icon",
            colour=EMBED_COLOUR,
            description=f"{ctx.guild.name}'s icon is:"
        )
        embed.set_image(url=ctx.guild.icon_url_as(size=1024))
        au = "av" + (".gif" if str(ctx.guild.icon_url).split("?")
                     [0].endswith(".gif") else ".png")
        # await ctx.guild.icon_url.save(au)
        # await ctx.reply(file=discord.File(open(au, "rb"), au))
        await ctx.send(embed=embed)
        # os.remove(au)

    @commands.command(usage="`tp!banner`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def banner(self, ctx):
        """Get the current banner image """

        if not ctx.guild.banner:
            return await ctx.reply("This server does not have a banner...")
        await ctx.reply(f"Banner of **{ctx.guild.name}**\n{ctx.guild.banner_url_as(format='png')}")

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(help="Check if a user has voted or not!")
    async def checkvote(self, ctx: commands.Context, user: Union[discord.Member, discord.User] = None):
        """Check if you or someone else has voted for AGB in the last 12 hours"""
        user = user or ctx.author
        async with aiohttp.ClientSession() as s:
            async with s.get(f'https://top.gg/api/bots/723726581864071178/check?userId={user.id}', headers={'Authorization': TOP_GG_TOKEN}) as r:
                pain = await r.json()
                if pain['voted'] == 1:
                    voted = True
                else:
                    voted = False
                if voted == True:
                    title = "Poggers!"
                    description = "You have voted in the last **12** hours."
                    embed = success_embed(title, description)
                else:
                    title = "Not pog!"
                    description = f"You haven't voted in the last **12** hours.\nClick **[here]({Vote})** to vote!"
                    embed = error_embed(title, description)
                return await ctx.reply(embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!roleinfo <role>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Get information about a role"""
        perms = "\n".join([f"- {p}".replace("_", " ")
                          for p, value in role.permissions if value is True])
        if "administrator" in perms:
            perms = "All of them lol"
        embed = discord.Embed(title=f"**{role.name}**", color=role.colour)
        embed.add_field(name="ID", value=role.id)
        embed.add_field(name="Created", value=role.created_at.strftime(
            "%d %b %Y %H:%M"))
        embed.add_field(name="Color", value=str(role.colour))
        embed.add_field(name="Members", value=f"{len(role.members)}")
        embed.add_field(name="Mentionable", value=role.mentionable)
        embed.add_field(name="Hoist", value=role.hoist)
        embed.add_field(name="Position", value=role.position)
        embed.add_field(name="Managed", value=role.managed)
        if int(role.permissions.value) == 0:
            embed.add_field(name="Permissions",
                            value='No permissions granted.')
        else:
            embed.add_field(name="Permissions", value=perms, inline=True)
        embed.add_field(name="Mention", value=f"{role.mention}")
        embed.add_field(name="Created", value=role.created_at.strftime(
            "%d %b %Y %H:%M"))
        await ctx.send(embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!massrole <role>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.check(permissions.is_owner)
    async def massrole(self, ctx, *, role: discord.Role):
        """Mass give a role to all users in the server"""
        if role.is_default():
            return await ctx.reply(f"Cant give a default role to users! {role.mention}")
        if role.position > ctx.author.top_role.position:
            return await ctx.reply(f"You cant give a role that is higher than your top role! {role.mention}")
        async with ctx.channel.typing():
            msg_1 = await ctx.send("Working...")
            for member in ctx.guild.members:
                if member.bot:
                    continue
                await member.add_roles(role)
            await msg_1.edit(content=f"**{role.name}** role was given to all users in the server!")

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=['userinfo', 'ui', 'mi'], usage="`tp!ui @user`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def user(self, ctx, user: Union[discord.Member, discord.User] = None):
        """Get user information"""
        usr = user or ctx.author
        avatarUrl = str(usr.avatar_url)

        hs_class = str(usr.public_flags.all()).replace('[<UserFlags.', '').replace(
            '>]', '').replace('_', ' ').replace(':', '').replace('>', '').title()
        hs_class = ''.join([i for i in hs_class if not i.isdigit()])
        hs_final = hs_class.replace(",", "").replace(
            " <Userflags.Early", "").replace("Supporter", "")

        es_brilliance = str(usr.public_flags.all()).replace('[<UserFlags.', '').replace('hypesquad_brilliance', '').replace(
            '[', '').replace(':', '').replace('>,', '').replace('<', '').replace('UserFlags.', '').replace('>]', '').replace('_', ' ').title()
        es_brilliance = ''.join([i for i in es_brilliance if not i.isdigit()])

        def houseCheck():
            if hs_final.strip() == 'Hypesquad Balance':
                return f"{emojis.hs_balance}"
            elif hs_final.strip() == 'Hypesquad Brilliance':
                return f"{emojis.hs_brilliance}"
            elif hs_final.strip() == 'Hypsquad Bravery':
                return f"{emojis.hs_bravery}"
            else:
                return ''

        def earlySupporter():
            if es_brilliance.strip() == 'Early Supporter':
                return f"{emojis.early_supporter}"
            else:
                return ''

        def boosterCheck():
            if user.premium_since != None:
                return f"{emojis.nitro_booster}"
            else:
                return ''

        embed = discord.Embed()
        embed.title = f"{self.bot.user.name}"
        embed.description = f"[Add me]({config.Invite}) | [Join the server]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})"
        embed.url = f"{Website}"
        user = user or ctx.author
        embed.add_field(name="User", value=f"`{user}`", inline=True)
        try:
            embed.add_field(
                name="Badges", value=f"{embed_space}{houseCheck()}{earlySupporter()}{boosterCheck()}", inline=True)
        except:
            pass
        embed.add_field(name="Nickname", value=user.nick if hasattr(
            user, "nick") else "None", inline=True)
        embed.add_field(name="Account created",
                        value=f"`{user.created_at:%x\n%b %d (%a), %Y - %H:%M:%S}`\nThat was `{(datetime.utcnow() - user.created_at).days}` days ago!", inline=False)
        embed.set_thumbnail(url=user.avatar_url)
        if isinstance(user, discord.Member):
            embed.colour = user.color
            embed.add_field(
                name="Joined Server", value=f"`{user.joined_at:%b %d, %Y - %H:%M:%S}`\nThat was `{(datetime.utcnow() - user.joined_at).days}` days ago!", inline=False)
            # .join(
            # x.mention for x in user.roles[1:][::-1]) if user.roles else "None",
            role_list = [r.mention for r in usr.roles if r !=
                         ctx.guild.default_role]
            if len(role_list):
                embed.add_field(name="Roles", value=f", ".join(
                    role_list), inline=False)
            else:
                embed.add_field(name="Roles", value=f"None", inline=False)
        await ctx.reply(content=f"Basic info about **`{user.id} / {user.name}`**", embed=embed)

#        embed.add_field(name="Status", value=user.status, inline=True)
#        embed.add_field(name="Activity", value=user.activity)
#        if isinstance(user.activity, discord.Spotify):
#            embed.add_field(name="Listening To", value=user.activity.title)


#######Baby Shaking Zone Media Only Channel#########


    @commands.Cog.listener(name='on_message')
    async def onlymedia(self, message):
        if message.channel.id in [755722577279713281, 780157565010313258]:
            if not message.attachments:
                await message.delete()
####################################################

####anxiety zone prevent other people from talking in announcements####
    @commands.Cog.listener(name='on_message')
    async def OwnerOwnly(self, message):
        whitelist = [101118549958877184, 417052810161684511,
                     393996898945728523, 454421372911878145,
                     542572136112324629, 468373112841306112,
                     146151306216734720, 343048549744902144,
                     683530527239962627, 828858385113939969]
        if message.channel.id == 755722577049026562:
            if message.author.id not in whitelist:
                await message.delete()
########################################################################


def setup(bot):
    bot.add_cog(DiscordCmds(bot))
