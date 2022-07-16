import discord
import DiscordUtils
import humanfriendly

from discord.ext import commands
from index import EMBED_COLOUR
from .Utils import success_embed
from datetime import datetime
import aiohttp
from DiscordUtils.Music import MusicPlayer
from utils import permissions
from utils.checks import Paginator, voter_only

music_ = DiscordUtils.Music()


class music(commands.Cog):
    """Jam to some awesome tunes! 🎶"""

    def __init__(self, bot):
        self.bot = bot
        self.skip_votes = {}
        self.session = aiohttp.ClientSession()

    def error_msg(self, error) -> str:
        if error == "not_in_same_vc":
            return ":x:You need to be in the same voice channel as me."
        elif error == "not_in_voice_channel":
            return ":x:You need to join a voice channel first."
        else:
            return "An error occured"

    def now_playing_embed(self, ctx, song) -> discord.Embed:
        return (
            discord.Embed(
                title=song.title,
                url=song.url,
                color=EMBED_COLOUR,
                timestamp=datetime.utcnow(),
                description=f"""
**Duration:** {humanfriendly.format_timespan(song.duration)}
**Channel:** [{song.channel}]({song.channel_url})
                        """,
            )
            .set_image(url=song.thumbnail)
            .set_footer(
                text=f"Loop: {'✅' if song.is_looping else '❌'}",
                icon_url=ctx.guild.icon.url
                if ctx.guild.icon is not None
                else "https://cdn.discordapp.com/embed/avatars/1.png",
            )
            .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        )

    @commands.command(aliases=["connect"])
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 5, commands.BucketType.user)
    async def join(self, ctx: commands.Context):
        """Make AGB join the voice channel"""
        if not ctx.author.voice:
            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if ctx.guild.me.voice and len(ctx.guild.me.voice.channel.members) > 1:

            return await ctx.reply("Someone else is already using the bot :c")
        # check if the song link is a spotify link
        if "open.spotify.com" in ctx.message.content:
            return await ctx.send("Spotify links are not supported")
        try:
            await ctx.author.voice.channel.connect()
            await ctx.message.add_reaction("✅")
            await ctx.guild.me.edit(deafen=True)
        except Exception as e:

            return await ctx.reply(
                f"I wasn't able to connect to your voice channel.\nPlease make sure I have enough permissions.\nError: {e}"
            )

    @commands.command(
        aliases=["dc", "disconnect"],
    )
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 5, commands.BucketType.user)
    async def leave(self, ctx: commands.Context):
        """Make AGB leave the voice channel"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not in a voice channel")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        if player := music_.get_player(guild_id=ctx.guild.id):
            try:
                await player.stop()
                await player.delete()
            except Exception:
                pass
        await ctx.voice_client.disconnect()
        await ctx.message.add_reaction("👋")

    @commands.command(aliases=["p"])
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 10, commands.BucketType.user)
    async def play(self, ctx, *, song_=None):
        """Play a song"""
        if "open.spotify.com" in ctx.message.content:
            return await ctx.send("Spotify links are not supported")
        if song_ is None:
            return await ctx.reply(
                f"Correct Usage: `{ctx.clean_prefix}play <song/url>`\nExample: `{ctx.clean_prefix}play Rick Roll`"
            )
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:
            await ctx.invoke(self.bot.get_command("join"))
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:
            player = music_.create_player(ctx, ffmpeg_error_betterfix=True)
        if not ctx.voice_client.is_playing():
            try:
                await player.queue(song_, search=True, bettersearch=True)
            except Exception:
                await player.queue(song_, search=True)
            song = await player.play()
            await ctx.send(embed=self.now_playing_embed(ctx, song))
            await ctx.guild.me.edit(deafen=True)
        else:
            try:
                song = await player.queue(song_, search=True, bettersearch=True)
            except Exception:
                song = await player.queue(song_, search=True)
            await ctx.send(
                embed=discord.Embed(
                    title=song.title,
                    url=song.url,
                    color=EMBED_COLOUR,
                    description=f"""
**Duration:** {humanfriendly.format_timespan(song.duration)}
**Channel:** [{song.channel}]({song.channel_url})
                            """,
                )
                .set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                .set_thumbnail(url=song.thumbnail)
                .set_footer(
                    text=f"Song added to queue | Loop: {'✅' if song.is_looping else '❌'}",
                    icon_url=ctx.guild.icon.url
                    if ctx.guild.icon is not None
                    else "https://cdn.discordapp.com/embed/avatars/1.png",
                )
            )

    @commands.command(aliases=["np"])
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 10, commands.BucketType.user)
    async def nowplaying(self, ctx):
        """Get the current song playing"""
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:
            return await ctx.reply("Nothing is playing rn.")
        if not ctx.voice_client.is_playing():
            return await ctx.reply("No music playing rn")
        song = player.now_playing()
        await ctx.reply(embed=self.now_playing_embed(ctx, song))

    @commands.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 10, commands.BucketType.user)
    async def pause(self, ctx):
        """Pause the current song"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not playing any songs")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:

            return await ctx.reply("I am not playing any songs")
        try:
            await player.pause()
        except DiscordUtils.NotPlaying:
            return await ctx.reply("I am not playing any songs")
        await ctx.message.add_reaction("⏸️")

    @commands.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 10, commands.BucketType.user)
    async def resume(self, ctx):
        """Resume the current song"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not in a voice channel")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:

            return await ctx.reply("I am not playing any songs")
        try:
            await player.resume()
        except DiscordUtils.NotPlaying:
            return await ctx.reply("I am not playing any songs")
        await ctx.message.add_reaction("▶️")

    @commands.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 10, commands.BucketType.user)
    async def stop(self, ctx):
        """Stop the current song"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not in a voice channel")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:

            return await ctx.reply("I am not playing any songs")
        try:
            await player.stop()
        except DiscordUtils.NotPlaying:
            return await ctx.reply("I am not playing any songs")
        await ctx.message.add_reaction("⏹️")

    @commands.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 10, commands.BucketType.user)
    async def loop(self, ctx):
        """Toggle looping the current song"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not in a voice channel")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:

            return await ctx.reply(
                "There is no music playing, please queue some songs."
            )
        try:
            song = await player.toggle_song_loop()
        except DiscordUtils.NotPlaying:
            return await ctx.reply("I am not playing any songs")
        if song.is_looping:
            await ctx.reply(f"🔁 Looping `{song.name}`.")
        else:
            await ctx.reply("🔁 Loop disabled.")

    @commands.command(aliases=["q"])
    @voter_only()
    async def queue(self, ctx):
        """Show the current queue"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not in a voice channel")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:

            return await ctx.reply(
                "There is no music playing, please queue some songs."
            )
        try:
            queue_ = player.current_queue()
        except DiscordUtils.EmptyQueue:
            return await ctx.reply("The queue is empty")

        nice = ""
        i = 1
        for (
            song_
        ) in queue_:  # i will paginate this later when i feel like not being lazy
            if i == 11:
                break
            nice += f"`{i}.{' ' if i != 10 else ''}` • [{song_.title}]({song_.url})\n"
            i += 1

        return await ctx.reply(embed=success_embed(":notes: Queue!", nice))

    @commands.command(aliases=["voteskip"])
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 30, commands.BucketType.user)
    async def skip(self, ctx):
        """Vote to skip the current song"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not in a voice channel")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        player = music_.get_player(guild_id=ctx.guild.id)
        if not player:

            return await ctx.reply(
                "There is no music playing, please queue some songs."
            )
        if not ctx.voice_client.is_playing():

            return await ctx.reply("There is no music playing")

        hoomans = len(
            list(filter(lambda m: not m.bot, ctx.author.voice.channel.members))
        )
        if hoomans <= 2 or ctx.author.guild_permissions.manage_guild:
            try:
                await player.skip(force=True)
                await ctx.message.add_reaction("⏭️")
                if ctx.guild.id in self.skip_votes:
                    self.skip_votes.pop(ctx.guild.id)
                return
            except DiscordUtils.NotPlaying:
                return await ctx.reply("There is no music playing")

        if ctx.guild.id not in self.skip_votes:
            self.skip_votes.update({ctx.guild.id: [ctx.author.id]})
            await ctx.reply(
                f"⏭️ Vote skipping has been started: `1/{round(hoomans/2)}` votes."
            )
        else:
            old_list = self.skip_votes[ctx.guild.id]
            if ctx.author.id in old_list:
                return await ctx.reply("You have already added your skip vote!")
            old_list.append(ctx.author.id)
            self.skip_votes.update({ctx.guild.id: old_list})
            if len(self.skip_votes[ctx.guild.id]) >= round(hoomans / 2):
                try:
                    await player.skip(force=True)
                    self.skip_votes.pop(ctx.guild.id)
                    await ctx.message.add_reaction("⏭️")
                except DiscordUtils.NotPlaying:
                    return await ctx.reply("There is no music playing")
            else:
                await ctx.reply(
                    f"⏭️ Skip vote added: `{len(self.skip_votes[ctx.guild.id])}/{round(hoomans/2)}` votes."
                )

    @commands.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 30, commands.BucketType.user)
    async def remove(self, ctx: commands.Context, index: str = None):
        """Remove a song from the queue"""
        if not ctx.author.voice:

            return await ctx.reply(self.error_msg("not_in_voice_channel"))
        if not ctx.guild.me.voice:

            return await ctx.reply("I am not in a voice channel")
        if ctx.author.voice.channel != ctx.guild.me.voice.channel:

            return await ctx.reply(self.error_msg("not_in_same_vc"))
        player: MusicPlayer = music_.get_player(guild_id=ctx.guild.id)
        if not player:

            return await ctx.reply(
                "There is no music playing, please queue some songs."
            )
        if not ctx.voice_client.is_playing():

            return await ctx.reply("There is no music playing")

        prefix = ctx.clean_prefix
        if index is None:

            return await ctx.reply(f"{prefix}remove <index>")
        try:
            index = int(index)
            if index <= 0:

                return await ctx.reply(":x:The number should be a positive number!")
        except ValueError:

            return await ctx.reply(
                f"Please enter an integer!\n\nUsage: `{prefix}remove <number>`\nExample: `{prefix}remove 69`"
            )
        try:
            song = await player.remove_from_queue(index)
            return await ctx.reply(
                f":white_check_mark: Removed `{song.name}` from the queue!"
            )
        except Exception as e:
            return await ctx.reply(f"{e}")

    @commands.command()
    @voter_only()
    @permissions.dynamic_ownerbypass_cooldown(3, 30, commands.BucketType.user)
    async def lyrics(self, ctx: commands.Context, *, song=None):
        """Get the lyrics of a song"""
        error_msg = f"Please enter the song name.\nExample: `{ctx.clean_prefix}lyrics Never Gonna Give You Up`"
        if song is None:
            player = music_.get_player(guild_id=ctx.guild.id)
            if not player:
                return await ctx.reply(error_msg)
            if not ctx.voice_client.is_playing():
                return await ctx.reply(error_msg)
            current_song = player.now_playing()
            song = current_song.name
        main_msg = await ctx.reply("Searching for lyrics...")
        embeds = []
        async with self.session.get(
                f"https://some-random-api.ml/lyrics?title={song.lower()}"
            ) as r:
            if r.status != 200:
                return await main_msg.edit(
                    content="An error occured while accessing the API, this is usually because there aren't any lyrics to the song. Please try again later :>"
                )
            rj = await r.json()
            if "error" in rj:
                return await ctx.reply(rj["error"])
            if len(rj["lyrics"]) <= 4000:
                return await ctx.reply(
                    embed=discord.Embed(
                        title=rj["title"],
                        url=rj["links"]["genius"],
                        description=rj["lyrics"],
                        color=EMBED_COLOUR,
                    ).set_thumbnail(url=rj["thumbnail"]["genius"])
                )
            i = 0
            while True:
                if len(rj["lyrics"]) - i > 4000:
                    embeds.append(
                        discord.Embed(
                            title=rj["title"],
                            url=rj["links"]["genius"],
                            description=rj["lyrics"][i : i + 3999],
                            color=EMBED_COLOUR,
                        ).set_thumbnail(url=rj["thumbnail"]["genius"])
                    )
                elif len(rj["lyrics"]) - i <= 0:
                    break
                else:
                    embeds.append(
                        discord.Embed(
                            title=rj["title"],
                            url=rj["links"]["genius"],
                            description=rj["lyrics"][i:-1],
                            color=EMBED_COLOUR,
                        ).set_thumbnail(url=rj["thumbnail"]["genius"])
                    )

                    break
                i += 3999
            return await main_msg.edit(
                content="", embed=embeds[0], view=Paginator(ctx=ctx, embeds=embeds)
            )


async def setup(bot):
    await bot.add_cog(music(bot))
