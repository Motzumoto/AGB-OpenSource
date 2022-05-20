import random
from typing import List, Optional, Union
from random import choice
import sys
from utils.constants import (
    GOOD_EXTENSIONS,
    IMGUR_LINKS,
    MARTINE_API_BASE_URL,
    NOT_EMBED_DOMAINS,
    REDDIT_BASEURL,
    emoji,
)
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
        self.__version__ = "2.4.01"
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": (
                    f"Red-DiscordBot PredaCogs-Nsfw/{self.__version__} "
                    f"(Python/{'.'.join(map(str, sys.version_info[:3]))} aiohttp/{aiohttp.__version__})"
                )
            }
        )

        self.lunar_headers = {f"{config.lunarapi.header}": f"{config.lunarapi.token}"}
        for command in self.walk_commands():
            command.nsfw = True
        self.use_reddit_api = False

    async def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def cog_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title=f"Error Caught!", color=0xFF0000, description=f"{error}"
        )
        embed.set_thumbnail(url=self.bot.user.avatar)

    async def _get_imgs(self, subs: List[str] = None):
        """Get images from Reddit API."""
        tries = 0
        while tries < 5:
            sub = choice(subs)
            try:
                if self.use_reddit_api:
                    async with self.session.get(
                        REDDIT_BASEURL.format(sub=sub)
                    ) as reddit:
                        if reddit.status != 200:
                            return None, None
                        try:
                            data = await reddit.json(content_type=None)
                            content = data[0]["data"]["children"][0]["data"]
                            url = content["url"]
                            subr = content["subreddit"]
                        except (KeyError, ValueError, json.decoder.JSONDecodeError):
                            tries += 1
                            continue
                        if url.startswith(IMGUR_LINKS):
                            url = url + ".png"
                        elif url.endswith(".mp4"):
                            url = url[:-3] + "gif"
                        elif url.endswith(".gifv"):
                            url = url[:-1]
                        elif not url.endswith(GOOD_EXTENSIONS) and not url.startswith(
                            "https://gfycat.com"
                        ):
                            tries += 1
                            continue
                        return url, subr
                else:
                    async with self.session.get(
                        MARTINE_API_BASE_URL, params={"name": sub}
                    ) as resp:
                        if resp.status != 200:
                            tries += 1
                            continue
                        try:
                            data = await resp.json()
                            return (
                                data["data"]["image_url"],
                                data["data"]["subreddit"]["name"],
                            )
                        except (KeyError, json.JSONDecodeError):
                            tries += 1
                            continue
            except aiohttp.client_exceptions.ClientConnectionError:
                tries += 1
                continue

        return None, None

    async def _get_others_imgs(self, ctx: commands.Context, url: str = None):
        """Get images from all other images APIs."""
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    await self._api_errors_msg(ctx, error_code=resp.status)
                    return None
                try:
                    data = await resp.json(content_type=None)
                except json.decoder.JSONDecodeError as exception:
                    await self._api_errors_msg(ctx, error_code=exception)
                    return None
            data = dict(img=data)
            return data
        except aiohttp.client_exceptions.ClientConnectionError:
            await self._api_errors_msg(ctx, error_code="JSON decode failed")
            return None

    async def _api_errors_msg(self, ctx: commands.Context, error_code: int = None):
        """Error message when API calls fail."""
        return await ctx.send(
            _("Error when trying to contact image service, please try again later. ")
            + "(Code: {})".format(inline(str(error_code)))
        )

    async def _make_embed(self, ctx: commands.Context, subs: List[str], name: str):
        """Function to make the embed for all Reddit API images."""
        try:
            url, subr = await asyncio.wait_for(self._get_imgs(subs=subs), 5)
        except asyncio.TimeoutError:
            await ctx.send(
                "Failed to get an image. Please try again later. (Timeout error)"
            )
            return
        if not url:
            return

        if any(wrong in url for wrong in NOT_EMBED_DOMAINS):
            em = (
                _("Here is {name} gif ...")
                + " \N{EYES}\n\n"
                + _("Requested by {req} {emoji} • From {r}\n{url}")
            ).format(
                name=name,
                req=bold(ctx.author.name),
                emoji=emoji(),
                r=bold(f"r/{subr}"),
                url=url,
            )
        else:
            em = await self._embed(
                color=EMBED_COLOUR,
                title=(_("Here is {name} image ...") + " \N{EYES}").format(name=name),
                description=bold(
                    _("[Link if you don't see image]({url})").format(url=url),
                    escape_formatting=False,
                ),
                image=url,
                footer=_("Requested by {req} {emoji} • From r/{r}").format(
                    req=ctx.author.display_name, emoji=emoji(), r=subr
                ),
            )

        return em

    async def _make_embed_other(
        self, ctx: commands.Context, name: str, url: str, arg: str, source: str
    ):
        """Function to make the embed for all others APIs images."""
        try:
            data = await asyncio.wait_for(self._get_others_imgs(ctx, url=url), 5)
        except asyncio.TimeoutError:
            await ctx.send(
                "Failed to get an image. Please try again later. (Timeout error)"
            )
            return
        if not data:
            return
        em = await self._embed(
            color=EMBED_COLOUR,
            title=(_("Here is {name} image ...") + " \N{EYES}").format(name=name),
            description=bold(
                _("[Link if you don't see image]({url})").format(url=data["img"][arg]),
                escape_formatting=False,
            ),
            image=data["img"][arg],
            footer=_("Requested by {req} {emoji} • From {source}").format(
                req=ctx.author.display_name, emoji=emoji(), source=source
            ),
        )
        return em

    # async def _maybe_embed(
    #     self, ctx: commands.Context, embed: Union[discord.Embed, str]
    # ):
    #     """
    #     Function to choose if type of the message is an embed or not
    #     and if not send a simple message.
    #     """
    #     if ctx.interaction is None:
    #         if ctx.channel.is_nsfw():
    #             try:
    #                 if isinstance(embed, discord.Embed):
    #                     await ctx.send(embed=embed)
    #                 else:
    #                     await ctx.send(embed)
    #             except discord.HTTPException:
    #                 return
    #         else:
    #             raise commands.NSFWChannelRequired(ctx.channel)
    #     await ctx.send(embed=embed, ephemeral=True)

    async def _maybe_embed(
        self, ctx: commands.Context, embed: Union[discord.Embed, str]
    ):
        """
        Function to choose if type of the message is an embed or not
        and if not send a simple message.
        """
        try:
            if isinstance(embed, discord.Embed):
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed)
        except discord.HTTPException:
            return

    async def _send_msg(self, ctx: commands.Context, name: str, subs: List[str] = None):
        """Main function called in all Reddit API commands."""
        embed = await self._make_embed(ctx, subs, name)
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                return await self._maybe_embed(ctx, embed=embed)
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
        else:
            await ctx.send(embed=embed, ephemeral=True)

    async def _send_other_msg(
        self, ctx: commands.Context, name: str, arg: str, source: str, url: str = None
    ):
        """Main function called in all others APIs commands."""
        embed = await self._make_embed_other(ctx, name, url, arg, source)
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                return await self._maybe_embed(ctx, embed)
            else:
                raise commands.NSFWChannelRequired(ctx.channel)
        await ctx.send(embed=embed, ephemeral=True)

    @staticmethod
    async def _embed(
        color: EMBED_COLOUR,
        title: str = None,
        description: str = None,
        image: str = None,
        footer: Optional[str] = None,
    ):
        em = discord.Embed(color=color, title=title, description=description)
        em.set_image(url=image)
        if footer:
            em.set_footer(text=footer)
        return em

    async def get_hentai_img(self) -> str:
        other_stuff = ["jpg", "gif", "yuri", "panties", "thighs", "ass"]
        async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
            async with s.get(
                f"https://lunardev.group/api/nsfw/{random.choice(other_stuff)}"
            ) as r:
                j = await r.json()
                url = j["url"]

        return url

    async def get_hentai_lunar(self, endpoint):
        try:
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                async with s.get(f"https://lunardev.group/api/nsfw/{endpoint}") as r:
                    j = await r.json()
                    url = j["url"]

            return url
        except:
            return "The API is down. Please try again later."

    # Example Command
    @commands.hybrid_command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def panties_example(self, ctx):
        """Pantsu"""
        url = await self.get_hentai_lunar("panties")

        embed = discord.Embed(
            title=f"{url}",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
        await ctx.send(embed=embed, ephemeral=True)

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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            return await ctx.send(":x: This command has been disabled!")

        Server = self.bot.get_guild(755722576445046806)

        # check if the command was used as an interaction
        if ctx.interaction is None:
            ephemeral = False
        else:
            ephemeral = True
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
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
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
                    f"Alright, your auto posting channel has been removed from our database."
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
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
        embed.set_footer(
            text=f"lunardev.group",
        )
        if ctx.interaction is None:
            if ctx.channel.is_nsfw():
                await ctx.send(embed=embed)
                return
            else:
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Nsfw(bot))
