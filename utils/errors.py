from discord.ext.commands.errors import CheckFailure
from typing import Any


class DatabaseError(Exception):
    def __init__(self, error: Any):
        self.original: Any = error
        self.message: str = str(error)
        super().__init__(self.message)


class DisabledCommand(CheckFailure):
    def __init__(self):
        super().__init__(":x: This command has been disabled!")


class GlobalDisabledCommand(CheckFailure):
    def __init__(self):
        super().__init__(":x: This command has been disabled!")
