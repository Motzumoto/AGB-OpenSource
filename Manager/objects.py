from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from discord.utils import MISSING

if TYPE_CHECKING:
    from datetime import date

    from typing_extensions import Self

    from ._types import AutoMod as AutoModData
    from ._types import AutoPosting as AutoPostingData
    from ._types import AutoRoles as AutoRolesData
    from ._types import Blacklist as BlacklistData
    from ._types import GlobalVars as GlobalVarsData
    from ._types import Guild as GuildData
    from ._types import GuildBlacklist as GuildBlacklistData
    from ._types import Reminders as RemindersData
    from ._types import Status as StatusData
    from ._types import User as UserData
    from ._types import UserEconomy as UserEconomyData
    from .database import Database


__all__: tuple[str, ...] = (
    "Table",
    "Badges",
    "table_to_cls",
    "AutoMod",
    "AutoPosting",
    "AutoRole",
    "Badge",
    "Blacklist",
    "Command",
    "Guild",
    "GuildBlacklist",
    "GlobalVar",
    "Reminder",
    "Status",
    "User",
    "UserEconomy",
)


def _handle_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        return value.lower() == "true"
    else:
        return False


def _handle_null_or_int(value: Any) -> Optional[int]:
    return int(value) if value else None


class Table(Enum):
    AUTOMOD = "automod"
    AUTOPOSTING = "autoposting"
    AUTOROLES = "autoroles"
    BADGES = "badges"
    BLACKLIST = "blacklist"
    COMMANDS = "commands"
    GLOBALVARS = "globalvars"
    GUILDBLACKLIST = "guildblacklist"
    GUILDS = "guilds"
    REMINDERS = "reminders"
    STATUS = "status"
    USER_ECONOMY = "usereco"
    USERS = "users"

    def __str__(self) -> str:
        return self.value


class Badges(Enum):
    owner = "owner"
    admin = "admin"
    mod = "mod"
    partner = "partner"
    support = "support"
    friend = "friend"
    user = "user"


class Base:
    table: str
    columns: tuple[str, ...]
    database: Database
    data: Any

    if TYPE_CHECKING:

        def __init__(self, database: Database, /, *, data: Any) -> None:
            ...

    def __getitem__(self, key: str) -> Any:
        return self.data[key] if key in self.data else None

    def __getattr__(self, name: str) -> Any:
        return self.data[name] if name in self.data else getattr(self, name)

    def _handle_query_inputs(
        self, *, where: dict[str, Any], **kwargs
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        if any(key not in self.columns for key in kwargs):
            raise ValueError(
                f"Invalid column name, must be one of: {', '.join(self.columns)}"
            )
        inputs = {}
        index = 1

        values: list[Any] = []
        for key, value in where.items():
            where[key] = f"${index}"
            values.insert(index, value)
            index += 1

        for key, value in kwargs.items():
            inputs[key] = f"${index}"
            values.insert(index, value)
            index += 1

        return where, inputs, values

    async def handle_execute(self, *, where: dict[str, Any], **kwargs) -> Any:
        _where, _inputs, _values = self._handle_query_inputs(where=where, **kwargs)
        where = where or _where
        query = f"UPDATE {self.table} SET {', '.join(f'{key} = {value}' for key, value in _inputs.items())}"
        if _where:
            query += " WHERE " + " AND ".join(
                f"{key} = {value}" for key, value in _where.items()
            )
        query += " RETURNING *"
        data = await self.database.fetchrow(query, *_values)
        return self.__class__(self.database, data=dict(data))  # type: ignore


class UserEconomy(Base):
    table: str = "usereco"
    columns = ("balance", "bank", "lastdaily", "isbot")

    def __init__(self, database: Database, /, data: UserEconomyData) -> None:
        self.database = database
        self.data = data

        self.user_id: int = _handle_null_or_int(data["userid"])  # type: ignore
        self.balance: int = int(data["balance"])
        self.bank: int = int(data["bank"])
        self.lastdaily: date = data["lastdaily"]
        self.isbot = _handle_bool(data["isbot"])

    async def modify(
        self,
        *,
        balance: Optional[int] = None,
        bank: Optional[int] = None,
        lastdaily: Optional[date] = None,
        isbot: Optional[bool] = MISSING,
    ) -> User:
        kwargs = {}
        if balance is not None:
            kwargs["balance"] = balance
        if bank is not None:
            kwargs["bank"] = bank
        if lastdaily is not None:
            kwargs["lastdaily"] = lastdaily
        if isbot is not MISSING:
            kwargs["isbot"] = str(isbot).lower()
        return await Base.handle_execute(
            self, where={"userid": str(self.user_id)}, **kwargs
        )


class User(Base):
    table = "users"
    columns = ("userid", "usedcmds", "bio", "blacklisted", "msgtracking")

    def __init__(self, database: Database, /, data: UserData) -> None:
        self.data: UserData = data
        self.database: Database = database

        self.user_id: int = _handle_null_or_int(data["userid"])  # type: ignore
        self.used_commands: int = int(data["usedcmds"])
        self.bio: Optional[str] = data["bio"]
        self.is_blacklisted: bool = _handle_bool(data["blacklisted"])
        self.message_tracking: bool = _handle_bool(data["msgtracking"])

    async def modify(
        self,
        *,
        usedcmds: Optional[int] = None,
        bio: Optional[str] = None,
        blacklisted: Optional[bool] = None,
        msgtracking: Optional[bool] = None,
    ) -> User:
        kwargs = {}
        if usedcmds is not None:
            kwargs["usedcmds"] = usedcmds
        if bio is not None:
            kwargs["bio"] = bio
        if blacklisted is not None:
            kwargs["blacklisted"] = str(blacklisted).lower()
        if msgtracking is not None:
            kwargs["msgtracking"] = msgtracking

        return await Base.handle_execute(
            self, where={"userid": str(self.user_id)}, **kwargs
        )


class Command(Base):
    table = "commands"
    columns = ("guild",)

    def __init__(self, database: Database, /, *, name: str) -> None:
        self.name: str = name
        self.columns = self.columns + (name,)

        self.database: Database = database

        self.states: dict[int, Optional[str]] = {}
        # key = guild_id, value = state ("true", "false" or None)

    def _handle_state_bool(self, value: Optional[str]) -> Optional[bool]:

        return None if value is None else value == "true"

    async def fill_guild_ids(self) -> None:
        query = f"SELECT guild, {self.name} FROM {self.table}"
        data = await self.database.fetch(query)
        for entry in data:
            guild_id = entry["guild"]
            self.states[int(guild_id)] = entry[self.name]

    def state_in(self, guild_id: int) -> Optional[bool]:
        guild_command = self.states.get(guild_id)
        return self._handle_state_bool(guild_command)

    async def modify(
        self,
        guild_id: int,
        state: Optional[bool] = None,
    ) -> Self:
        query = f"UPDATE {self.table} SET {self.name} = $1 WHERE guild = $2 RETURNING *"

        values = [str(state).lower() if state else None, str(guild_id)]
        data = await self.database.fetchrow(query, *values)
        self.states[guild_id] = data[self.name]  # type: ignore
        return self


class Guild(Base):
    table = "guilds"
    columns = ("hentaichannel", "prefix")

    def __init__(self, database: Database, /, data: GuildData) -> None:
        self.data: GuildData = data
        self.database: Database = database

        self.id: int = str(data["guildid"])
        self.hentai_channel_id: Optional[str] = _handle_null_or_int(
            data["hentaichannel"]
        )
        self.prefix: Optional[str] = data["prefix"]

    async def modify(
        self,
        *,
        hentai_channel_id: Optional[int] = MISSING,
        prefix: Optional[Any] = MISSING,
    ) -> Guild:
        kwargs = {}
        if hentai_channel_id is not MISSING:
            kwargs["hentaichannel"] = (
                str(hentai_channel_id) if hentai_channel_id else None
            )
        if prefix is not MISSING:
            kwargs["prefix"] = prefix

        return await Base.handle_execute(
            self, where={"guildid": str(self.id)}, **kwargs
        )


class AutoMod(Base):
    table = "automod"
    columns = ("server", "log")

    def __init__(self, database: Database, /, data: AutoModData) -> None:
        self.data: AutoModData = data
        self.database: Database = database

        self.guild_id: int = int(data["server"])
        self.log_channel_id: Optional[int] = _handle_null_or_int(data["log"])

    async def modify(
        self,
        *,
        log: Optional[int] = MISSING,
    ) -> AutoMod:
        kwargs = {}
        if log is not MISSING:
            kwargs["log"] = str(log) if log else None

        return await Base.handle_execute(
            self, where={"server": self.guild_id}, **kwargs
        )


class AutoPosting(Base):
    table = "autoposting"
    columns = (
        "guild_id",
        "hentai_id",
    )

    def __init__(self, database: Database, /, data: AutoPostingData) -> None:
        self.data: AutoPostingData = data
        self.database: Database = database

        self.guild_id: int = int(data["guild_id"])
        self.hentai_id: Optional[int] = _handle_null_or_int(data["hentai_id"])

    async def modify(
        self,
        *,
        hentai_id: Optional[int] = MISSING,
    ) -> AutoPosting:
        kwargs = {}
        if hentai_id is not MISSING:
            kwargs["hentai_id"] = str(hentai_id) if hentai_id else None

        return await Base.handle_execute(
            self, where={"guild_id": str(self.guild_id)}, **kwargs
        )


class AutoRole(Base):
    table = "autoroles"
    columns = ("role", "enabled")

    def __init__(self, database: Database, /, data: AutoRolesData) -> None:
        self.data: AutoRolesData = data
        self.database: Database = database

        self.role_id: int = int(data["role"])
        self.enabled: bool = _handle_bool(data["enabled"])

    async def modify(
        self,
        *,
        enabled: bool,
    ) -> AutoRole:
        return await Base.handle_execute(
            self, where={"role": self.role_id}, enabled=enabled
        )


class Badge(Base):
    table = "badges"
    columns = tuple()

    def __init__(self, database: Database, /, *, name: str) -> None:
        self.database: Database = database

        self.name: str = name
        # key = user_id, value = bool
        self.users: dict[int, bool] = {}

    async def fill_users_ids(self) -> None:
        query = f"SELECT userid, {self.name} FROM {self.table}"
        data = await self.database.fetch(query)
        for entry in data:
            user_id = entry["userid"]
            self.users[int(user_id)] = _handle_bool(entry[self.name])

    def has_badge(self, user_id: int) -> bool:
        return self.users.get(user_id, False)

    async def modify(
        self,
        user_id: int,
        state: Optional[bool] = None,
    ) -> Self:
        query = (
            f"UPDATE {self.table} SET {self.name} = $1 WHERE userid = $2 RETURNING *"
        )

        values = [str(state).lower() if state else None, str(user_id)]
        data = await self.database.fetchrow(query, *values)
        self.users[user_id] = data[self.name]  # type: ignore
        return self


class Blacklist(Base):
    table = "blacklist"
    columns = ("userid", "blacklisted")

    def __init__(self, database: Database, /, data: BlacklistData) -> None:
        self.data: BlacklistData = data
        self.database: Database = database

        self.user_id: int = int(data["userid"])
        self.is_blacklisted: bool = _handle_bool(data["blacklisted"])

    async def modify(self, *, blacklisted: Optional[bool] = MISSING) -> Blacklist:
        kwargs = {}
        if blacklisted is not MISSING:
            kwargs["blacklisted"] = str(blacklisted).lower() if blacklisted else None
        return await Base.handle_execute(
            self, where={"userid": str(self.user_id)}, **kwargs
        )


class GuildBlacklist(Base):
    table = "guildblacklist"
    columns = ("id", "name", "blacklisted")

    def __init__(self, database: Database, /, data: GuildBlacklistData) -> None:
        self.data: GuildBlacklistData = data
        self.database: Database = database

        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.is_blacklisted: bool = _handle_bool(data["blacklisted"])

    async def modify(
        self,
        *,
        where: dict[str, Any] = {},
        name: Optional[str] = MISSING,
        blacklisted: Optional[bool] = MISSING,
    ) -> GuildBlacklist:
        where = where or {"id": str(self.guild_id)}
        kwargs = {}
        if name is not MISSING:
            kwargs["name"] = str(name) if name else None
        if blacklisted is not MISSING:
            kwargs["blacklisted"] = str(blacklisted).lower() if blacklisted else None
        return await Base.handle_execute(self, where=where, **kwargs)


class Reminder(Base):
    table = "reminders"
    columns = ("user", "length", "reminder")

    def __init__(self, database: Database, /, data: RemindersData) -> None:
        self.data: RemindersData = data
        self.database: Database = database

        self.user_id: int = int(data["user"])
        self.length: str = data["length"]
        self.reminder: Optional[str] = data["reminder"]

    async def modify(
        self,
        *,
        reminder: Optional[str] = MISSING,
        length: Optional[str] = MISSING,
    ) -> Reminder:
        kwargs = {}
        if reminder is not MISSING:
            kwargs["reminder"] = str(reminder) if reminder else None
        if length is not MISSING:
            kwargs["length"] = str(length) if length else None
        return await Base.handle_execute(self, where={"user": self.user_id}, **kwargs)


class Status(Base):
    table = "status"
    columns = ("id", "status")

    def __init__(self, database: Database, /, data: StatusData) -> None:
        self.data: StatusData = data
        self.database: Database = database

        self.id: int = int(data["id"])
        self.status: str = data["status"]

    async def modify(self, status: str, *, where: dict[str, Any] = {}) -> Status:
        where = where or {"id": self.id}
        return await Base.handle_execute(self, where=where, status=status)


class GlobalVar(Base):
    table = "globalvars"
    columns = ("variableName", "variableData", "variableData2")

    def __init__(self, database: Database, /, data: GlobalVarsData) -> None:
        self.data: GlobalVarsData = data
        self.database: Database = database

        self.variableName: str = str(data["variableName"])
        self.variableData: float = float(data["variableData"])
        self.variableData2: Any = data["variableData2"]

    async def modify(
        self,
        *,
        variableData: Optional[float] = None,
        variableData2: Optional[Any] = MISSING,
    ) -> GlobalVar:
        kwargs = {}
        if variableData is not None:
            kwargs["variableData"] = float(variableData)
        if variableData2 is not MISSING:
            kwargs["variableData2"] = str(variableData2) if variableData2 else None
        return await Base.handle_execute(
            self, where={"variableName": self.variableName}, **kwargs
        )


table_to_cls: dict[Table, Any] = {
    Table.AUTOMOD: AutoMod,
    Table.AUTOPOSTING: AutoPosting,
    Table.AUTOROLES: AutoRole,
    Table.BADGES: Badge,
    Table.BLACKLIST: Blacklist,
    Table.COMMANDS: Command,
    Table.GUILDS: Guild,
    Table.GUILDBLACKLIST: GuildBlacklist,
    Table.GLOBALVARS: GlobalVar,
    Table.REMINDERS: Reminder,
    Table.STATUS: Status,
    Table.USERS: User,
    Table.USER_ECONOMY: UserEconomy,
}
