
import logging
import os
from datetime import datetime

# import dbl
import discord
import Manager.database
import statcord
from utils import default
import asyncio
from utils.data import Bot

# reimplement uvloop

try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(
    logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


config = default.get("config.json")
emojis = default.get("emojis.json")
db_config = default.get("db_config.json")

default_prefix = "tp!"
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

mydb = Manager.database.db
cursor = Manager.database.csr

intents = discord.Intents.default()
intents.members = True
bot = Bot(
    owner_ids=config.owners,
    command_prefix=default_prefix,
    prefix=default_prefix,
    command_attrs=dict(hidden=True),
    help_command=None,
    activity=discord.Game(name="initializing..."),
    # shard_count = 3,
    chunk_guilds_at_startup=False,
    intents=intents,
    allowed_mentions=discord.AllowedMentions(
        roles=False, users=True, everyone=False, replied_user=False),
    case_insensitive=True,
    strip_after_prefix=True
)

bot.launch_time = datetime.utcnow()

for file in os.listdir("Cogs"):
    if file.endswith(".py"):
        name = file[:-3]
        if name != "music":
            bot.load_extension(f"Cogs.{name}")

os.environ.setdefault("JISHAKU_HIDE", "1")
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

key = config.statcord
api = statcord.Client(bot, key)
api.start_loop()


@bot.event
async def on_command(ctx):
    try:
        api.command_run(ctx)
    except:
        pass



@bot.event
async def on_message_edit(before, after):
    if before.content == after.content:
        return
    if before.author.bot:
        return
    bot.dispatch("message", after)


@bot.check
def no_badwords(ctx):
    return 'N word' not in ctx.message.content.lower()


@bot.check
def no_nwords(ctx):
    return 'Reversed N Word' not in ctx.message.content.lower()


bot.run(config.token)
