import discord
from discord import app_commands
from discord.ext import commands

from utils import default

owners = default.config()["owners"]


def is_owner(ctx):
    """Checks if the author is one of the owners"""
    return ctx.author.id in owners


async def is_owner_slash(interaction):
    """Checks if the interaction user is one of the owners"""
    await interaction.response.defer(ephemeral=True, thinking=True)
    if interaction.user.id in owners:
        return True
    await interaction.followup.send(
        "You are not one of the owners of this bot. You can't use this command.",
        ephemeral=True,
    )
    return False


async def check_permissions(ctx, perms, *, check=all):
    """Checks if author has permissions to a permission"""
    if ctx.author.id in owners:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


async def slash_check_permissions(
    interaction: discord.Interaction, perms, *, check=all
):
    """Checks if author has permissions to a permission"""

    if interaction.user.id in owners:
        return True
    resolved = interaction.channel.permissions_for(interaction.user)
    check(getattr(resolved, name, None) == value for name, value in perms.items())
    return


def dynamic_ownerbypass_cooldown(rate: int, per: float, type):
    def actual_func(message):
        return None if message.author.id in owners else commands.Cooldown(rate, per)

    return commands.dynamic_cooldown(actual_func, type)


def has_permissions(*, check=all, **perms):
    """discord.Commands method to check if author has permissions"""

    async def pred(ctx):
        if ctx.author.id in owners:
            return True
        else:
            return await check_permissions(ctx, perms, check=check)

    return commands.check(pred)


def slash_has_permissions(*, check=all, **perms):
    """discord.app_commands method to check if author has permissions"""

    async def pred(interaction):
        if interaction.user.id in owners:
            return True
        else:
            return await slash_check_permissions(interaction, perms, check=check)

    return app_commands.check(pred)


async def slash_check_priv(interaction: discord.Interaction, member: discord.Member):
    """Custom (weird) way to check permissions when handling moderation commands"""
    embed = discord.Embed(
        title="Permission Denied", color=0xFF0000, description="No lol."
    )
    embed2 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {interaction.command.name} yourself.",
    )
    embed3 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"I'm not going to let you {interaction.command.name} my owner.",
    )
    embed4 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {interaction.command.name} the owner of this server.",
    )
    embed5 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {interaction.command.name} someone who has the same permissions as you.",
    )
    embed6 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {interaction.command.name} due to the role hierarchy.",
    )
    # Self checks
    if member.id == interaction.client.user.id:
        return await interaction.followup.send(embed=embed)
    if member == interaction.user:
        return await interaction.followup.send(embed=embed2)

    # Check if user bypasses
    if interaction.user.id == interaction.guild.owner.id:
        return False

    # Now permission check
    if member.id in owners and interaction.user.id not in owners:
        return await interaction.followup.send(embed=embed3)
    if member.id == interaction.guild.owner.id:
        return await interaction.followup.send(embed=embed4)
    if interaction.user.top_role == member.top_role:
        return await interaction.followup.send(embed=embed5)
    if interaction.user.top_role < member.top_role:
        return await interaction.followup.send(embed=embed6)


async def check_priv(ctx, member):
    """Custom (weird) way to check permissions when handling moderation commands"""
    embed = discord.Embed(
        title="Permission Denied", color=0xFF0000, description="No lol."
    )
    embed2 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {ctx.command.name} yourself.",
    )
    embed3 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"I'm not going to let you {ctx.command.name} my owner.",
    )
    embed4 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {ctx.command.name} the owner of this server.",
    )
    embed5 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {ctx.command.name} someone who has the same permissions as you.",
    )
    embed6 = discord.Embed(
        title="Permission Denied",
        color=0xFF0000,
        description=f"You can't {ctx.command.name} due to the role hierarchy.",
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
        if member.id in owners and ctx.author.id not in owners:
            return await ctx.send(embed=embed3)
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
