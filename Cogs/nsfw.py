import random

import aiohttp
import discord
import nekos
from discord.ext import commands
from index import config, EMBED_COLOUR, cursor, mydb
from utils import permissions
from utils.checks import *


class Nsfw(commands.Cog, name='nsfw', command_attrs=dict(nsfw=True)):
    """Spicy pictures"""

    def __init__(self, bot):
        self.bot = bot
        self.modules = ['nsfw_neko_gif', 'anal', 'les', 'hentai',
                        'bj', 'cum_jpg', 'tits', 'pussy_jpg', 'pwankg',
                        'classic', 'spank', 'boobs', 'random_hentai_gif']
        for command in self.walk_commands():
            command.nsfw = True

    async def cog_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def create_embed(self, ctx, error):
        embed = discord.Embed(title=f"Error Caught!",
                              color=discord.Colour.red(), description=f"{error}")
        embed.set_thumbnail(
            url=self.bot.user.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)

    async def get_hentai_img(self):
        if random.randint(1, 2) == 1:
            url = nekos.img(random.choice(self.modules))
        else:
            other_stuff = ['bondage', 'hentai', 'thighs']
            async with aiohttp.ClientSession() as s:
                async with s.get(f'https://shiro.gg/api/images/nsfw/{random.choice(other_stuff)}') as r:
                    j = await r.json()
                    url = j['url']
        return url

    @commands.command(aliases=['post', 'ap'], usage="`tp!ap #channel`")
    @voter_only()
    @commands.cooldown(rate=1, per=2.5, type=commands.BucketType.user)
    @permissions.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True, manage_channels=True, manage_webhooks=True)
    async def autopost(self, ctx, *, channel: discord.TextChannel):
        """Mention a channel to autopost hentai to. example: `tp!autopost #auto-nsfw`"""
        if not channel.is_nsfw():
            return await ctx.send("That shit isn't NSFW - fuck that.")
        # try:
        cursor.execute(
            f"SELECT hentai_channel FROM guilds WHERE guildID = {ctx.guild.id}")
        res = cursor.fetchall()

        if not channel.mention:
            await ctx.send("Please mention a channel for me to autopost to.")

        for row in res:
            if row[0] == None:
                cursor.execute(
                    f"UPDATE guilds SET hentai_channel = '{channel.id}' WHERE guildID = {ctx.guild.id}")
                mydb.commit()
                await ctx.send(f"{channel.mention} has been added to the database. I will start posting shortly!")
            else:
                await ctx.send("whoops, guild already has a fuckin' channel my dude")

        mydb.commit()

    @autopost.error
    async def autopost_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await self.create_embed(ctx, error)
            return
        elif isinstance(error, NotVoted):
            embed = discord.Embed(title="Error Caught!", color=discord.Colour.red(
            ), description=f"You need to vote to run this command! You can vote **[here]({config.Vote})**.")
            embed.set_thumbnail(
                url=self.bot.user.avatar_url_as(static_format="png"))
            await ctx.send(embed=embed)
            return           
            
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(title="Error Caught!", color=discord.Colour.red(
            ), description="Please send the channel you want me to autopost to.\nExample: `tp!autopost #auto-nsfw`")
            embed.set_thumbnail(
                url=self.bot.user.avatar_url_as(static_format="png"))
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.ChannelNotFound):
            embed = discord.Embed(title="Error Caught!", color=discord.Colour.red(
            ), description="Hey I couldn't find that channel! Please make sure you mentioned the channel.\nExample: `tp!autopost #auto-nsfw`")
            embed.set_thumbnail(
                url=self.bot.user.avatar_url_as(static_format="png"))
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.TooManyArguments):
            embed = discord.Embed(title="Error Caught!", color=discord.Colour.red(
            ), description="Hey don't do that! You sent too many channels for me to post to. I can only post to one channel per server, don't try to break me.")
            embed.set_thumbnail(
                url=self.bot.user.avatar_url_as(static_format="png"))
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.BotMissingPermissions):
            await self.create_embed(ctx, error)
            return
        elif isinstance(error, discord.Forbidden):
            await self.create_embed(ctx, error)
            return

    @commands.command(aliases=['apr'])
    @voter_only()
    @commands.cooldown(rate=1, per=2.5, type=commands.BucketType.user)
    @permissions.has_permissions(manage_channels=True)
    async def autopost_remove(self, ctx):
        """Remove the auto hentai posting channel."""

        cursor.execute(
            f"SELECT hentai_channel FROM guilds WHERE guildID = {ctx.guild.id}")
        res = cursor.fetchall()

        for row in res:
            if row[0] == None:
                await ctx.reply("you don't have a fukin' channel idot.")
            else:
                cursor.execute(
                    f"UPDATE guilds SET hentai_channel = NULL WHERE guildID = {ctx.guild.id}")
                await ctx.reply(f"Alright, your auto posting channel has been removed from our database.")

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def classic(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("classic"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def trap(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("trap"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def boobs(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("boobs"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def pussy(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("pussy"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def hentai(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=(await self.get_hentai_img()))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(aliases=['catgirl'])
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def neko(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("neko"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(aliases=['les', 'female'])
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def lesbian(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("les"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def tits(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("tits"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def wallpaper(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("wallpaper"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def anal(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("anal"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def feet(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("feet"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def hololewd(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("hololewd"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    @commands.guild_only()
    async def spank(self, ctx, *, user: discord.Member):
        user = user or ctx.author
        if user == ctx.author:
            embed = discord.Embed(
                title=f"{ctx.author} Spanks themselves...", colour=EMBED_COLOUR)
            embed.set_image(url=nekos.img("spank"))
            embed.set_footer(text=f" {ctx.author}",
                             icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{ctx.author} Spanks {user.name}...", colour=EMBED_COLOUR)
            embed.set_image(url=nekos.img("spank"))
            embed.set_footer(text=f" {ctx.author}",
                             icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def lewdkemo(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("lewdkemo"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def pwg(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("pwankg"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(hidden=True)
    @commands.check(permissions.is_owner)
    async def nsfwneko(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("nsfw_neko_gif"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def blowjob(self, ctx):
        embed = discord.Embed(title="Enjoy", description=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", colour=EMBED_COLOUR,
                              timestamp=ctx.message.created_at)
        embed.set_image(url=nekos.img("blowjob"))
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @voter_only()
    @commands.is_nsfw()
    async def thighs(self, ctx):
        async with aiohttp.ClientSession() as data:
            async with data.get('https://shiro.gg/api/images/nsfw/thighs') as r:
                data = await r.json()
                embed = discord.Embed(
                    colour=EMBED_COLOUR, timestamp=ctx.message.created_at)
                embed.set_image(url=data['url'])
                embed.set_footer(text=f" {ctx.author}",
                                 icon_url=ctx.author.avatar_url)
                embed.add_field(
                    name="Enjoy", value=f"[Add me]({self.config.Invite}) | [Support]({config.Server}) | [Vote]({self.config.Vote})", inline=False)
                await ctx.reply(embed=embed)

def setup(bot):
    bot.add_cog(Nsfw(bot))
