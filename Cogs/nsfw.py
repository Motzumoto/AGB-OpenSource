from __future__ import annotations

import asyncio
import json
import random
from random import choice
from typing import TYPE_CHECKING, List, Optional, Union

import aiohttp
import discord
from discord.ext import commands
from index import EMBED_COLOUR, colors, config
from utils import constants as sub
from utils import default, imports, permissions
from utils.checks import voter_only
from utils.constants import (
    GOOD_EXTENSIONS,
    IMGUR_LINKS,
    MARTINE_API_BASE_URL,
    NOT_EMBED_DOMAINS,
    REDDIT_BASEURL,
    emoji,
)
from utils.default import bold, inline, log

from Cogs.Utils import Translator

_ = Translator("Nsfw", __file__)

MY_GUILD_ID = discord.Object(975810661709922334)
owners = default.get("config.json").owners
config = imports.get("config.json")
testing = ["True", "False"]

if TYPE_CHECKING:
    from index import Bot


class Nsfw(commands.Cog, name="nsfw", command_attrs=dict(nsfw=True)):
    """Spicy pictures"""

    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.use_reddit_api = random.choice(testing)
        self.session = aiohttp.ClientSession(headers={"User-Agent": "AGB"})
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

    async def _get_imgs(self, subs: List[str] = None):
        # sourcery skip: use-fstring-for-concatenation
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
            (
                _(
                    "Error when trying to contact image service, please try again later. "
                )
                + f"(Code: {inline(str(error_code))})"
            )
        )

    async def _make_embed(self, ctx: commands.Context, subs: List[str], name: str):
        """Function to make the embed for all Reddit API images."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = f"{db_user.used_commands + 1} used commands"
        try:
            url, subr = await asyncio.wait_for(self._get_imgs(subs=subs), 5)
            log(subr)
        except asyncio.TimeoutError:
            await ctx.send(
                "Failed to get an image. Please try again later. (Timeout error)"
            )
            return
        if not url:
            return

        return (
            (
                _("Here is {name} gif ...")
                + " \N{EYES}\n\n"
                + _("From {r}\n{url} • {u}")
            ).format(
                name=name,
                req=bold(ctx.author.name),
                emoji=emoji(),
                r=bold(f"r/{subr}"),
                url=url,
                u=used_commands,
            )
            if any(wrong in url for wrong in NOT_EMBED_DOMAINS)
            else await self._embed(
                color=colors.prim,
                title=(_("Here is {name} image ...") + " \N{EYES}").format(name=name),
                description=bold(
                    _("[Link if you don't see image]({url})").format(url=url),
                    escape_formatting=False,
                ),
                image=url,
                footer=_("From r/{r} • {u}").format(
                    req=ctx.author.display_name, emoji=emoji(), r=subr, u=used_commands
                ),
            )
        )

    async def _make_embed_other(
        self, ctx: commands.Context, name: str, url: str, arg: str, source: str
    ):
        """Function to make the embed for all others APIs images."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = f"{db_user.used_commands + 1} used commands"
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
            color=colors.prim,
            title=(_("Here is {name} image ...") + " \N{EYES}").format(name=name),
            description=bold(
                _("[Link if you don't see image]({url})").format(url=data["img"][arg]),
                escape_formatting=False,
            ),
            image=data["img"][arg],
            footer=_("From {source} {e} • {u}").format(
                source=source, e=emoji(), u=used_commands
            ),
        )
        return em

    async def _maybe_embed(
        self, ctx: commands.Context, embed: Union[discord.Embed, str]
    ):
        """
        Function to choose if type of the message is an embed or not
        and if not send a simple message.
        """
        await ctx.typing(ephemeral=True)
        try:
            if isinstance(embed, discord.Embed):
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed)
        except discord.HTTPException as e:
            raise commands.BotMissingPermissions(["embed_links"]) from e

    async def _send_msg(self, ctx: commands.Context, name: str, subs: List[str] = None):
        """Main function called in all Reddit API commands."""
        await ctx.typing(ephemeral=True)
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
        await ctx.typing(ephemeral=True)
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
        except Exception:
            return "The API is down. Please try again later."

    @commands.hybrid_command()
    @voter_only()
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
        """Mention a channel to autopost to. example: `tp!autopost #auto-nsfw`"""
        await ctx.typing(ephemeral=True)
        Server = self.bot.get_guild(755722576445046806)

        # check if the command was used as an interaction
        ephemeral = ctx.interaction is not None
        if not channel.is_nsfw():
            return await ctx.send("That channel isn't NSFW, no.", ephemeral=ephemeral)

        # if channel.guild.member_count < 15:
        #     if channel.guild.owner_id in config.owners:
        #         pass
        #     else:
        #         await ctx.send(
        #             "I'm sorry, but this server does not meet our requirements. Your server requires over 15 members.\nWe have this requirement to prevent spam and abuse.\nWhile you can't use this feature, you can still use all of AGB's NSFW commands which require a vote to be able to use all of them. You can vote for AGB's NSFW commands by using `tp!vote`. Thanks for understanding.",
        #             ephemeral=ephemeral,
        #         )
        #         return

        try:
            await Server.fetch_member(ctx.author.id)
        except Exception:
            await ctx.send(
                f"You are not in the support server. Please join the support server to use this command. This is to make sure that your server gets posts sent to it correctly.\n{config.Server}"
            )
            return

        if not channel.mention:
            await ctx.send(
                "Please mention a channel for me to autopost to.", ephemeral=ephemeral
            )

        db_guild = self.bot.db.get_guild(ctx.guild.id) or await self.bot.db.fetch_guild(
            ctx.guild.id
        )
        if not db_guild:
            db_guild = await self.bot.db.add_guild(ctx.guild.id)

        if db_guild.hentai_channel_id and db_guild.hentai_channel_id == channel.id:
            await ctx.send(
                "whoops, guild already has a channel my dude",
                ephemeral=ephemeral,
            )
            return
        # add to the db
        await db_guild.modify(hentai_channel_id=channel.id)

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
            await channel.edit(overwrites=overwrites)  # type: ignore
        except Exception:
            await ctx.send(
                (
                    f"I don't have permission to edit {channel.mention} to make sure I can post there. "
                    "The channel has been added to the database regardless, if I never post there, "
                    "you will have to manually edit the channel permissions to allow me to post there."
                ),
                ephemeral=ephemeral,
            )
            return
        else:
            await ctx.send(
                (
                    f"{channel.mention} has been added to the database. I will start posting shortly!\n"
                    "Make sure that the channel has no overrides that prevent me from posting!"
                ),
                ephemeral=ephemeral,
            )

    @commands.hybrid_command()
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    @voter_only()
    @permissions.has_permissions(manage_channels=True)
    async def autopost_remove(self, ctx):
        """Remove the auto posting channel."""
        await ctx.typing(ephemeral=True)
        # await ctx.send(f"This command is currently disabled because it is no
        # longer working (for now). Please join the support server to know what
        # is going on - {config.Server}")
        db_guild = self.bot.db.get_guild(ctx.guild.id) or await self.bot.db.fetch_guild(
            ctx.guild.id
        )
        if not db_guild or not db_guild.hentai_channel_id:
            await ctx.send("you don't have a fukin' channel idot.")
            return

        # remove the channel from the db
        await db_guild.modify(hentai_channel_id=None)
        await ctx.send(
            "Alright, your auto posting channel has been removed from our database."
        )

    @commands.hybrid_group()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def nsfw(self, ctx):
        """Nsfw Commands"""
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        if ctx.invoked_subcommand is None:
            return await ctx.send(
                "Invalid nsfw command. Please use `tp!help nsfw` to see the nsfw commands."
            )

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def butt(self, ctx):
        """the thing that you sit on!\nUse `tp!nsfw command` to use this command."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = db_user.used_commands + 1
        if random.randint(1, 5) == 1:
            await ctx.typing(ephemeral=True)
            # return await ctx.send("This command is being on.", ephemeral=True)
            url = await self.get_hentai_lunar("ass")

            embed = discord.Embed(
                title="Enjoy",
                url="https://lunardev.group/",
                description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
                colour=colors.prim,
            )
            embed.set_image(url=url)
            embed.set_footer(
                text=f"lunardev.group | {used_commands} commands used.",
            )
            if ctx.interaction is None:
                if not ctx.channel.is_nsfw():
                    # raise nsfw channel required
                    raise commands.NSFWChannelRequired(ctx.channel)
                await ctx.send(embed=embed)
                return
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await self._send_msg(ctx, "ass", sub.ASS)

    @nsfw.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def underwear(self, ctx):
        """underwear\nUse `tp!nsfw command` to use this command."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = db_user.used_commands + 1
        await ctx.typing(ephemeral=True)
        # # return await ctx.send("This command is being on.", ephemeral=True)
        url = await self.get_hentai_lunar("panties")

        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=colors.prim,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group | {used_commands} commands used.",
        )
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
        """holo live streamer nsfw\nUse `tp!nsfw command` to use this command."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = db_user.used_commands + 1
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        url = await self.get_hentai_lunar("hololive")

        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=colors.prim,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group | {used_commands} commands used.",
        )
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
        """kemonomimi; fox girls/cat girls/animal girls\nUse `tp!nsfw command` to use this command."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = db_user.used_commands + 1
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        url = await self.get_hentai_lunar("neko")
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=colors.prim,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group | {used_commands} commands used.",
        )
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
        """gif\nUse `tp!nsfw command` to use this command."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = db_user.used_commands + 1
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        url = await self.get_hentai_lunar("panties")

        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=colors.prim,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group | {used_commands} commands used.",
        )
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
        """thigh pictures\nUse `tp!nsfw command` to use this command."""
        db_user = self.bot.db.get_user(ctx.author.id) or await self.bot.db.fetch_user(
            ctx.author.id
        )
        used_commands = db_user.used_commands + 1
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        url = await self.get_hentai_lunar("thighs")

        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=colors.prim,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group | {used_commands} commands used.",
        )
        if ctx.interaction is None:
            if not ctx.channel.is_nsfw():
                # raise nsfw channel required
                raise commands.NSFWChannelRequired(ctx.channel)
            await ctx.send(embed=embed)
            return
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_group()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def reddit_irl(self, ctx):
        """NSFW Reddit Commands"""
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        if ctx.invoked_subcommand is None:
            return await ctx.send(
                "Invalid nsfw command. Please use `tp!help reddit_irl` to see the nsfw commands."
            )

    @commands.hybrid_group()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def reddit_drawing(self, ctx):
        """NSFW Reddit Commands"""
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        if ctx.invoked_subcommand is None:
            return await ctx.send(
                "Invalid nsfw command. Please use `tp!help reddit` to see the nsfw commands."
            )

    @commands.hybrid_group()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def reddit(self, ctx):
        """NSFW Reddit Commands"""
        await ctx.typing(ephemeral=True)
        # return await ctx.send("This command is being on.", ephemeral=True)
        if ctx.invoked_subcommand is None:
            return await ctx.send(
                "Invalid nsfw command. Please use `tp!help reddit` to see the nsfw commands."
            )

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def fourk(self, ctx: commands.Context):
        """Sends some 4k images from random subreddits."""
        await self._send_msg(ctx, "4k", sub.FOUR_K)

    @reddit_drawing.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def o_face(self, ctx: commands.Context):
        """Sends some o_face images from random subreddits."""
        await self._send_msg(ctx, "ahegao", sub.AHEGAO)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def asian(self, ctx: commands.Context):
        """Sends some asian images."""
        await self._send_msg(ctx, "asian porn", sub.ASIANPORN)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def thicc(self, ctx: commands.Context):
        """Sends some thicc images."""
        await self._send_msg(ctx, "bbw", sub.BBW)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def kink(self, ctx: commands.Context):
        """Sends some kink from random subreddits."""
        await self._send_msg(ctx, "bdsm", sub.BDSM)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def blackpp(self, ctx: commands.Context):
        """Sends some blackpp images from random subreddits."""
        await self._send_msg(ctx, "black cock", sub.BLACKCOCK)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def blow(self, ctx: commands.Context):
        """Sends some blow images/gifs from random subreddits."""
        await self._send_msg(ctx, "blowjob", sub.BLOWJOB)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def bobs(self, ctx: commands.Context):
        """Sends some bobs images from random subreddits."""
        await self._send_msg(ctx, "boobs", sub.BOOBS)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def bottomless(self, ctx: commands.Context):
        """Sends some bottomless images from random subreddits."""
        await self._send_msg(ctx, "bottomless", sub.BOTTOMLESS)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def cosplay(self, ctx: commands.Context):
        """Sends some nsfw cosplay images from random subreddits."""
        await self._send_msg(ctx, "nsfw cosplay", sub.COSPLAY)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def pp(self, ctx: commands.Context):
        """Sends some pp images from random subreddits."""
        await self._send_msg(ctx, "dick", sub.DICK)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def doublepenetration(self, ctx: commands.Context):
        """Sends some doublepenetration images/gifs from random subreddits."""
        await self._send_msg(ctx, "double penetration", sub.DOUBLE_P)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def ebony(self, ctx: commands.Context):
        """Sends some ebony images."""
        await self._send_msg(ctx, "ebony", sub.EBONY)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def facials(self, ctx: commands.Context):
        """Sends some facials images from random subreddits."""
        await self._send_msg(ctx, "facials", sub.FACIALS)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def feet(self, ctx: commands.Context):
        """Sends some feet images from random subreddits."""
        await self._send_msg(ctx, "feets", sub.FEET)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def fdom(self, ctx: commands.Context):
        """Sends some fdom images from random subreddits."""
        await self._send_msg(ctx, "femdom", sub.FEMDOM)

    @reddit_drawing.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def drawing(self, ctx: commands.Context):
        """Sends some lewd drawing images/gifs from Nekobot API."""

        await self._send_other_msg(
            ctx,
            name="hentai",
            arg="message",
            source="Nekobot API",
            url=sub.NEKOBOT_URL.format(sub.NEKOBOT_HENTAI),
        )

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def lesb(self, ctx: commands.Context):
        """Sends some lesb gifs or images from random subreddits."""
        await self._send_msg(ctx, "lesbian", sub.LESBIANS)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def mylf(self, ctx: commands.Context):
        """Sends some mylf images from random subreddits."""
        await self._send_msg(ctx, "milf", sub.MILF)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def oral(self, ctx: commands.Context):
        """Sends some oral gifs or images from random subreddits."""
        await self._send_msg(ctx, "oral", sub.ORAL)

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def gif(self, ctx: commands.Context):
        """Sends some gifs from Nekobot API."""
        await self._send_other_msg(
            ctx,
            name="porn gif",
            arg="message",
            source="Nekobot API",
            url=sub.NEKOBOT_URL.format("pgif"),
        )

    @reddit_irl.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def public(self, ctx: commands.Context):
        """Sends some public images from random subreddits."""
        await self._send_msg(ctx, "public nude", sub.PUBLIC)

    @reddit.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def kitty(self, ctx: commands.Context):
        """Sends some kitty nude images from random subreddits."""
        await self._send_msg(ctx, "pussy", sub.PUSSY)

    @reddit.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def realgirls(self, ctx: commands.Context):
        """Sends some real girls images from random subreddits."""
        await self._send_msg(ctx, "real nudes", sub.REAL_GIRLS)

    @reddit.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def redhead(self, ctx: commands.Context):
        """Sends some red heads images from random subreddits."""
        await self._send_msg(ctx, "red head", sub.REDHEADS)

    @reddit_drawing.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def r34(self, ctx: commands.Context):
        """Sends some r34 images from random subreddits."""
        await self._send_msg(ctx, "rule34", sub.RULE_34)

    @reddit_drawing.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def furry(self, ctx: commands.Context):
        """Sends some furry images from random subreddits."""
        await self._send_msg(ctx, "yiff", sub.YIFF)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Nsfw(bot))
