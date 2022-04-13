import psycopg
import asyncio
import asyncpg
from utils import default

config = default.get("db_config.json")

db2 = psycopg.connect(
    dbname=config.database,
    user=config.user,
    password=config.password,
    host=config.host,
)
db2.autocommit = True

csr2 = db2.cursor()

# NEW DB MANAGER
loop = asyncio.get_event_loop()
POSTGRES_INFO = {
    "user": f"{config.user}",
    "password": f"{config.password}",
    "database": f"{config.database}",
    "host": f"{config.host}",
}

pool = loop.run_until_complete(asyncpg.create_pool(**POSTGRES_INFO))
