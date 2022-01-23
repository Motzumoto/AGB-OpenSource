from matplotlib.pyplot import title
import discord
from discord.ext import commands

from utils import default

owners = default.config()["owners"]


def is_owner(ctx):
    """Checks if the author is one of the owners"""
    return ctx.author.id in owners


async def check_permissions(ctx, perms, *, check=all):
    """Checks if author has permissions to a permission"""
    if ctx.author.id in owners:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


def has_permissions(*, check=all, **perms):
    """discord.Commands method to check if author has permissions"""

    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)

    return commands.check(pred)


async def check_priv(ctx, member):
    """Custom (weird) way to check permissions when handling moderation commands"""
    embed = discord.Embed(
        title="Permission Denied", color=0xFF0000, description="no lol are u dumb"
    )
    embed2 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"u really must be stupid to try to {ctx.command.name} urself",
    )
    embed3 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"ur a bit of an ass arent u, im not gonna let u {ctx.command.name} my owner",
    )
    embed4 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"u cant {ctx.command.name} the owner, dumbass",
    )
    embed5 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"u cant {ctx.command.name} someone who has the same perms as u",
    )
    embed6 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"u really thought u could {ctx.command.name} someone higher than u? pathetic",
    )
    try:
        # Self checks
        if member.id == ctx.bot.user.id:
            return await ctx.send(embed=embed)
        if member == ctx.author:
            return await ctx.send(embed=embed2)

        # Check if user bypasses
        if ctx.author.id == ctx.guild.owner.id:
            return False

        # Now permission check
        if member.id in owners:
            if ctx.author.id not in owners:
                return await ctx.send(embed=embed3)
            else:
                pass
        if member.id == ctx.guild.owner.id:
            return await ctx.send(embed=embed4)
        if ctx.author.top_role == member.top_role:
            return await ctx.send(embed=embed5)
        if ctx.author.top_role < member.top_role:
            return await ctx.send(embed=embed6)
    except Exception:
        pass


def can_send(ctx):
    return (
        isinstance(ctx.channel, discord.DMChannel)
        or ctx.channel.permissions_for(ctx.guild.me).send_messages
    )


def can_embed(ctx):
    return (
        isinstance(ctx.channel, discord.DMChannel)
        or ctx.channel.permissions_for(ctx.guild.me).embed_links
    )


def can_upload(ctx):
    return (
        isinstance(ctx.channel, discord.DMChannel)
        or ctx.channel.permissions_for(ctx.guild.me).attach_files
    )


def can_react(ctx):
    return (
        isinstance(ctx.channel, discord.DMChannel)
        or ctx.channel.permissions_for(ctx.guild.me).add_reactions
    )


def is_nsfw(ctx):
    return isinstance(ctx.channel, discord.DMChannel) or ctx.channel.is_nsfw()


def can_handle(ctx, permission: str):
    """Checks if bot has permissions or is in DMs right now"""
    return isinstance(ctx.channel, discord.DMChannel) or getattr(
        ctx.channel.permissions_for(ctx.guild.me), permission
    )
