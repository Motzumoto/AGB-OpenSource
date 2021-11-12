import discord
import statcord
import logging
import os
import random
from discord.ext import commands

import Manager.database
import Manager.logger

from datetime import datetime
from cogwatch import watch
from discord.ext.commands import AutoShardedBot

from utils import default, permissions


logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename=f"StartLogs/{default.date()}.log", encoding="utf-8", mode="w"
)
handler.setFormatter(
    logging.Formatter(
        "[%(name)s][%(levelname)s]  | %(message)s (%(asctime)s)",
        datefmt="%B %d, %I:%M %p %Z",
    )
)
logger.addHandler(handler)

config = default.get("config.json")
emojis = default.get("emojis.json")
db_config = default.get("db_config.json")

EMBED_COLOUR = 0x3454DB

embed_space = "\u200b "
suggestion_yes = "<:checked:825049250110767114>"
suggestion_no = "<:zzz_playroomx:825049236802240563>"
delay = 10
Error = 0xE20000
TOP_GG_TOKEN = config.topgg
Website = "https://agb-dev.xyz"
Server = "https://discord.gg/cNRNeaX"
Vote = "https://top.gg/bot/723726581864071178/vote"
Invite = "https://discord.com/api/oauth2/authorize?client_id=723726581864071178&permissions=470150214&scope=bot"
BID = "157421"
CHAT_API_KEY = ""

mydb_n = Manager.database.db2
cursor_n = Manager.database.csr2

mydb = Manager.database.db
cursor = Manager.database.csr


class Bot(AutoShardedBot):
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

    @watch(path="Cogs")
    async def on_ready(self) -> str:
        return print("Cogwatch loaded in for the Cogs path")

    def run(self, token: str) -> None:
        self.setup()

        super().run(token, bot=True, reconnect=True)

    def setup(self) -> None:
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                if name != "music":
                    bot.load_extension(f"Cogs.{name}")

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
                    text="agb-dev.xyz",
                    icon_url=msg.author.avatar_url,
                )
                bucket = self.message_cooldown.get_bucket(msg)
                retry_after = bucket.update_rate_limit()
                if retry_after:
                    return
                else:
                    await msg.channel.send(embed=embed, delete_after=25)
                    mydb_n.commit()

        await self.process_commands(msg)

    async def on_command(self, ctx):
        try:
            api.command_run(ctx)
        except:
            pass

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

key = config.statcord
api = statcord.Client(bot, key)
api.start_loop()


bot.run(config.token)

# datefmt="%B %d, %I:%M %p %Z"

# logger = logging.getLogger('AGB_Log')
# logger.setLevel(logging.INFO)

# handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# handler.setFormatter(Manager.logger.AgbFormatter())
# logger.propagate = False
# logger.addHandler(handler)
