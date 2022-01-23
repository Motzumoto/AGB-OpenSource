import discord
import asyncio
from enum import Enum
import time


class SlashOptions(Enum):
    """Stores the option values for slash commands."""

    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4  # any integer between -2^53 and 2^53
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7  # any channel type / category
    ROLE = 8
    MENTIONABLE = 9  # users and roles
    NUMBER = 10  # any float between -2^53 and 2^53


class CommandType(Enum):
    """Stores the type of command."""

    SLASH = 1
    USER = 2
    MESSAGE = 3


class SlashContext:
    """Drop in `ctx` replacement for a slash interactions."""

    def __init__(self, bot, interaction):
        self._interaction = interaction
        self.author = interaction.user
        self.message = interaction.message
        self.guild = interaction.guild
        self.channel = interaction.channel
        self.bot = bot
        self.created_at = discord.Object(interaction.id).created_at
        if self.guild is not None:
            gid = self.guild.id
        else:
            gid = "@me"
        self.jump_url = f"https://discord.com/channels/{gid}/{self.channel.id}/{self._interaction.id}"
        self.path = None  # to be set by on_interaction
        self.args = None  # to be set by on_interaction
        self._created_at = time.time()

    async def send(self, content=None, **kwargs):
        """Sends a message using the appropriate method in the given context."""
        if "content" in kwargs:
            content = kwargs["content"]
        # The followup token is expiring soon, just send to the channel.
        if self._created_at + (60 * 12) < time.time():
            return await self.channel.send(content, **kwargs)
        # We already sent a response to the interaction, send a followup instead.
        try:
            return await self._interaction.followup.send(content, wait=True, **kwargs)
        # The token expired probably? Just send to the channel...
        except discord.HTTPException:
            return await self.channel.send(content, **kwargs)


class SlashMember:
    """A `discord.Member` equivalent that has only the data provided by slash commands."""

    def __init__(self, guild, id, username, discriminator, nick, permissions):
        self.guild = guild
        self.id = id
        self.name = username
        self.discriminator = discriminator
        self.nick = nick
        self.display_name = nick or username
        self.guild_permissions = permissions
        self.mention = f"<@{id}>"

    def __str__(self):
        return self.name + "#" + self.discriminator


class SlashCommand:
    """A command object for a slash command."""

    def __init__(self, func, path, aliases):
        self.path = path
        self.aliases = aliases
        self.callback = func
        self.cog = None  # to be set in add_cog


def command(path=None, aliases=[]):
    """
    A decorator that can be added to async functions to make them slash commands.

        from core import slash

        @slash.command()
        async def mycommand(self, ctx):
            pass

        @slash.command()
        async def group_command(self, ctx):
            pass

        @slash.command(path=("ping",))
        async def pingcommand(self, ctx):
            pass

    The `path` parameter can be used to denote the command path to use,
    if not provided it defaults to
    `command_subcommand_subcommand` -> `("command", "subcommand", "subcommand")`

    The `alias` parameter is a currently hacky way to support user and message commands,
    the single-deep name of the user/message command should be provided as a single element tuple.
    ie `@slash.command(aliases=[("Ban User",)])`
    """

    def wrapper(func):
        # Without this line, `path` is not properly defined. Thanks python.
        nonlocal path
        if path is None:
            path = tuple(func.__name__.split("_"))
        return SlashCommand(func, path, aliases)

    return wrapper


def prepare_args(interaction):
    """Resolves the raw argument data provided into objects."""
    path = [interaction.data["name"]]
    command_type = CommandType(interaction.data["type"])
    if command_type == CommandType.USER:
        target_id = interaction.data["target_id"]
        user_data = interaction.data["resolved"]["users"][target_id]
        mem_data = interaction.data["resolved"]["members"][target_id]
        mem = SlashMember(
            interaction.guild,
            int(target_id),
            user_data["username"],
            user_data["discriminator"],
            mem_data["nick"],
            discord.Permissions(int(mem_data["permissions"])),
        )
        return [mem], tuple(path)
    # There are no args or subcommands
    if "options" not in interaction.data:
        return [], tuple(path)
    return recursive_options(
        interaction.data["options"],
        {} if "resolved" not in interaction.data else interaction.data["resolved"],
        path,
        interaction.guild,
    )


def recursive_options(options: list, resolved: dict, path: list, guild):
    args = []
    for option in options:
        option_type = SlashOptions(option["type"])
        if option_type in (SlashOptions.SUB_COMMAND, SlashOptions.SUB_COMMAND_GROUP):
            path.append(option["name"])
            if "options" in option:
                return recursive_options(option["options"], resolved, path, guild)
        elif option_type == SlashOptions.STRING:
            args.append(option["value"])
        elif option_type == SlashOptions.INTEGER:
            args.append(int(option["value"]))
        elif option_type == SlashOptions.BOOLEAN:
            args.append(bool(option["value"]))
        elif option_type == SlashOptions.USER:
            user_data = resolved["users"][option["value"]]
            mem_data = resolved["members"][option["value"]]
            mem = SlashMember(
                guild,
                int(user_data["id"]),
                user_data["username"],
                user_data["discriminator"],
                mem_data["nick"],
                discord.Permissions(int(mem_data["permissions"])),
            )
            args.append(mem)
        elif option_type == SlashOptions.CHANNEL:
            args.append(guild.get_channel(int(option["value"])))
        elif option_type == SlashOptions.ROLE:
            args.append(guild.get_role(int(option["value"])))
        elif option_type == SlashOptions.MENTIONABLE:
            raise NotImplementedError()
        elif option_type == SlashOptions.NUMBER:
            args.append(float(option["value"]))
    return args, tuple(path)
