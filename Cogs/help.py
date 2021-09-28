import random

import discord
from discord.ext import commands, menus
from index import EMBED_COLOUR, config, emojis
from utils import default


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.help_command = FormattedHelp()
        self.bot._original_help_command = bot.help_command


def cog_unload(self):
    self.bot.help_command = self.bot._original_help_command


class HelpMenu(menus.ListPageSource):
    def __init__(self, data, per_page):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu, entries):
        return entries


class FormattedHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={"usage": "`tp!help (command/category)`"}, hidden=True
        )

    def rem_lead_space(s, strict=False):
        if s and not strict and s[0] == "\n":
            s = s[1:]
        lines = s.splitlines(True)
        max_spaces = -1
        for line in lines:
            if line != "\n":
                for idx, c in enumerate(lines[:max_spaces]):
                    if not c == " ":
                        break
                max_spaces = idx + 1
        return "".join([l if l == "\n" else l[max_spaces - 1 :] for l in lines])

    async def send_command_help(self, command):
        self.context
        e = discord.Embed(
            title=f"Help - {command.qualified_name} {random.choice(emojis.rainbow_emojis)}",
            description=f"{command.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            color=EMBED_COLOUR,
        )
        e.add_field(name="Usage", value=command.usage)
        e.set_footer(
            text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and Fearful"
        )
        await self.get_destination().send(embed=e)

    async def send_group_help(self, group):
        ctx = self.context
        e = discord.Embed(
            title=f"Help - {group.qualified_name} {random.choice(emojis.rainbow_emojis)}",
            description=f"{group.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
            color=EMBED_COLOUR,
        )
        e.set_footer(
            text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and Fearful"
        )
        embeds = [e]
        for command in group.commands:
            e = discord.Embed(
                title=f"Help - {command.qualified_name} {random.choice(emojis.rainbow_emojis)}",
                description=f"{command.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                color=EMBED_COLOUR,
            )
            e.add_field(name="Usage", value=command.usage)
            e.set_footer(
                text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and Fearful"
            )
            embeds.append(e)
        menu = menus.MenuPages(source=HelpMenu(embeds, per_page=1))
        await menu.start(ctx)

    async def send_cog_help(self, cog):
        ctx = self.context
        e = discord.Embed(
            title=f"Help - {cog.qualified_name} {random.choice(emojis.rainbow_emojis)}",
            description=getattr(cog, "__doc__", discord.Embed.Empty),
            color=EMBED_COLOUR,
        )
        e.set_footer(
            text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and Fearful"
        )
        embeds = [e]
        for command in cog.walk_commands():
            if isinstance(command, commands.Group) or getattr(command, "hidden"):
                continue
            e = discord.Embed(
                title=f"Help - {command.qualified_name} {random.choice(emojis.rainbow_emojis)}",
                description=f"{command.help}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host}) | [Hosting]({config.host})",
                color=EMBED_COLOUR,
            )
            if command.usage:
                e.add_field(name="Usage", value=command.usage)
                e.add_field(name="Support Server", value=f"[Click Me]({config.Server})")
            e.set_footer(
                text=f"{self.context.bot.user.name} by Motzumoto, iPlay G, and Fearful"
            )
            embeds.append(e)
        menu = menus.MenuPages(source=HelpMenu(embeds, per_page=1))
        await menu.start(ctx)

    async def send_bot_help(self, mapping):
        async with self.context.typing():
            nsfw_cog = self.context.bot.get_cog("nsfw")
            nsfw_commands = nsfw_cog.get_commands()
            nsfw_q = [c.name for c in nsfw_commands if not c.hidden]
            nsfw_names = "".join(f"`{name}`, " for index, name in enumerate(nsfw_q))

            info_cog = self.context.bot.get_cog("info")
            info_commands = info_cog.get_commands()
            info_q = [c.name for c in info_commands if not c.hidden]
            info_names = "".join(f"`{name}`, " for index, name in enumerate(info_q))

            economy_cog = self.context.bot.get_cog("economy")
            economy_commands = economy_cog.get_commands()
            economy_q = [c.name for c in economy_commands if not c.hidden]
            economy_names = "".join(
                f"`{name}`, " for index, name in enumerate(economy_q)
            )

            fun_cog = self.context.bot.get_cog("fun")
            fun_commands = fun_cog.get_commands()
            fun_q = [c.name for c in fun_commands if not c.hidden]
            fun_names = "".join(f"`{name}`, " for index, name in enumerate(fun_q))

            guild_cog = self.context.bot.get_cog("discord")
            guild_commands = guild_cog.get_commands()
            guild_q = [c.name for c in guild_commands if not c.hidden]
            guild_names = "".join(f"`{name}`, " for index, name in enumerate(guild_q))

            mod_cog = self.context.bot.get_cog("mod")
            mod_commands = mod_cog.get_commands()
            mod_q = [c.name for c in mod_commands if not c.hidden]
            mod_names = "".join(f"`{name}`, " for index, name in enumerate(mod_q))

            music_cog = self.context.bot.get_cog("music")
            music_commands = music_cog.get_commands()
            music_q = [c.name for c in music_commands if not c.hidden]
            music_names = "".join(f"`{name}`, " for index, name in enumerate(music_q))

            if self.context.channel.is_nsfw():
                description = f"""For help on individual commands, use `tp!help <command>`.\n\n**{random.choice(emojis.rainbow_emojis)} {info_cog.qualified_name.capitalize()}**\n{info_names}\n\n**{random.choice(emojis.rainbow_emojis)} {economy_cog.qualified_name.capitalize()}**\n{economy_names}\n\n**{random.choice(emojis.rainbow_emojis)} {fun_cog.qualified_name.capitalize()}**\n{fun_names}\n\n**{random.choice(emojis.rainbow_emojis)} {guild_cog.qualified_name.capitalize()}**
                {guild_names}\n\n**{random.choice(emojis.rainbow_emojis)} {mod_cog.qualified_name.capitalize()}**\n{mod_names}\n\n**{random.choice(emojis.rainbow_emojis)} {music_cog.qualified_name.capitalize()}**\n{music_names}\n\n**{random.choice(emojis.rainbow_emojis)} {nsfw_cog.qualified_name.capitalize()}**\n{nsfw_names}"""

                embed = discord.Embed(
                    color=EMBED_COLOUR,
                    description=f"{description}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                )
                embed.set_footer(
                    text="If there is anything that you would like to see / changed, run 𝐭𝐩!𝐬𝐮𝐠𝐠𝐞𝐬𝐭 with your suggestion!\nAlso check out our server host!"
                )
                embed.set_thumbnail(url=self.context.bot.user.avatar_url)
                await self.get_destination().send(embed=embed)
                return
            else:
                description = f"""**{random.choice(emojis.rainbow_emojis)} {info_cog.qualified_name.capitalize()}**\n{info_names}\n\n**{random.choice(emojis.rainbow_emojis)} {economy_cog.qualified_name.capitalize()}**\n{economy_names}\n\n**{random.choice(emojis.rainbow_emojis)} {fun_cog.qualified_name.capitalize()}**\n{fun_names}\n\n**{random.choice(emojis.rainbow_emojis)} {guild_cog.qualified_name.capitalize()}**\n{guild_names}\n\n**{random.choice(emojis.rainbow_emojis)} {mod_cog.qualified_name.capitalize()}**\n{mod_names}\n\n**{random.choice(emojis.rainbow_emojis)} {music_cog.qualified_name.capitalize()}**\n{music_names}\n\n**{random.choice(emojis.rainbow_emojis)} {nsfw_cog.qualified_name.capitalize()}**\nNsfw commands are hidden. To see them, run `tp!help` in an NSFW channel."""

                embed = discord.Embed(
                    color=EMBED_COLOUR,
                    description=f"{description}\n[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Hosting]({config.host})",
                )
                embed.set_footer(
                    text="If there is anything that you would like to see / changed, run 𝐭𝐩!𝐬𝐮𝐠𝐠𝐞𝐬𝐭 with your suggestion!\nAlso check out our server host!"
                )
                embed.set_thumbnail(url=self.context.bot.user.avatar_url)
                await self.get_destination().send(embed=embed)
                return

def setup(bot):
    bot.add_cog(Help(bot))
    bot.get_command("help").hidden = True

