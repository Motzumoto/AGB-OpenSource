import discord
import mysql.connector
import asyncio
import aiomysql
from discord.ext import commands, tasks
from utils import default
import psycopg

commandsEnabled = {}
