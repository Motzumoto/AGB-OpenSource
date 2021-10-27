import aiohttp
from discord.ext import commands
from index import TOP_GG_TOKEN
from utils import default

owners = default.get("config.json").owners


async def check_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


def has_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)

    return commands.check(pred)


async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


def has_guild_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_permissions(ctx, perms, check=check)

    return commands.check(pred)


class NotVoted(commands.CheckFailure):
    pass


async def check_voter(user_id):
    if user_id in owners:
        return True
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"https://top.gg/api/bots/723726581864071178/check?userId={user_id}",
            headers={"Authorization": TOP_GG_TOKEN, "Content-Type": "application/json"},
        ) as r:
            vote = await r.json()
            if vote["voted"] == 1:
                return True
            else:
                return False


def voter_only():
    async def predicate(ctx):
        if ctx.author.id in owners:
            return True
        check_vote = await check_voter(ctx.author.id)
        if not check_vote:
            raise NotVoted("Please vote!")
        return True

    return commands.check(predicate)


# These do not take channel overrides into account


def is_mod():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {"manage_guild": True})

    return commands.check(pred)


def is_admin():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {"administrator": True})

    return commands.check(pred)


def mod_or_permissions(**perms):
    perms["manage_guild"] = True

    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)

    return commands.check(predicate)


def admin_or_permissions(**perms):
    perms["administrator"] = True

    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)

    return commands.check(predicate)


def is_in_guilds(*guild_ids):
    def predicate(ctx):
        guild = ctx.guild
        if guild is None:
            return False
        return guild.id in guild_ids

    return commands.check(predicate)
