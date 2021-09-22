from cogwatch import watch
from discord.ext.commands import AutoShardedBot
from utils import default, permissions


class Bot(AutoShardedBot):
    def __init__(self, *args, prefix=None, **kwargs):
        super().__init__(*args, **kwargs)

    @watch(path="Cogs")
    async def on_ready(self):
        print(f"{default.date()} | Cogwatch loaded in for the Cogs path")

    async def on_message(self, msg):
        if not self.is_ready() or msg.author.bot or not permissions.can_send(msg):
            return

        await self.process_commands(msg)
