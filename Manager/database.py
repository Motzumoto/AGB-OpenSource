import discord
import mysql.connector
from discord.ext import commands, tasks
from utils import default

config = default.get("db_config.json")

db = mysql.connector.connect(
    host=config.host,
    user=config.user,
    password=config.password,
    database=config.database,
    port=config.port,
    buffered=True,
    autocommit=True,
)

csr = db.cursor()
