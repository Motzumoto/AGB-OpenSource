import discord
import logging
import os
import asyncio
import random
from discord.ext import commands
from discord import app_commands


import Manager.database
import Manager.logger
from Manager.logger import formatColor

from datetime import datetime

from utils import imports, permissions
from colorama import Fore, Style, init
import logging


try:
    import uvloop  # type: ignore
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

init()
discord.http._set_api_version(9)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format=f"{f'{Style.DIM}(%(asctime)s){Style.RESET_ALL}'} [{Fore.CYAN}%(levelname)s{Style.RESET_ALL}]: %(message)s",
    datefmt="[%a]-%I:%M-%p",
)



config = imports.get("config.json")
emojis = imports.get("emojis.json")
db_config = imports.get("db_config.json")

EMBED_COLOUR = 0x2F3136

embed_space = "\u200b "
suggestion_yes = "<:checked:825049250110767114>"
suggestion_no = "<:zzz_playroomx:825049236802240563>"
delay = 10
Error = 0xE20000
TOP_GG_TOKEN = config.topgg
Website = "https://lunardev.group"
Server = "https://discord.gg/cNRNeaX"
Vote = "https://top.gg/bot/723726581864071178/vote"
Invite = "https://discord.com/api/oauth2/authorize?client_id=723726581864071178&permissions=2083908950&scope=bot"
BID = "notforyou"
CHAT_API_KEY = "notforyou"

mydb_n = Manager.database.db2
cursor_n = Manager.database.csr2

slash_errors = (
    app_commands.CommandOnCooldown,
    app_commands.BotMissingPermissions,
    app_commands.CommandInvokeError,
    app_commands.MissingPermissions,
)


async def create_slash_embed(self, interaction, error):
    await interaction.response.defer(ephemeral=True, thinking=True)
    embed = discord.Embed(title="Error", colour=0xFF0000)
    embed.add_field(name="Author", value=interaction.user.mention)
    embed.add_field(name="Error", value=error)
    embed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
    await interaction.followup.send(embed=embed, ephemeral=True)


def msgtracking(user):
    try:
        cursor_n.execute(f"SELECT * FROM users WHERE userid = '{user}'")
        row = cursor_n.fetchall()[0][4]
    except Exception:
        return True
    return row is True


async def update_command_usages(self, interaction):
    try:
        cursor_n.execute(
            f"SELECT * FROM public.users WHERE userid = '{interaction.user.id}'"
        )
        row = cursor_n.fetchall()

        cursor_n.execute(
            f"UPDATE public.users SET usedcmds = '{row[0][1] + 1}' WHERE userid = '{interaction.user.id}'"
        )
        # logger.info(f"Updated userCmds for {ctx.author.id} -> {row[0][3]}")
    except Exception:
        pass


class MyCustomTree(app_commands.CommandTree):
    async def call(self, interaction):
        await super().call(interaction)
        if interaction.user.id in config.owners:
            logger.info(
                f"{formatColor('[DEV]', 'bold_red')} {formatColor(interaction.user, 'red')} used command {formatColor(interaction.command.name, 'grey')}"
            )
            return
        else:
            logger.info(
                f"{formatColor(interaction.user.id, 'grey')} used command {formatColor(interaction.command.name, 'grey')}"
            )


class Bot(commands.AutoShardedBot):
    def __init__(self, intents: discord.Intents, *args, **kwargs) -> None:
        # Getting kwargs -> .get('kwarg_name', 'default_value')
        self.default_prefix = kwargs.get("default_prefix", "tp!")
        self.embed_color = kwargs.get("embed_color", 0x3454DB)

        super().__init__(
            command_prefix=self.default_prefix,
            strip_after_prefix=True,
            case_insensitive=True,
            owner_ids=config.owners,
            help_command=None,
            command_attrs=dict(hidden=True),
            activity=discord.Game(name="initializing..."),
            shard_count=1,
            chunk_guilds_at_startup=False,
            intents=intents,
            tree_cls=MyCustomTree,
            allowed_mentions=discord.AllowedMentions(
                roles=False, users=True, everyone=False, replied_user=False
            ),
        )
        self.launch_time = datetime.utcnow()
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1.0, random.randint(1, 5), commands.BucketType.guild
        )

    async def setup(self) -> None:
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                await self.load_extension(f"Cogs.{name}")

    async def setup_hook(self):
        await self.setup()

    async def close(self):
        await super().close()
        await self.session.close()

    async def on_message(self, msg) -> None:
        if not self.is_ready() or msg.author.bot or not permissions.can_send(msg):
            return
        if msg.content.lower().startswith("tp!"):
            msg.content = msg.content[: len("tp!")].lower() + msg.content[len("tp!") :]
        if bot.user in msg.mentions:
            try:
                cursor_n.execute(
                    f"SELECT prefix FROM public.guilds WHERE guildId = '{msg.guild.id}'"
                )
            except Exception:
                pass
            result = cursor_n.fetchall()
            for row in result:
                try:
                    embed = discord.Embed(
                        title="Hi! My name is AGB!",
                        url=Website,
                        colour=EMBED_COLOUR,
                        description=f"If you like me, please take a look at the links below!\n[Add me]({config.Invite}) | [Support Server]({config.Server}) | [Vote]({config.Vote})",
                        timestamp=msg.created_at,
                    )
                    embed.add_field(name="Prefix for this server:", value=f"{row[0]}")
                    embed.add_field(name="Help command", value=f"{row[0]}help")
                    embed.set_footer(
                        text="lunardev.group",
                        icon_url=msg.author.avatar,
                    )
                    mydb_n.commit()
                    bucket = self.message_cooldown.get_bucket(msg)
                    retry_after = bucket.update_rate_limit()
                    if (
                        not retry_after
                        and msg.reference is None
                        and random.randint(1, 2) != 1
                    ):
                        await msg.channel.send(embed=embed)
                    return
                except Exception:
                    await msg.channel.send(
                        f"**Hi, My name is AGB!**\nIf you like me and want to know more information about me, please enable embed permissions in your server settings so I can show you more information!\nIf you don't know how, please join the support server and ask for help!\n{config.Server}"
                    )

        await self.process_commands(msg)

    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        if before.author.bot:
            return
        bot.dispatch("message", after)


intents = discord.Intents.default()
intents.members = True
# intents.message_content = True

bot = Bot(intents)

os.environ.setdefault("JISHAKU_HIDE", "1")
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"


@bot.check
def no_badwords(ctx):
    return "n word" not in ctx.message.content.lower()


@bot.check
def no_nwords(ctx):
    return "reggin" not in ctx.message.content.lower()


if __name__ == "__main__":
    bot.run(config.token)
