### IMPORTANT ANNOUNCEMENT ###
#
# All additions to AGB will now cease.
# AGB's management will be limited to the following:
# - Optimization
# - Bug Fixes
# - Basic Maintenance
#
# DO NOT ADD ANY NEW FEATURES TO AGB
# ALL NEW FEATURES WILL BE RESERVED FOR MEKU
#
### IMPORTANT ANNOUNCEMENT ###


import discord

# import statcord
import logging
import os
import random
from discord.ext import commands
import re


import Manager.database
import Manager.logger

from datetime import datetime
from discord.ext.commands import AutoShardedBot

from utils import default, permissions, slash
from colorama import init, Fore, Back, Style
import logging


init()

# logger = logging.getLogger("discord")
# logger.setLevel(logging.INFO)
# handler = logging.FileHandler(
#     filename=f"StartLogs/{default.date()}.log", encoding="utf-8", mode="w"
# )
# handler.setFormatter(
#     logging.Formatter(
#         "[%(name)s][%(levelname)s]  | %(message)s (%(asctime)s)",
#         datefmt="%B %d, %I:%M %p %Z",
#     )
# )
# logger.addHandler(handler)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format=f"{Style.DIM + '(%(asctime)s)' + Style.RESET_ALL} [{Fore.CYAN + '%(levelname)s' +  Style.RESET_ALL}]: {'%(message)s'}",
    datefmt="[%a]-%I:%M-%p",
)


config = default.get("config.json")
emojis = default.get("emojis.json")
db_config = default.get("db_config.json")

EMBED_COLOUR = 0xB54176

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
BID = "157421"
CHAT_API_KEY = ""

mydb_n = Manager.database.db2
cursor_n = Manager.database.csr2


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
            allowed_mentions=discord.AllowedMentions(
                roles=False, users=True, everyone=False, replied_user=False
            ),
        )
        self.launch_time = datetime.utcnow()
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1.0, random.randint(1, 5), commands.BucketType.guild
        )
        self.nword_re = re.compile(
            r"(n|m|и|й)(i|1|l|!|ᴉ|¡)(g|ƃ|6|б)(g|ƃ|6|б)(e|3|з|u)(r|Я)", re.I
        )
        self.slash_commands = {}
        self.logger = logging.getLogger("slashbot")

    def run(self, token: str) -> None:
        self.setup()

        super().run(token)

    def setup(self) -> None:
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                bot.load_extension(f"Cogs.{name}")

    def add_cog(self, cog, *, override=False):
        super().add_cog(cog, override=override)
        for item in cog.__dir__():
            item = getattr(cog, item, None)
            if isinstance(item, slash.SlashCommand):
                item.cog = cog
                self.slash_commands[item.path] = item
                for alias in item.aliases:
                    self.slash_commands[alias] = item

    def remove_cog(self, name):
        removed_cog = super().remove_cog(name)
        if removed_cog is None:
            return None
        for item in removed_cog.__dir__():
            item = getattr(removed_cog, item, None)
            if (
                isinstance(item, slash.SlashCommand)
                and item.path in self.slash_commands
            ):
                del self.slash_commands[item.path]
        return removed_cog

    async def on_interaction(self, interaction):
        # Filter out non-slash command interactions
        if interaction.type != discord.InteractionType.application_command:
            return
        # Only accept interactions that occurred in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                content="Commands cannot be used in DMs."
            )
            return

        ctx = slash.SlashContext(self, interaction)
        args, path = slash.prepare_args(interaction)
        ctx.path = path
        if path not in self.slash_commands:
            await interaction.response.send_message(
                content="That command is not available right now. Try again later.",
                ephemeral=True,
            )
            return

        command = self.slash_commands[path]
        await ctx._interaction.response.defer(ephemeral=True)
        try:
            await command.callback(command.cog, ctx, *args)
        except Exception as e:
            await ctx.send("`The command encountered an error. Try again in a moment.`")
            self.logger.exception(f"Error in command {ctx.path}\n{e}")

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
            except:
                pass
            result = cursor_n.fetchall()
            for row in result:
                embed = discord.Embed(
                    title="Hi! My name is AGB!",
                    url=f"{Website}",
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
                if retry_after:
                    return
                else:
                    if msg.reference is not None:
                        return
                    else:
                        if random.randint(1, 2) == 1:
                            return
                        else:
                            await msg.channel.send(embed=embed)
                            return

        await self.process_commands(msg)

    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        if before.author.bot:
            return
        bot.dispatch("message", after)


intents = discord.Intents.default()
intents.members = True

bot = Bot(intents)

os.environ.setdefault("JISHAKU_HIDE", "1")
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

# key = config.statcord
# api = statcord.Client(bot, key)
# api.start_loop()


@bot.check
def no_badwords(ctx):
    return "n word" not in ctx.message.content.lower()


@bot.check
def no_nwords(ctx):
    return "reggin" not in ctx.message.content.lower()


bot.run(config.token)

# datefmt="%B %d, %I:%M %p %Z"

# logger = logging.getLogger('AGB_Log')
# logger.setLevel(logging.INFO)

# handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# handler.setFormatter(Manager.logger.AgbFormatter())
# logger.propagate = False
# logger.addHandler(handler)
