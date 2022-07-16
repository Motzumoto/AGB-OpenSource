import random
from typing import List, Optional, Union
from random import choice
import sys

import aiohttp
import asyncio
import json
from discord.ext import commands

import discord

import aiohttp
from index import EMBED_COLOUR, config, cursor_n, mydb_n
from Manager.commandManager import cmd
from utils import permissions, default, imports
from utils.checks import voter_only
from Cogs.Utils import Translator

from utils.default import bold, inline


_ = Translator("Nsfw", __file__)

MY_GUILD_ID = discord.Object(975810661709922334)
owners = default.get("config.json").owners
config = imports.get("config.json")


class Nsfw(commands.Cog, name="nsfw", command_attrs=dict(nsfw=True)):
    """Spicy pictures"""

    def __init__(self, bot):
        self.bot = bot

        self.lunar_headers = {f"{config.lunarapi.header}": f"{config.lunarapi.token}"}
        for command in self.walk_commands():
            command.nsfw = True

    async def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def cog_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title="Error Caught!", color=0xFF0000, description=f"{error}"
        )

        embed.set_thumbnail(url=self.bot.user.avatar)

    @commands.hybrid_command()
    @voter_only()
    @commands.is_nsfw()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    @permissions.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(
        embed_links=True, manage_channels=True, manage_webhooks=True, attach_files=True
    )
    async def autopost(
        self, ctx, *, channel: discord.TextChannel, ephemeral: bool = False
    ):
        """Mention a channel to autopost hentai to. example: `tp!autopost #auto-nsfw`"""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        Server = self.bot.get_guild(755722576445046806)

        # check if the command was used as an interaction
        ephemeral = ctx.interaction is not None
        if not channel.is_nsfw():
            return await ctx.send(
                "That shit isn't NSFW - fuck that.", ephemeral=ephemeral
            )

        if channel.guild.member_count < 15:
            await ctx.send(
                "I'm sorry, but this server does not meet our requirements. Your server requires over 15 members.\nWe have this requirement to prevent spam and abuse.\nWhile you can't use this feature, you can still use all of AGB's NSFW commands which require a vote to be able to use all of them. You can vote for AGB's NSFW commands by using `tp!vote`. Thanks for understanding.",
                ephemeral=ephemeral,
            )
            return

        try:
            await Server.fetch_member(ctx.author.id)
        except Exception:
            await ctx.send(
                f"You are not in the support server. Please join the support server to use this command.\n{config.Server}"
            )
            return

        cursor_n.execute(
            f"SELECT hentaichannel FROM public.guilds WHERE guildId = '{ctx.guild.id}'"
        )
        res = cursor_n.fetchall()

        if not channel.mention:
            await ctx.send(
                "Please mention a channel for me to autopost to.", ephemeral=ephemeral
            )

        for row in res:
            if row[0] is None:
                cursor_n.execute(
                    f"UPDATE public.guilds SET hentaichannel = '{channel.id}' WHERE guildId = '{ctx.guild.id}'"
                )
                mydb_n.commit()
                # edit the channel permissions to allow the bot to post
                overwrites = channel.overwrites
                overwrites[ctx.guild.me] = discord.PermissionOverwrite(
                    send_messages=True,
                    manage_webhooks=True,
                    attach_files=True,
                    embed_links=True,
                    view_channel=True,
                )
                try:
                    await channel.edit(overwrites=overwrites)
                except Exception:
                    await ctx.send(
                        f"I don't have permission to edit {channel.mention} to make sure I can post there. The channel has been added to the database regardless, if I never post there, you will have to manually edit the channel permissions to allow me to post there.",
                        ephemeral=ephemeral,
                    )
                    return
                else:

                    await ctx.send(
                        f"{channel.mention} has been added to the database. I will start posting shortly!\nMake sure that the channel has no overrides that prevent me from posting!",
                        ephemeral=ephemeral,
                    )
            else:
                await ctx.send(
                    "whoops, guild already has a fuckin' channel my dude",
                    ephemeral=ephemeral,
                )

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    @voter_only()
    @commands.is_nsfw()
    @permissions.has_permissions(manage_channels=True)
    async def autopost_remove(self, ctx):
        """Remove the auto hentai posting channel."""
        if cmdEnabled := cmd(str(ctx.command.name).lower(), ctx.guild.id):
            return await ctx.send(":x: This command has been disabled!")

        # await ctx.send(f"This command is currently disabled because it is no
        # longer working (for now). Please join the support server to know what
        # is going on - {config.Server}")

        cursor_n.execute(
            f"SELECT hentaichannel FROM public.guilds WHERE guildId = '{ctx.guild.id}'"
        )
        res = cursor_n.fetchall()

        for row in res:
            if row[0] is None:
                await ctx.send("you don't have a fukin' channel idot.")
            else:
                cursor_n.execute(
                    f"UPDATE public.guilds SET hentaichannel = NULL WHERE guildId = '{ctx.guild.id}'"
                )
                await ctx.send(
                    "Alright, your auto posting channel has been removed from our database."
                )

                mydb_n.commit()

    @commands.hybrid_group()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def nsfw(self, ctx):
        """Hentai Commands"""

        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=(await self.get_hentai_img()))
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def ass(self, ctx):
        """Booty!"""
        url = await self.get_hentai_lunar("ass")
        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def panties(self, ctx):
        """Pantsu"""
        url = await self.get_hentai_lunar("panties")
        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def hentai(self, ctx):
        """Hentai"""

        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=(await self.get_hentai_img()))
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def holo(self, ctx):
        """holo live streamer porn"""

        url = await self.get_hentai_lunar("hololive")
        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def kemo(self, ctx):
        """kemonomimi; fox girls/cat girls/animal girls"""

        url = await self.get_hentai_lunar("neko")
        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def pwg(self, ctx):
        """Pussy wank gifs"""

        url = await self.get_hentai_lunar("panties")
        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def thighs(self, ctx):
        """thigh pictures"""

        url = await self.get_hentai_lunar("thighs")
        # try:
        #     cursor_n.execute(
        #         f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'"
        #     )
        #     udb = cursor_n.fetchall()

        #     usedCommands = ""
        #     if int(udb[0][1]) >= 0:
        #         usedCommands += f"{udb[0][1]}"
        # except:
        #     usedCommands = "0"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(text="lunardev.group")
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Nsfw(bot))
