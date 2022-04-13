import random

import aiohttp
import discord
from discord import app_commands
import nekos
from discord.ext import commands
from index import EMBED_COLOUR, config, cursor_n, mydb_n
from Manager.commandManager import cmd
from utils import permissions
from utils.checks import NotVoted


class Nsfw(commands.Cog, name="nsfw", command_attrs=dict(nsfw=True)):
    """Spicy pictures"""

    def __init__(self, bot):
        self.bot = bot
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
        self.lunar_headers = {f"{config.lunarapi.header}": f"{config.lunarapi.token}"}
        for command in self.walk_commands():
            command.nsfw = True

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
        # await ctx.send(embed=embed)

    async def get_hentai_img(self) -> str:
        if random.randint(1, 3) == 1:
            url = nekos.img(random.choice(self.modules))
        else:
            other_stuff = ["jpg", "gif", "yuri"]
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                async with s.get(
                    f"https://lunardev.group/api/nsfw/{random.choice(other_stuff)}",
                    json={"user": "683530527239962627"},
                ) as r:
                    j = await r.json()
                    url = j["url"]

        return url

    async def get_hentai_lunar(self, endpoint):
        async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
            async with s.get(
                f"https://lunardev.group/api/nsfw/{endpoint}",
                json={"user": "683530527239962627"},
            ) as r:
                j = await r.json()
                url = j["url"]

        return url

    @commands.command(aliases=["post", "ap"], usage="`tp!ap #channel`")
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    @permissions.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(
        embed_links=True, manage_channels=True, manage_webhooks=True, attach_files=True
    )
    async def autopost(self, ctx, *, channel: discord.TextChannel):
        """Mention a channel to autopost hentai to. example: `tp!autopost #auto-nsfw`"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        Server = self.bot.get_guild(755722576445046806)

        # await ctx.send(f"This command is currently disabled because it is no
        # longer working (for now). Please join the support server to know what
        # is going on - {config.Server}")

        if not channel.is_nsfw():
            return await ctx.send("That shit isn't NSFW - fuck that.")

        if channel.guild.member_count < 15:
            await ctx.send(
                "I'm sorry, but this server does not meet our requirements. Your server requires over 30 members.\nWe have this requirement to prevent spam and abuse."
            )
            return

        try:
            await Server.fetch_member(ctx.author.id)
        except:
            await ctx.send(
                f"You are not in the support server. Please join the support server to use this command.\n{config.Server}"
            )
            return

        cursor_n.execute(
            f"SELECT hentaichannel FROM public.guilds WHERE guildId = '{ctx.guild.id}'"
        )
        res = cursor_n.fetchall()

        if not channel.mention:
            await ctx.send("Please mention a channel for me to autopost to.")

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
                except:
                    await ctx.send(
                        f"I don't have permission to edit {channel.mention} to make sure I can post there. The channel has been added to the database regardless, if I never post there, you will have to manually edit the channel permissions to allow me to post there."
                    )
                    return
                else:

                    await ctx.send(
                        f"{channel.mention} has been added to the database. I will start posting shortly!\nMake sure that the channel has no overrides that prevent me from posting!"
                    )
            else:
                await ctx.send("whoops, guild already has a fuckin' channel my dude")

    @autopost.error
    async def autopost_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await self.create_embed(ctx, error)
            return
        elif isinstance(error, NotVoted):
            embed = discord.Embed(
                title="Error Caught!",
                color=0xFF0000,
                description=f"You need to vote to run this command! You can vote **[here]({config.Vote})**.",
            )
            embed.set_thumbnail(url=self.bot.user.avatar)
            # await ctx.send(embed=embed)
            return

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error Caught!",
                color=0xFF0000,
                description="Please send the channel you want me to autopost to.\nExample: `tp!autopost #auto-nsfw`",
            )
            embed.set_thumbnail(url=self.bot.user.avatar)
            # await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.ChannelNotFound):
            embed = discord.Embed(
                title="Error Caught!",
                color=0xFF0000,
                description="Hey I couldn't find that channel! Please make sure you mentioned the channel.\nExample: `tp!autopost #auto-nsfw`",
            )
            embed.set_thumbnail(url=self.bot.user.avatar)
            # await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.TooManyArguments):
            embed = discord.Embed(
                title="Error Caught!",
                color=0xFF0000,
                description="Hey don't do that! You sent too many channels for me to post to. I can only post to one channel per server, don't try to break me.",
            )
            embed.set_thumbnail(url=self.bot.user.avatar)
            # await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.BotMissingPermissions):
            await self.create_embed(ctx, error)
            return
        elif isinstance(error, discord.errors.Forbidden):
            await self.create_embed(ctx, error)
            return

    @commands.command(aliases=["apr"], usage="`tp!apr`")
    @permissions.dynamic_ownerbypass_cooldown(
        rate=1, per=5, type=commands.BucketType.user
    )
    @permissions.has_permissions(manage_channels=True)
    async def autopost_remove(self, ctx):
        """Remove the auto hentai posting channel."""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

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

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_nsfw()
    @commands.guild_only()
    async def spank(self, ctx, *, user: discord.Member):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author} Spanks themselves...", colour=EMBED_COLOUR
            )
            embed.set_image(url=nekos.img("spank"))
            embed.set_footer(
                text=f"lunardev.group",
            )
            # await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{ctx.author} Spanks {user.name}...", colour=EMBED_COLOUR
            )
            embed.set_image(url=nekos.img("spank"))
            embed.set_footer(
                text=f"lunardev.group",
            )
            # await ctx.send(embed=embed)

    @commands.command(
        aliases=[
            "trap",
            "boobs",
            "pussy",
            "hentai",
            "neko",
            "lesbian",
            "tits",
            "wallpaper",
            "anal",
            "feet",
            "hololewd",
            "lewdkemo",
            "pwg",
            "blowjob",
            "thighs",
        ]
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_nsfw()
    async def classic(self, ctx):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        await ctx.send(
            content=f"""
This command has been converted to slash commands.
The slash commands are global, and if you cant see any of the slash commands, AGB does not have the permissions to set them up.
Please reinvite AGB with `tp!invite` or use the integrated invite button (see screenshot).
If you need help, please join the support server - {config.Server}\nPress `/` on your keyboard to see the commands, it should look something like this - (see screenshot)
                       """,
            files=[discord.File("slashcmds.png"), discord.File("integratedinvite.png")],
        )

    # # @permissions.dynamic_ownerbypass_cooldown(rate=1, per=2, type=commands.BucketType.user)
    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def slashclassic(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("classic"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def trap(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("trap"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def boobs(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("boobs"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def pussy(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("pussy"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def hentai(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=(await self.get_hentai_img()))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def neko(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("neko"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        # await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def lesbian(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("les"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def tits(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("tits"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 3, key=lambda i: (i.guild_id, i.user.id))
    async def wallpaper(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("wallpaper"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def anal(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("anal"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def feet(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("feet"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def holo(self, interaction: discord.Interaction) -> None:
        url = await self.get_hentai_lunar("hololive")
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def kemo(self, interaction: discord.Interaction) -> None:
        url = await self.get_hentai_lunar("neko")
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def pwg(self, interaction: discord.Interaction) -> None:
        url = await self.get_hentai_lunar("panties")
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def blow(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("blowjob"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def thighs(self, interaction: discord.Interaction) -> None:
        url = await self.get_hentai_lunar("thighs")
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=url)
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(2, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def boobs(self, interaction: discord.Interaction) -> None:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"
        embed = discord.Embed(
            title="Enjoy",
            url="https://lunardev.group/",
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            colour=EMBED_COLOUR,
        )
        embed.set_image(url=nekos.img("boobs"))
        embed.set_footer(
            text=f"lunardev.group\nYou've used {usedCommands} commands so far!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Nsfw(bot))
