import random

from discord import Embed
from discord.ui import button, View
from discord.ext import commands
from typing import List

from index import EMBED_COLOUR, Vote, Server, Invite, emojis
from discord.utils import get

EMOJIS = {
    'first': '<:first:861982503001653249>',
    'next': '<:right:861982503266943018>',
    'stop': '<:stop:861982503035600917>',
    'back': '<:left:861982473420144643>',
    'last': '<:last:861982503397228564>'}


def cog_unload(self):
    self.bot.help_command = self.bot._original_help_command

class Help(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        bot.help_command = FormattedHelp()


class Unit(dict):
    def __getattr__(self, attr):
        if attr in self:
            return self[attr]
        elif hasattr(self, attr):
            return self.attr
        else:
            return None

    async def edit(self, message, unit):
        await message.edit(content=unit.content, embed=unit.embed)


class Paginator(View):
    def __init__(self, ctx, *units: List[Unit]):
        super().__init__()
        self.ctx = ctx
        self.loop = ctx.bot.loop
        self.units = units
        self.current = 0
        self.timeout = 30

    async def edit(self, message, pos):
        unit = self.units[pos]
        unit.embed.set_footer(text=f"Page: {pos}")
        await message.edit(embed=unit.embed)

    @button(emoji=EMOJIS['first'])
    async def first(self, button, interaction):
        await self.edit(interaction.message, 0)
        self.current = 0

    @button(emoji=EMOJIS['back'])
    async def back(self, button, interaction):
        if self.current-1 == -1:
            return
        await self.edit(interaction.message, self.current-1)
        self.current -= 1

    @button(emoji=EMOJIS['stop'])
    async def stop(self, button, interaction):
        await interaction.message.delete()

    @button(emoji=EMOJIS['next'])
    async def _next(self, button, interaction):
        if self.current + 1 == len(self.units):
            return
        await self.edit(interaction.message, self.current+1)
        self.current += 1

    @button(emoji=EMOJIS['last'])
    async def last(self, button, interaction):
        pos = len(self.units)-1
        await self.edit(interaction.message, pos)
        self.current = pos

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        else:
            await interaction.response.send_message(f"You cannot interact with someone else's command!{random.choice(emojis.rainbow_emojis)}", ephemeral=True)


class FormattedHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'usage': '`tp!help (command/category)`'})

    def get_usage(self, command):
        return f"tp!{command.qualified_name} {' '.join([f'({arg})' for arg in command.clean_params])}"

    def get_cog_embed(self, cog):
        embed = Embed(title=cog.qualified_name, color=EMBED_COLOUR)
        if hasattr(cog, 'description'):
            embed.description = cog.description
        return embed

    async def send_error_message(self, error):
        embed = Embed(title=error, color=EMBED_COLOUR)
        await self.get_destination().send(embed=embed)

    def get_command_embed(self, command):
        ctx = self.context
        embed = Embed(title=command.qualified_name,
                      description=command.description, color=EMBED_COLOUR)
        embed.add_field(name="Usage", value=self.get_usage(command))
        return embed

    def nsfw(self, command):
        return getattr(command, 'nsfw', False) and not self.context.channel.is_nsfw()

    async def nsfw_warn(self):
        await self.context.send(embed=Embed(title=f"You can only view NSFW commands in an NSFW channel!{random.choice(emojis.rainbow_emojis)}", color=EMBED_COLOUR), delete_after=10)

    async def send_command_help(self, command):
        if self.nsfw(command):
            return await self.nsfw_warn()
        if getattr(command, 'hidden', False):
            return await self.send_error_message(self.command_not_found(command.qualified_name))
        await self.context.send(embed=self.get_command_embed(command))

    async def send_cog_help(self, cog):
        if self.nsfw(cog):
            return await self.nsfw_warn()
        if getattr(cog, 'hidden', False):
            return await self.send_error_message(self.command_not_found(cog.qualified_name))
        units = [Unit(embed=self.get_cog_embed(cog))]
        for command in cog.walk_commands():
            units.append(Unit(embed=self.get_command_embed(command)))
        await self.context.send(embed=self.get_cog_embed(cog), view=Paginator(self.context, *units))

    async def send_group_help(self, group):
        if self.nsfw(group):
            return await self.nsfw_warn()
        if getattr(group, 'hidden', False):
            return await self.send_error_message(self.command_not_found(group.qualified_name))
        units = [Unit(embed=self.get_command_embed(group))]
        for command in group.walk_commands():
            units.append(Unit(embed=self.get_command_embed(command)))
        await self.context.send(embed=self.get_command_embed(group), view=Paginator(self.context, *units))

    async def send_bot_help(self, mapping):
        units = []
        for cog, commands in mapping.items():
            if len(commands) != 0:
                if not getattr(cog, 'hidden', False) and not self.nsfw(cog):
                    embed = Embed(title=cog.qualified_name if cog else "\u200b", description="\n".join([self.get_usage(
                        command) for command in mapping[cog] if not getattr(command, 'hidden', False) and not self.nsfw(command)]), color=EMBED_COLOUR)
                    units.append(Unit(embed=embed))
    
        embed = Embed(title=f"AGB Commands{random.choice(emojis.rainbow_emojis)}",
                    description="AGB can offer you a ton of useful and fun commands to use!", color=EMBED_COLOUR)
        embed.set_image(
            url='https://cdn.discordapp.com/avatars/723726581864071178/5e7d167dbf17ebc4137b2ed3fa2a698f.png?size=1024')
        await self.context.send(embed=embed, view=Paginator(self.context, *units))


def setup(b):
    b.add_cog(Help(b))
