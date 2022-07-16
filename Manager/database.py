from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional, Union, overload

from asyncpg import Pool, Record, create_pool
from utils.errors import DatabaseError

from .logger import formatColor
from .objects import *

if TYPE_CHECKING:
    from index import Bot

    from ._types import DBConfig

DATABASE_LOGGING_PREFIX = formatColor("[Database]", "green")


class Connection:

    __slots__: tuple[str, ...] = ("bot", "_config", "_pool")

    def __init__(
        self,
        bot: Bot,
        /,
        config: DBConfig,
    ) -> None:
        self.bot: Bot = bot
        self._config = config
        self._pool: Optional[Pool] = None

    @property
    def pool(self) -> Pool:
        return self._pool  # type: ignore

    async def create_connection(self) -> None:
        if self._pool is not None and not self._pool._closed:
            return

        pool: Pool = await create_pool(
            user=self._config.user,
            password=self._config.password,
            host=self._config.host,
            database=self._config.database,
            port=self._config.port,
        )  # type: ignore
        self._pool = pool

        # circular imports
        from utils.default import log

        log(
            f"{DATABASE_LOGGING_PREFIX} Successfully created a connection to the database."
        )

    async def execute(self, query, *args) -> Any:
        con = await self.pool.acquire()
        try:
            return await con.execute(query, *args)
        except Exception as e:
            raise DatabaseError(e) from e
        finally:
            await self.pool.release(con)

    async def executemany(self, query, *args) -> Any:
        con = await self.pool.acquire()
        try:
            return await con.executemany(query, *args)
        except Exception as e:
            raise DatabaseError(e) from e
        finally:
            await self.pool.release(con)

    async def fetch(self, query, *args) -> list[Record]:  # type: ignore
        con = await self.pool.acquire()
        try:
            return await con.fetch(query, *args)
        except Exception as e:
            raise DatabaseError(e) from e
        finally:
            await self.pool.release(con)

    async def fetchrow(self, query, *args) -> Optional[Record]:
        con = await self.pool.acquire()
        try:
            return await con.fetchrow(query, *args)
        except Exception as e:
            raise DatabaseError(e) from e
        finally:
            await self.pool.release(con)

    async def fetchval(self, query, *args) -> Optional[Any]:
        con = await self.pool.acquire()
        try:
            return await con.fetchval(query, *args)
        except Exception as e:
            raise DatabaseError(e) from e
        finally:
            await self.pool.release(con)

    async def close(self) -> None:
        if self._pool is None:
            return

        await self._pool.close()
        self._pool = None


class Database(Connection):
    def __init__(
        self,
        bot: Bot,
        /,
        config: DBConfig,
    ) -> None:
        super().__init__(bot, config=config)

        # cache

        # key = command_name, value = Command (object)
        self._commands: dict[str, Command] = {}
        # key = user_id, value = User (object)
        self._users: dict[int, User] = {}
        # key = user_id, value = UserEconomy (object)
        self._economy_users: dict[int, UserEconomy] = {}
        # key = guild_id, value = Guild (object)
        self._guilds: dict[int, Guild] = {}
        # key = guild_id, value = AutoMod (object)
        self._automods: dict[int, AutoMod] = {}
        # key = guild_id, value = AutoPosting (object)
        self._autopostings: dict[int, AutoPosting] = {}
        # key = role_id, value = AutoRoles (object)
        self._autoroles: dict[int, AutoRole] = {}
        # key = badge name, value = Badge (object)
        self._badges: dict[str, Badge] = {}
        # key = user_id, value = Blacklist (object)
        self._blacklists: dict[int, Blacklist] = {}
        # key = guild_id, value = GuildBlacklist (object)
        self._guild_blacklists: dict[int, GuildBlacklist] = {}
        # key = id, value = Status (object)
        self._statuses: dict[int, Status] = {}
        # key = user_id, value = Reminder (object)
        self._reminders: dict[int, Reminder] = {}
        # key = name, value = GlobalVar (object)
        self._global_vars: dict[str, GlobalVar] = {}

        self._table_to_cache: dict[Table, tuple[str, dict[Any, Any]]] = {
            Table.USERS: ("userid", self._users),
            Table.USER_ECONOMY: ("userid", self._economy_users),
            Table.GUILDS: ("guildid", self._guilds),
            Table.REMINDERS: ("user", self._reminders),
            Table.COMMANDS: ("placeholder", self._commands),
            Table.AUTOMOD: ("server", self._automods),
            Table.AUTOPOSTING: ("guild_id", self._autopostings),
            Table.AUTOROLES: ("role", self._autoroles),
            Table.BADGES: ("userid", self._badges),
            Table.BLACKLIST: ("userid", self._blacklists),
            Table.GLOBALVARS: ("variableName", self._global_vars),
            Table.GUILDBLACKLIST: ("id", self._guild_blacklists),
            Table.STATUS: ("id", self._statuses),
        }

    async def initate_database(self, *, chunk: bool = True) -> None:
        # circular imports
        from utils.default import log

        log(f"{DATABASE_LOGGING_PREFIX} Initializing database...")
        await self.create_connection()
        if chunk:
            log(f"{DATABASE_LOGGING_PREFIX} Chunking database...")
            await self.chunk(all=True)
            log(f"{DATABASE_LOGGING_PREFIX} Chunking database... Done!")

        log(f"{DATABASE_LOGGING_PREFIX} Database initialized.")

    async def chunk(
        self,
        all: bool = False,
        *,
        auto_mod: bool = False,
        auto_posting: bool = False,
        auto_roles: bool = False,
        badges: bool = False,
        blacklist: bool = False,
        commands: bool = False,
        global_vars: bool = False,
        guild_blacklists: bool = False,
        guilds: bool = False,
        reminders: bool = False,
        statuses: bool = False,
        users: bool = False,
        user_economy: bool = False,
    ) -> None:
        cache: bool = False

        auto_mod = auto_mod or all
        auto_posting = auto_posting or all
        auto_roles = auto_roles or all
        badges = badges or all
        blacklist = blacklist or all
        commands = False  # commands or all
        global_vars = global_vars or all
        guild_blacklists = guild_blacklists or all
        guilds = guilds or all
        reminders = reminders or all
        statuses = statuses or all
        users = users or all  # users or all
        user_economy = user_economy or all
        badges = badges or all

        # circular imports
        from utils.default import log

        LOG_CHUNKING_PREFIX = f"{DATABASE_LOGGING_PREFIX} Chunking "
        LOG_CHUNKING_TEXT = "{0} {1}..."
        if auto_mod:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "automod"))
            objs = await self.fetch_automods(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "automod")
                + f" Done! Chunked {len(objs)} entries."
            )
        if auto_posting:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "autoposting"))
            objs = await self.fetch_autopostings(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "autoposting")
                + f" Done! Chunked {len(objs)} entries."
            )
        if auto_roles:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "autoroles"))
            objs = await self.fetch_autoroles(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "autoroles")
                + f" Done! Chunked {len(objs)} entries."
            )
        if badges:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "badges"))
            objs = await self.fetch_badges(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "badges")
                + f" Done! Chunked {len(objs)} entries."
            )
        if blacklist:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "blacklist"))
            objs = await self.fetch_blacklists(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "blacklist")
                + f" Done! Chunked {len(objs)} entries."
            )
        if commands:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "commands"))
            objs = await self.fetch_commands(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "commands")
                + f" Done! Chunked {len(objs)} entries."
            )
        if guilds:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "guilds"))
            objs = await self.fetch_guilds(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "guilds")
                + f" Done! Chunked {len(objs)} entries."
            )
        if global_vars:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "global vars"))
            objs = await self.fetch_global_vars(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "global vars")
                + f" Done! Chunked {len(objs)} entries."
            )
        if guild_blacklists:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "guild blacklists"))
            objs = await self.fetch_guild_blacklists(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "guild blacklists")
                + f" Done! Chunked {len(objs)} entries."
            )
        if reminders:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "reminders"))
            objs = await self.fetch_reminders(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "reminders")
                + f" Done! Chunked {len(objs)} entries."
            )
        if statuses:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "statuses"))
            objs = await self.fetch_statuses(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "statuses")
                + f" Done! Chunked {len(objs)} entries."
            )
        if users:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "users"))
            objs = await self.fetch_users(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "users")
                + f" Done! Chunked {len(objs)} entries."
            )
        if user_economy:
            log(LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "user economy"))
            objs = await self.fetch_economy_users(cache=cache)
            log(
                LOG_CHUNKING_TEXT.format(LOG_CHUNKING_PREFIX, "user economy")
                + f" Done! Chunked {len(objs)} entries."
            )

    @overload
    async def __fetch(
        self, table: Table, cache: Any, where: Literal[None] = ...
    ) -> list[Any]:
        ...

    @overload
    async def __fetch(self, table: Any, cache: Any, where: Any) -> Optional[Any]:
        ...

    async def __fetch(
        self,
        table: Table,
        cache: bool = False,
        where: Optional[dict[str, Any]] = None,
    ) -> Union[list[Any], Optional[Any]]:
        query = f"SELECT * FROM {table.value}"
        _cache = self._table_to_cache[table]
        cls = table_to_cls[table]

        if where is not None:
            query += " WHERE " + " AND ".join(
                f"{k} = ${i}" for i, (k, v) in enumerate(where.items(), start=1)
            )
            data = await self.fetchrow(query, *where.values())
            if not data:
                return None

            if cache:
                key, cache_dict = _cache
                cache_dict[data[key]] = cls(self, dict(data))

            return cls(self, dict(data))

        entries = await self.fetch(
            query,
        )
        to_ret = []
        for entry in entries:
            inst = cls(self, dict(entry))
            if cache:
                key, cache_dict = _cache
                dict_key_value = entry[key]
                dict_key_value = (
                    int(dict_key_value)
                    if dict_key_value.isdigit()
                    else str(dict_key_value)
                )
                cache_dict[dict_key_value] = inst

            to_ret.append(inst)

        return to_ret

    # commands

    async def add_command(self, command_name) -> Command:
        query = f"ALTER TABLE {Table.COMMANDS} ADD COLUMN IF NOT EXISTS {command_name.lower()} VARCHAR(75)"
        await self.execute(query)
        inst = Command(self, name=command_name)
        await inst.fill_guild_ids()
        self._commands[command_name] = inst
        return inst

    async def remove_command(self, command_name) -> Optional[Command]:
        query = f"ALTER TABLE {Table.COMMANDS} DROP COLUMN {command_name.lower()}"
        await self.execute(query)
        return self._commands.pop(command_name, None)

    def get_command(self, command_name) -> Optional[Command]:
        return self._commands.get(command_name)

    async def fetch_commands(self, cache: bool = False) -> list[Command]:
        to_return = []
        data = await self.fetchrow(f"SELECT * FROM {Table.COMMANDS}")
        for key in data.keys():  # type: ignore
            if key != "guild":
                inst = Command(self, name=key)
                await inst.fill_guild_ids()
                to_return.append(inst)

        if cache:
            self._commands = {b.name: b for b in to_return}

        return to_return

    async def fetch_command(
        self, command_name, cache: bool = False
    ) -> Optional[Command]:
        query = f"SELECT {command_name} FROM {Table.COMMANDS}"
        try:
            data = await self.fetchrow(query)
        except DatabaseError:
            return None

        if data is None:
            return None

        inst = Command(self, name=command_name)
        await inst.fill_guild_ids()
        if cache:
            self._commands[command_name] = inst
        return inst

    # users

    async def add_user(self, user_id: int) -> User:
        query = f"INSERT INTO {Table.USERS} (userid) VALUES ($1) RETURNING *"
        data = await self.fetchrow(query, str(user_id))
        return User(self, dict(data))

    async def remove_user(self, user_id: int) -> Optional[User]:
        query = f"DELETE FROM {Table.USERS} WHERE userid = $1"
        await self.execute(query, str(user_id))
        return self._users.pop(user_id, None)

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    async def fetch_users(self, cache: bool = False) -> list[User]:
        return await self.__fetch(Table.USERS, cache=cache)

    async def fetch_user(self, user_id: int, cache: bool = False) -> Optional[User]:
        return await self.__fetch(
            Table.USERS, cache=cache, where={"userid": str(user_id)}
        )

    # economy

    async def add_economy_user(
        self, user_id: int, *, balance: int = 0, bank: int = 0
    ) -> UserEconomy:
        query = f"INSERT INTO {Table.USER_ECONOMY} (userid, balance, bank) VALUES ($1, $2, $3) RETURNING *"
        data = await self.fetchrow(query, str(user_id), balance, bank)
        inst = UserEconomy(self, dict(data))  # type: ignore
        self._economy_users[user_id] = inst
        return inst

    async def remove_economy_user(self, user_id: int) -> Optional[UserEconomy]:
        query = f"DELETE FROM {Table.USER_ECONOMY} WHERE userid = $1"
        await self.execute(query, str(user_id))
        return self._economy_users.pop(user_id, None)

    def get_economy_user(self, user_id: int) -> Optional[UserEconomy]:
        return self._economy_users.get(user_id)

    async def fetch_economy_users(self, cache: bool = False) -> list[UserEconomy]:
        return await self.__fetch(Table.USER_ECONOMY, cache=cache)

    async def fetch_economy_user(
        self, user_id: int, cache: bool = False
    ) -> Optional[UserEconomy]:
        return await self.__fetch(
            Table.USER_ECONOMY, cache=cache, where={"userid": str(user_id)}
        )

    # guilds

    async def add_guild(self, guild_id: int) -> Guild:
        query = f"INSERT INTO {Table.GUILDS} (guildid) VALUES ($1) RETURNING *"
        data = await self.fetchrow(query, str(guild_id))
        inst = Guild(self, dict(data))  # type: ignore
        self._guilds[guild_id] = inst
        return inst

    async def remove_guild(self, guild_id: int) -> Optional[Guild]:
        query = f"DELETE FROM {Table.GUILDS} WHERE guildid = $1"
        await self.execute(query, str(guild_id))
        return self._guilds.pop(guild_id, None)

    def get_guild(self, guild_id: int) -> Optional[Guild]:
        return self._guilds.get(guild_id)

    async def fetch_guilds(self, cache: bool = False) -> list[Guild]:
        return await self.__fetch(Table.GUILDS, cache=cache)

    async def fetch_guild(self, guild_id: int, cache: bool = False) -> Optional[Guild]:
        return await self.__fetch(
            Table.GUILDS, cache=cache, where={"guildid": str(guild_id)}
        )

    # automod

    async def add_automod(
        self, guild_id, log_channel_id: Optional[int] = None
    ) -> AutoMod:
        query = f"INSERT INTO {Table.AUTOMOD} (server) VALUES ($1) RETURNING *"
        if log_channel_id is not None:
            query = "INSERT INTO automod (server, log) VALUES ($1, $2) RETURNING *"
            data = await self.fetchrow(query, str(guild_id), str(log_channel_id))
        else:
            data = await self.fetchrow(query, str(guild_id))

        inst = Automod(self, dict(data))  # type: ignore
        self._automods[guild_id] = inst
        return inst

    async def remove_automod(self, guild_id) -> Optional[AutoMod]:
        query = f"DELETE FROM {Table.AUTOMOD} WHERE server = $1"
        await self.execute(query, guild_id)
        return self._automods.pop(guild_id, None)

    def get_automod(self, guild_id) -> Optional[AutoMod]:
        return self._automods.get(guild_id)

    async def fetch_automods(self, cache: bool = False) -> list[AutoMod]:
        return await self.__fetch(Table.AUTOMOD, cache=cache)

    async def fetch_automod(self, guild_id, cache: bool = False) -> Optional[AutoMod]:
        return await self.__fetch(
            Table.AUTOMOD, cache=cache, where={"server": str(guild_id)}
        )

    # autoposting

    async def add_autoposting(self, guild_id, hentai_channel_id: int) -> AutoPosting:
        query = f"INSERT INTO {Table.AUTOPOSTING} (guild_id, hentai_id) VALUES ($1, $2) RETURNING *"
        data = await self.fetchrow(query, str(guild_id), str(hentai_channel_id))
        inst = AutoPosting(self, dict(data))  # type: ignore
        self._autopostings[guild_id] = inst
        return inst

    async def remove_autoposting(self, guild_id) -> Optional[AutoPosting]:
        query = f"DELETE FROM {Table.AUTOPOSTING} WHERE guild_id = $1"
        await self.execute(query, str(guild_id))
        return self._autopostings.pop(guild_id, None)

    def get_autoposting(self, guild_id) -> Optional[AutoPosting]:
        return self._autopostings.get(guild_id)

    async def fetch_autopostings(self, cache: bool = False) -> list[AutoPosting]:
        return await self.__fetch(Table.AUTOPOSTING, cache=cache)

    async def fetch_autoposting(
        self, guild_id, cache: bool = False
    ) -> Optional[AutoPosting]:
        return await self.__fetch(
            Table.AUTOPOSTING, cache=cache, where={"guild_id": str(guild_id)}
        )

    # autoroles

    async def add_autorole(self, role_id, state: bool = False) -> AutoRole:
        query = (
            f"INSERT INTO {Table.AUTOROLES} (role, enabled) VALUES ($1, $2) RETURNING *"
        )
        data = await self.fetchrow(query, role_id, state)
        inst = AutoRole(self, dict(data))  # type: ignore
        self._autoroles[role_id] = inst
        return inst

    async def remove_autorole(self, role_id) -> Optional[AutoRole]:
        query = f"DELETE FROM {Table.AUTOROLES} WHERE role = $1"
        await self.execute(query, role_id)
        return self._autoroles.pop(role_id, None)

    def get_autorole(self, role_id) -> Optional[AutoRole]:
        return self._autoroles.get(role_id)

    async def fetch_autoroles(self, cache: bool = False) -> list[AutoRole]:
        return await self.__fetch(Table.AUTOROLES, cache=cache)

    async def fetch_autorole(self, role_id, cache: bool = False) -> Optional[AutoRole]:
        return await self.__fetch(Table.AUTOROLES, cache=cache, where={"role": role_id})

    # badges

    # TODO: this doesn't look right.
    async def add_badge(self, user_id, badge: Badges) -> Badge:
        query = f"INSERT INTO {Table.BADGES} (userid, {badge.value}) VALUES ($1) RETURNING *"
        data = await self.fetchrow(query, str(user_id))
        inst = Badge(self, name=badge.value)
        self._badges[badge.value] = inst
        return inst

    def get_badge(self, badge: Badges) -> Optional[Badge]:
        return self._badges.get(badge.value)

    async def fetch_badges(self, cache: bool = False) -> list[Badge]:
        to_return = []
        data = await self.fetchrow(f"SELECT * FROM {Table.BADGES}")
        for key in data.keys():  # type: ignore
            if key != "userid":
                inst = Badge(self, name=key)
                await inst.fill_users_ids()
                to_return.append(inst)

        if cache:
            self._badges = {b.name: b for b in to_return}

        return to_return

    async def fetch_badge(self, badge: Badges, cache: bool = False) -> Optional[Badge]:
        data = await self.fetchval(f"SELECT {badge.value} FROM {Table.BADGES.value}")
        if not data:
            return None

        inst = Badge(self, name=data[badge.value])  # type: ignore
        await inst.fill_users_ids()
        if cache:
            self._badges[badge.value] = inst

        return inst

    # blacklist

    async def add_blacklist(self, user_id: int, blacklisted: bool = False) -> Blacklist:
        query = f"INSERT INTO {Table.BLACKLIST} (userid, blacklisted) VALUES ($1, $2) RETURNING *"
        data = await self.fetchrow(query, str(user_id), str(blacklisted).lower())
        inst = Blacklist(self, dict(data))  # type: ignore
        self._blacklists[user_id] = inst
        return inst

    async def remove_blacklist(self, user_id: int) -> Optional[Blacklist]:
        query = f"DELETE FROM {Table.BLACKLIST} WHERE userid = $1"
        await self.execute(query, user_id)
        return self._blacklists.pop(user_id, None)

    def get_blacklist(self, user_id: int) -> Optional[Blacklist]:
        return self._blacklists.get(user_id)

    async def fetch_blacklists(self, cache: bool = False) -> list[Blacklist]:
        return await self.__fetch(Table.BLACKLIST, cache=cache)

    async def fetch_blacklist(
        self, user_id: int, cache: bool = False
    ) -> Optional[Blacklist]:
        return await self.__fetch(
            Table.BLACKLIST, cache=cache, where={"userid": str(user_id)}
        )

    # global vars

    async def add_global_var(
        self,
        variable_name,
        data: Optional[float] = None,
        data2: Optional[Any] = None,
    ) -> GlobalVar:
        query = f"INSERT INTO {Table.GLOBALVARS} (variableName, variableData, variableData2) VALUES ($1, $2, $3) RETURNING *"
        data = await self.fetchrow(query, variable_name, data, data2)
        inst = GlobalVar(self, dict(data))  # type: ignore
        self._global_vars[variable_name] = inst
        return inst

    async def remove_global_var(self, variable_name) -> Optional[GlobalVar]:
        query = f"DELETE FROM {Table.GLOBALVARS} WHERE variableName = $1"
        await self.execute(query, variable_name)
        return self._global_vars.pop(variable_name, None)

    def get_global_var(self, variable_name) -> Optional[GlobalVar]:
        return self._global_vars.get(variable_name)

    async def fetch_global_vars(self, cache: bool = False) -> list[GlobalVar]:
        return await self.__fetch(Table.GLOBALVARS, cache=cache)

    async def fetch_global_var(
        self, variable_name, cache: bool = False
    ) -> Optional[GlobalVar]:
        return await self.__fetch(
            Table.GLOBALVARS, cache=cache, where={"variableName": variable_name}
        )

    # guild blacklist

    async def add_guild_blacklist(
        self, guild_id, name: Optional[str] = None, blacklisted: bool = False
    ) -> GuildBlacklist:
        query = f"INSERT INTO {Table.GUILDBLACKLIST} (id, name, blacklisted) VALUES ($1, $2, $3) RETURNING *"
        data = await self.fetchrow(query, str(guild_id), name, blacklisted)
        inst = GuildBlacklist(self, dict(data))  # type: ignore
        self._guild_blacklists[guild_id] = inst
        return inst

    def get_guild_blacklist(self, guild_id) -> Optional[GuildBlacklist]:
        return self._guild_blacklists.get(guild_id)

    async def fetch_guild_blacklists(self, cache: bool = False) -> list[GuildBlacklist]:
        return await self.__fetch(Table.GUILDBLACKLIST, cache=cache)

    async def fetch_guild_blacklist(
        self, guild_id, cache: bool = False
    ) -> Optional[GuildBlacklist]:
        return await self.__fetch(
            Table.GUILDBLACKLIST, cache=cache, where={"id": str(guild_id)}
        )

    # reminders

    async def add_reminder(self, user_id, length, reminder) -> Reminder:
        query = f"INSERT INTO {Table.REMINDERS} VALUES ($1, $2, $3) RETURNING *"
        data = await self.fetchrow(query, str(user_id), length, reminder)
        inst = Reminder(self, dict(data))  # type: ignore
        self._reminders[user_id] = inst
        return inst

    async def remove_reminder(self, user_id) -> Optional[Reminder]:
        query = f"DELETE FROM {Table.REMINDERS} WHERE user = $1"
        await self.execute(query, str(user_id))
        return self._reminders.pop(user_id, None)

    def get_reminder(self, user_id) -> Optional[Reminder]:
        return self._reminders.get(user_id)

    async def fetch_reminders(self, cache: bool = False) -> list[Reminder]:
        return await self.__fetch(Table.REMINDERS, cache=cache)

    async def fetch_reminder(self, user_id, cache: bool = False) -> Optional[Reminder]:
        return await self.__fetch(
            Table.REMINDERS, cache=cache, where={"user": str(user_id)}
        )

    # status

    async def add_status(self, status_id, status) -> Status:
        query = f"INSERT INTO {Table.STATUS} (id, status) VALUES ($1, $2) RETURNING *"
        data = await self.fetchrow(query, status_id, status)
        inst = Status(self, dict(data))  # type: ignore
        self._statuses[status_id] = inst
        return inst

    async def remove_status(self, status_id) -> Optional[Status]:
        query = f"DELETE FROM {Table.STATUS} WHERE id = $1"
        await self.execute(query, status_id)
        return self._statuses.pop(status_id, None)

    def get_status(self, status_id) -> Optional[Status]:
        return self._statuses.get(status_id)

    async def fetch_statuses(self, cache: bool = False) -> list[Status]:
        return await self.__fetch(Table.STATUS, cache=cache)

    async def fetch_status(self, status_id, cache: bool = False) -> Optional[Status]:
        return await self.__fetch(Table.STATUS, cache=cache, where={"id": status_id})
