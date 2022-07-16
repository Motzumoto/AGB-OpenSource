from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, menus
from index import colors, config, emojis

if TYPE_CHECKING:
    from index import Bot


class Help(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        bot.help_command = FormattedHelp()
        self.bot._original_help_command = bot.help_command


async def cog_unload(self):
    self.bot.help_command = self.bot._original_help_command


async def cog_check(self, ctx):
    """A local check which applies to all commands in this cog."""
    if not ctx.guild:
        raise commands.NoPrivateMessage
    return True


class HelpMenu(menus.ListPageSource):
    def __init__(self, data, per_page):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu, entries):
        return entries


class FormattedHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={"usage": "`tp!help (command/category)`", "hidden": True}
        )

    async def cog_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")

    def get_command_signature(self, command):
        return (
            f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"
        )

    def rem_lead_space(self, strict=False):
        if self and not strict and self[0] == "\n":
            self = self[1:]
        lines = self.splitlines(True)
        max_spaces = -1
        for line in lines:
            if line != "\n":
                for idx, c in enumerate(lines[:max_spaces]):
                    if c != " ":
                        break
                max_spaces = idx + 1
        return "".join([l if l == "\n" else l[max_spaces - 1 :] for l in lines])

    async def send_command_help(self, command):
        self.context
        e = discord.Embed(
            title=f"Help - {command.qualified_name} {random.choice(emojis.rainbow_emojis)}",
            description=f"{command.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            color=colors.prim,
        )
        e.add_field(
            name="Usage", value=self.get_command_signature(command).replace("*", "")
        )
        e.set_footer(
            text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and WinterFe"
        )
        await self.get_destination().send(embed=e)

    async def send_group_help(self, group):
        ctx = self.context
        e = discord.Embed(
            title=f"Help - {group.qualified_name} {random.choice(emojis.rainbow_emojis)}",
            description=f"{group.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            color=colors.prim,
        )
        e.set_footer(
            text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and WinterFe"
        )
        embeds = [e]
        for command in group.commands:
            e = discord.Embed(
                title=f"Help - {command.qualified_name} {random.choice(emojis.rainbow_emojis)}",
                description=f"{command.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                color=colors.prim,
            )
            e.add_field(
                name="Usage", value=self.get_command_signature(command).replace("*", "")
            )
            e.set_footer(
                text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and WinterFe"
            )
            embeds.append(e)
        menu = menus.MenuPages(source=HelpMenu(embeds, per_page=1))
        await menu.start(ctx)

    async def send_cog_help(self, cog):
        ctx = self.context
        e = discord.Embed(
            title=f"Help - {cog.qualified_name} {random.choice(emojis.rainbow_emojis)}",
            description=getattr(cog, "__doc__", None),
            color=colors.prim,
        )
        e.set_footer(
            text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and WinterFe"
        )
        embeds = [e]
        for command in cog.walk_commands():
            if isinstance(command, commands.Group) or getattr(command, "hidden"):
                continue
            e = discord.Embed(
                title=f"Help - {command.qualified_name} {random.choice(emojis.rainbow_emojis)}",
                description=f"{command.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})  ",
                color=colors.prim,
            )
            if command.usage:
                e.add_field(
                    name="Usage",
                    value=self.get_command_signature(command).replace("*", ""),
                )
                e.add_field(name="Support Server", value=f"[Click Me]({config.Server})")
            e.set_footer(
                text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and WinterFe"
            )
            embeds.append(e)
        menu = menus.MenuPages(source=HelpMenu(embeds, per_page=1))
        await menu.start(ctx)

    async def send_bot_help(self, mapping):
        # check if we're in a DM
        if self.context.guild is None:
            fuck_off = "This command can only be used in a server."
            await self.get_destination().send(fuck_off)
            return
        nsfw_channels = (
            ", ".join(
                [c.mention for c in self.context.guild.text_channels if c.is_nsfw()]
            )
            or "No NSFW channels found. Make one to be able to use these commands."
        )
        async with self.context.typing():
            nsfw_cog = self.context.bot.get_cog("nsfw")
            nsfw_commands = nsfw_cog.get_commands()
            nsfw_q = [c.name for c in nsfw_commands if not c.hidden]
            nsfw_names = "".join(f"`{name}`, " for name in nsfw_q)

            info_cog = self.context.bot.get_cog("info")
            info_commands = info_cog.get_commands()
            info_q = [c.name for c in info_commands if not c.hidden]
            info_names = "".join(f"`{name}`, " for name in info_q)

            economy_cog = self.context.bot.get_cog("Help")
            economy_commands = economy_cog.get_commands()
            economy_q = [c.name for c in economy_commands if not c.hidden]
            economy_names = "".join(f"`{name}`, " for name in economy_q)

            fun_cog = self.context.bot.get_cog("fun")
            fun_commands = fun_cog.get_commands()
            fun_q = [c.name for c in fun_commands if not c.hidden]
            fun_names = "".join(f"`{name}`, " for name in fun_q)

            guild_cog = self.context.bot.get_cog("discord")
            guild_commands = guild_cog.get_commands()
            guild_q = [c.name for c in guild_commands if not c.hidden]
            guild_names = "".join(f"`{name}`, " for name in guild_q)

            mod_cog = self.context.bot.get_cog("mod")
            mod_commands = mod_cog.get_commands()
            mod_q = [c.name for c in mod_commands if not c.hidden]
            mod_names = "".join(f"`{name}`, " for name in mod_q)

            music_cog = self.context.bot.get_cog("music")
            music_commands = music_cog.get_commands()
            music_q = [c.name for c in music_commands if not c.hidden]
            music_names = "".join(f"`{name}`, " for name in music_q)

            if self.context.channel.is_nsfw():
                description = f"""For help on individual commands, use `tp!help <command>`.\n\n**{random.choice(emojis.rainbow_emojis)} {info_cog.qualified_name.capitalize()}**\n{info_names}\n\n**{random.choice(emojis.rainbow_emojis)} {economy_cog.qualified_name.capitalize()}**\n{economy_names}\n\n**{random.choice(emojis.rainbow_emojis)} {fun_cog.qualified_name.capitalize()}**\n{fun_names}\n\n**{random.choice(emojis.rainbow_emojis)} {guild_cog.qualified_name.capitalize()}**
				{guild_names}\n\n**{random.choice(emojis.rainbow_emojis)} {mod_cog.qualified_name.capitalize()}**\n{mod_names}\n\n{random.choice(emojis.rainbow_emojis)} **{music_cog.qualified_name.capitalize()}**\n{music_names}\n\n{random.choice(emojis.rainbow_emojis)} **{nsfw_cog.qualified_name.capitalize()}**\n{nsfw_names}\nalso, there are nsfw slash commands. make sure AGB has permission to register them in your server."""

                embed = discord.Embed(
                    color=colors.prim,
                    description=f"{description}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                )
                embed.set_footer(
                    text="If there is anything that you would like to see / changed, run 𝐭𝐩!𝐬𝐮𝐠𝐠𝐞𝐬𝐭 with your suggestion!\nAlso check out our server host!"
                )
            else:
                description = f"""**{random.choice(emojis.rainbow_emojis)} {info_cog.qualified_name.capitalize()}**\n{info_names}\n\n**{random.choice(emojis.rainbow_emojis)} {economy_cog.qualified_name.capitalize()}**\n{economy_names}\n\n**{random.choice(emojis.rainbow_emojis)} {fun_cog.qualified_name.capitalize()}**\n{fun_names}\n\n**{random.choice(emojis.rainbow_emojis)} {guild_cog.qualified_name.capitalize()}**\n{guild_names}\n\n**{random.choice(emojis.rainbow_emojis)} {mod_cog.qualified_name.capitalize()}**\n{mod_names}\n\n{random.choice(emojis.rainbow_emojis)}**{music_cog.qualified_name.capitalize()}**\n{music_names}\n\n{random.choice(emojis.rainbow_emojis)}**{nsfw_cog.qualified_name.capitalize()}**\nNsfw commands are hidden. To see them run tp!help in any of these NSFW channels.\n{nsfw_channels}"""

                embed = discord.Embed(
                    color=colors.prim,
                    description=f"{description}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
                )
                embed.set_footer(
                    text="If there is anything that you would like to see / changed, run 𝐭𝐩!𝐬𝐮𝐠𝐠𝐞𝐬𝐭 with your suggestion!"
                )

            embed.set_thumbnail(url=self.context.bot.user.avatar)
            await self.get_destination().send(embed=embed)
            return

        #     embed_description = ""

        #     # nsfw_cog = self.bot.get_cog('nsfw')
        #     # nsfw_commands = nsfw_cog.get_commands()

        #     for cog, commands in mapping.items():
        #         qualified_names = [c.name for c in commands if not c.hidden]
        #         if not qualified_names or getattr(cog, 'hidden', None) or not cog:
        #             continue
        #         qualified_names = ''.join(
        # f'`{name}`, ' for index, name in enumerate(qualified_names))

        #         embed_description += f"**{random.choice(emojis.rainbow_emojis)} {cog.qualified_name.capitalize() or 'No Category'}**\n{qualified_names[:-2]}\n\n"

        # embed = discord.Embed(color=colors.prim, description=f"For help on individual commands, use `tp!help <command>`.\n\n{embed_description}")
        # embed.add_field(name='Support Server', value=f"[Click Me]({config.Server})")
        # embed.set_footer(text="If there is anything that you would like to see / changed, run 𝐭𝐩!𝐬𝐮𝐠𝐠𝐞𝐬𝐭 with your suggestion!")
        # embed.set_thumbnail(url=self.context.bot.user.avatar)
        # await self.get_destination().send(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Help(bot))
    bot.get_command("help").hidden = True


# import random

# from discord import Embed
# from discord.ui import button, View
# from discord.ext import commands
# from typing import List

# from index import EMBED_COLOUR, Vote, Server, Invite, emojis
# from discord.utils import get

# EMOJIS = {
#     'first': '<:first:861982503001653249>',
#     'next': '<:right:861982503266943018>',
#     'stop': '<:stop:861982503035600917>',
#     'back': '<:left:861982473420144643>',
#     'last': '<:last:861982503397228564>'}


# async def cog_unload(self):
#     self.bot.help_command = self.bot._original_help_command

# class Help(commands.Cog, command_attrs=dict(hidden=True)):
#     def __init__(self, bot):
#         self.bot = bot
#         bot.help_command = FormattedHelp()


# class Unit(dict):
#     def __getattr__(self, attr):
#         if attr in self:
#             return self[attr]
#         elif hasattr(self, attr):
#             return self.attr
#         else:
#             return None

#     async def edit(self, message, unit):
#         await message.edit(content=unit.content, embed=unit.embed)


# class Paginator(View):
#     def __init__(self, ctx, *units: List[Unit]):
#         super().__init__()
#         self.ctx = ctx
#         self.loop = ctx.bot.loop
#         self.units = units
#         self.current = 0
#         self.timeout = 30

#     async def edit(self, message, pos):
#         unit = self.units[pos]
#         unit.embed.set_footer(text=f"Page: {pos}")
#         await message.edit(embed=unit.embed)

#     @button(emoji=EMOJIS['first'])
#     async def first(self, button, interaction):
#         await self.edit(interaction.message, 0)
#         self.current = 0

#     @button(emoji=EMOJIS['back'])
#     async def back(self, button, interaction):
#         if self.current-1 == -1:
#             return
#         await self.edit(interaction.message, self.current-1)
#         self.current -= 1

#     @button(emoji=EMOJIS['stop'])
#     async def stop(self, button, interaction):
#         await interaction.message.delete()

#     @button(emoji=EMOJIS['next'])
#     async def _next(self, button, interaction):
#         if self.current + 1 == len(self.units):
#             return
#         await self.edit(interaction.message, self.current+1)
#         self.current += 1

#     @button(emoji=EMOJIS['last'])
#     async def last(self, button, interaction):
#         pos = len(self.units)-1
#         await self.edit(interaction.message, pos)
#         self.current = pos

#     async def interaction_check(self, interaction):
#         if interaction.user == self.ctx.author:
#             return True
#         else:
#             await interaction.followup.send(f"You cannot interact with someone else's command!{random.choice(emojis.rainbow_emojis)}", ephemeral=True)


# class FormattedHelp(commands.HelpCommand):
#     def __init__(self):
#         super().__init__(command_attrs={
#             'usage': '`tp!help (command/category)`'})

#     def get_usage(self, command):
#         return f"tp!{command.qualified_name} {' '.join([f'({arg})' for arg in command.clean_params])}"

#     def get_cog_embed(self, cog):
#         embed = Embed(title=cog.qualified_name, color=colors.prim)
#         if hasattr(cog, 'description'):
#             embed.description = cog.description
#         return embed

#     async def send_error_message(self, error):
#         embed = Embed(title=error, color=colors.prim)
#         await self.get_destination().send(embed=embed)

#     def get_command_embed(self, command):
#         ctx = self.context
#         embed = Embed(title=command.qualified_name,
#                       description=command.description, color=colors.prim)
#         embed.add_field(name="Usage", value=self.get_usage(command))
#         return embed

#     def nsfw(self, command):
#         return getattr(command, 'nsfw', False) and not self.context.channel.is_nsfw()

#     async def nsfw_warn(self):
#         await self.context.send(embed=Embed(title=f"You can only view NSFW commands in an NSFW channel!{random.choice(emojis.rainbow_emojis)}", color=colors.prim), delete_after=10)

#     async def send_command_help(self, command):
#         if self.nsfw(command):
#             return await self.nsfw_warn()
#         if getattr(command, 'hidden', False):
#             return await self.send_error_message(self.command_not_found(command.qualified_name))
#         await self.context.send(embed=self.get_command_embed(command))

#     async def send_cog_help(self, cog):
#         if self.nsfw(cog):
#             return await self.nsfw_warn()
#         if getattr(cog, 'hidden', False):
#             return await self.send_error_message(self.command_not_found(cog.qualified_name))
#         units = [Unit(embed=self.get_cog_embed(cog))]
#         for command in cog.walk_commands():
#             units.append(Unit(embed=self.get_command_embed(command)))
#         await self.context.send(embed=self.get_cog_embed(cog), view=Paginator(self.context, *units))

#     async def send_group_help(self, group):
#         if self.nsfw(group):
#             return await self.nsfw_warn()
#         if getattr(group, 'hidden', False):
#             return await self.send_error_message(self.command_not_found(group.qualified_name))
#         units = [Unit(embed=self.get_command_embed(group))]
#         for command in group.walk_commands():
#             units.append(Unit(embed=self.get_command_embed(command)))
#         await self.context.send(embed=self.get_command_embed(group), view=Paginator(self.context, *units))

#     async def send_bot_help(self, mapping):
#         units = []
#         for cog, commands in mapping.items():
#             if len(commands) != 0:
#                 if not getattr(cog, 'hidden', False) and not self.nsfw(cog):
#                     embed = Embed(title=cog.qualified_name if cog else "\u200b", description="\n".join([self.get_usage(
#                         command) for command in mapping[cog] if not getattr(command, 'hidden', False) and not self.nsfw(command)]), color=colors.prim)
#                     units.append(Unit(embed=embed))

#         embed = Embed(title=f"AGB Commands{random.choice(emojis.rainbow_emojis)}",
#                     description="AGB can offer you a ton of useful and fun commands to use!", color=colors.prim)
#         embed.set_image(
#             url='https://cdn.discordapp.com/avatars/723726581864071178/5e7d167dbf17ebc4137b2ed3fa2a698f.png?size=1024')
#         await self.context.send(embed=embed, view=Paginator(self.context, *units))


# def setup(b):
#     b.add_cog(Help(b))
