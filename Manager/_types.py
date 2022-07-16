from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict

if TYPE_CHECKING:
    from datetime import date

__all__: tuple[str, ...] = (
    "DBConfig",
    "UserEconomy",
    "User",
    "Guild",
    "AutoMod",
    "AutoPosting",
    "Badges",
    "Blacklist",
    "GuildBlacklist",
    "GlobalVars",
    "Reminders",
    "Status",
)


class DBConfig(NamedTuple):
    host: str
    user: str
    password: str
    database: str
    port: str


class UserEconomy(TypedDict):
    userid: Any
    balance: int
    bank: int
    lastdaily: date
    isbot: Any


class User(TypedDict):
    userid: Any
    usedcmds: int
    bio: Any
    blacklisted: Any
    msgtracking: bool


class Guild(TypedDict):
    guildid: Any
    hentaichannel: Any
    prefix: Any


class AutoMod(TypedDict):
    server: Any
    log: Any


class AutoPosting(TypedDict):
    guild_id: Any
    hentai_id: Any


class AutoRoles(TypedDict):
    role: int  # primary
    enabled: bool


class Badges(TypedDict):
    userid: Any
    owner: Any
    admin: Any
    mod: Any
    partner: Any
    support: Any
    friend: Any


class Blacklist(TypedDict):
    userid: Any
    blacklisted: Any


class GuildBlacklist(TypedDict):
    id: Any
    name: Any
    blacklisted: bool


class GlobalVars(TypedDict):
    variableName: Any
    variableData: float
    variableData2: Any


class Reminders(TypedDict):
    user: Any
    length: Any
    reminder: Any


class Status(TypedDict):
    id: int
    status: Any
