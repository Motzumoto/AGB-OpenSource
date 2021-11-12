import discord
import mysql.connector
import asyncio
import aiomysql
from discord.ext import commands, tasks
from utils import default
import psycopg

config = default.get("db_config.json")
config2 = default.get("db_config.new.json")

db = mysql.connector.connect(
    host=config.host,
    user=config.user,
    password=config.password,
    database=config.database,
    port=config.port,
    buffered=True,
    autocommit=True,
)

db2 = psycopg.connect(
    dbname=config2.database,
    user=config2.user,
    password=config2.password,
    host=config2.host,
)
db2.autocommit = True

csr2 = db2.cursor()

csr = db.cursor()
