import asyncio
import copy
import datetime
import math
import random
import re
import typing

import async_timeout
import discord
import wavelink
from discord.ext import commands, menus
from index import EMBED_COLOUR
from utils import default

# URL matching REGEX...
URL_REG = re.compile(r"https?://(?:www\.)?.+")


class NoChannelProvided(commands.CommandError):
    """Error raised when no suitable voice channel was supplied."""

    pass


class IncorrectChannelError(commands.CommandError):
    """Error raised when commands are issued outside of the players session channel."""

    pass


class Track(wavelink.Track):
    """Wavelink Track object with a requester attribute."""

    __slots__ = ("requester",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get("requester")


class Player(wavelink.Player):
    """Custom wavelink Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context = kwargs.get("context", None)
        if self.context:
            self.dj: discord.Member = self.context.author

        self.queue = asyncio.Queue()
        self.controller = None

        self.waiting = False
        self.updating = False

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

        # Clear the votes for a new song...
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

        try:
            self.waiting = True
            with async_timeout.timeout(20):
                track = await self.queue.get()
        except asyncio.TimeoutError:
            # No music has been played for 5 minutes, cleanup and disconnect...
            return await self.teardown()

        await self.play(track)
        self.waiting = False

        # Invoke our players controller...
        await self.invoke_controller()

    async def invoke_controller(self) -> None:
        """Method which updates or sends a new player controller."""
        if self.updating:
            return

        self.updating = True

        if not self.controller:
            self.controller = InteractiveController(
                embed=self.build_embed(), player=self
            )
            await self.controller.start(self.context)

        elif not await self.is_position_fresh():
            try:
                await self.controller.message.delete()
            except:
                pass

            self.controller.stop()

            self.controller = InteractiveController(
                embed=self.build_embed(), player=self
            )
            await self.controller.start(self.context)

        else:
            embed = self.build_embed()
            await self.controller.message.edit(content=None, embed=embed)

        self.updating = False

    def build_embed(self) -> typing.Optional[discord.Embed]:
        """Method which builds our players controller embed."""
        track = self.current
        if not track:
            return

        channel = self.bot.get_channel(int(self.channel_id))
        qsize = self.queue.qsize()

        embed = discord.Embed(
            title=f"Music Controller | {channel.name}", colour=EMBED_COLOUR
        )
        embed.description = f"Now Playing:\n**`{track.title}`**\n\n"
        embed.set_thumbnail(url=track.thumb)

        embed.add_field(
            name="Duration",
            value=str(datetime.timedelta(milliseconds=int(track.length))),
        )
        embed.add_field(name="Queue Length", value=str(qsize))
        embed.add_field(name="Volume", value=f"**`{self.volume}%`**")
        embed.add_field(name="Requested By", value=track.requester.mention)
        embed.add_field(name="DJ", value=self.dj.mention)
        embed.add_field(name="Video URL", value=f"[Click Here!]({track.uri})")

        return embed

    async def is_position_fresh(self) -> bool:
        """Method which checks whether the player controller should be remade or updated."""
        try:
            async for message in self.context.channel.history(limit=5):
                if message.id == self.controller.message.id:
                    return True
        except (discord.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        try:
            await self.controller.message.delete()
        except:
            pass

        self.controller.stop()
        await self.destroy()


class InteractiveController(menus.Menu):
    """The Players interactive controller menu class."""

    def __init__(self, *, embed: discord.Embed, player: Player):
        super().__init__(timeout=None)

        self.embed = embed
        self.player = player

    def update_context(self, payload: discord.RawReactionActionEvent):
        """Update our context with the user who reacted."""
        ctx = copy.copy(self.ctx)
        ctx.author = payload.member

        return ctx

    def reaction_check(self, payload: discord.RawReactionActionEvent):
        if payload.event_type == "REACTION_REMOVE":
            return False

        if not payload.member:
            return False
        if payload.member.bot:
            return False
        if payload.message_id != self.message.id:
            return False
        if (
            payload.member
            not in self.bot.get_channel(int(self.player.channel_id)).members
        ):
            return False

        return payload.emoji in self.buttons

    async def send_initial_message(
        self, ctx, channel: discord.TextChannel
    ) -> discord.Message:
        return await channel.send(embed=self.embed)

    @menus.button(emoji="\u25B6")
    async def resume_command(self, payload: discord.RawReactionActionEvent):
        """Resume button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command("resume")
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji="\u23F8")
    async def pause_command(self, payload: discord.RawReactionActionEvent):
        """Pause button"""
        ctx = self.update_context(payload)

        command = self.bot.get_command("pause")
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji="\u23F9")
    async def stop_command(self, payload: discord.RawReactionActionEvent):
        """Stop button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command("stop")
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji="\u23ED")
    async def skip_command(self, payload: discord.RawReactionActionEvent):
        """Skip button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command("skip")
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji="\U0001F500")
    async def shuffle_command(self, payload: discord.RawReactionActionEvent):
        """Shuffle button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command("shuffle")
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji="\u2795")
    async def volup_command(self, payload: discord.RawReactionActionEvent):
        """Volume up button"""
        ctx = self.update_context(payload)

        command = self.bot.get_command("vol_up")
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji="\u2796")
    async def voldown_command(self, payload: discord.RawReactionActionEvent):
        """Volume down button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command("vol_down")
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji="\U0001F1F6")
    async def queue_command(self, payload: discord.RawReactionActionEvent):
        """Player queue button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command("queue")
        ctx.command = command

        await self.bot.invoke(ctx)


class PaginatorSource(menus.ListPageSource):
    """Player queue paginator class."""

    def __init__(self, entries, *, per_page=8):
        super().__init__(entries, per_page=per_page)

    async def format_page(self, menu: menus.Menu, page):
        embed = discord.Embed(title="Coming Up...", colour=EMBED_COLOUR)
        embed.description = "\n".join(
            f"`{index}. {title}`" for index, title in enumerate(page, 1)
        )

        return embed

    def is_paginating(self):
        # We always want to embed even on 1 page of results...
        return True


owners = default.get("config.json").owners


class Music(commands.Cog, wavelink.WavelinkMixin, name="music"):
    """Music Cog. This is still a work in progress, so things will stop working. Please just let us work the kinks out"""

    def __init__(self, bot: commands.Bot):
        """Music Cog. This is still a work in progress, so things will stop working. Please just let us work the kinks out"""
        self.bot = bot
        self.config = default.get("config.json")

        if not hasattr(bot, "wavelink"):
            bot.wavelink = wavelink.Client(bot=bot)

        bot.loop.create_task(self.start_nodes())

    async def start_nodes(self) -> None:
        """Connect and intiate nodes."""
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

        nodes = {
            "MAIN": {
                "host": "0.0.0.0",
                "port": 8001,
                "rest_uri": "http://127.0.0.1:8001/",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "us_south",
            }
        }

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        print(f"{default.date()} | Node {node.identifier} is ready!")

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel = self.bot.get_channel(int(player.channel_id))

        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj = m
                    return

        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member

    async def cog_command_error(self, ctx, error: Exception):
        """Cog wide error handler."""
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            return await ctx.send(
                "You must be in a voice channel or provide one to connect to."
            )

    async def cog_check(self, ctx):
        """Cog wide check, which disallows commands in DMs."""
        if not ctx.guild:
            await ctx.send("Music commands are not available in Private Messages.")
            return False

        return True

    async def cog_before_invoke(self, ctx):
        """Coroutine called before command invocation.
        We mainly just want to check whether the user is in the players controller channel.
        """
        player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, cls=Player, context=ctx
        )

        if player.context:
            if player.context.channel != ctx.channel:
                await ctx.send(
                    f"{ctx.author.mention}, you must be in {player.context.channel.mention} for this session."
                )
                raise IncorrectChannelError

        if ctx.command.name == "connect" and not player.context:
            return
        elif self.is_privileged(ctx):
            return

        if not player.channel_id:
            return

        channel = self.bot.get_channel(int(player.channel_id))
        if not channel:
            return

        if player.is_connected:
            if ctx.author not in channel.members:
                await ctx.send(
                    f"{ctx.author.mention}, you must be in `{channel.name}` to use voice commands."
                )
                raise IncorrectChannelError

    def required(self, ctx):
        """Method which returns required votes based on amount of members in a channel."""
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    def is_privileged(self, ctx):
        """Check whether the user is an Admin or DJ."""
        if ctx.author.id in owners:
            return True
        else:
            pass
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

    @commands.command(aliases=["join"], usage="`tp!join`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def connect(
        self,
        ctx,
        *,
        channel: typing.Union[discord.VoiceChannel, discord.StageChannel] = None,
    ):
        """Connect to a voice channel."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if player.is_connected:
            return
        channel = getattr(ctx.author.voice, "channel", channel)
        if channel is None:
            raise NoChannelProvided

        await player.connect(channel.id)

    @commands.command(usage="`tp!play <song>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def play(self, ctx, *, query: str):
        """Play or queue a song with the given query."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        # try:
        #     await ctx.message.delete()
        # except discord.Forbidden:
        #     pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            await ctx.invoke(self.connect)
        query = query.strip("<>")
        if not URL_REG.match(query):
            query = f"ytsearch:{query}"
        tracks = await self.bot.wavelink.get_tracks(query)
        if not tracks:
            return await ctx.send(
                "No songs were found with that query. Please try again."
            )
        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                await player.queue.put(track)
            await ctx.send(
                f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                f" with {len(tracks.tracks)} songs to the queue.\n```"
            )
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            await ctx.send(f"```ini\nAdded {track.title} to the Queue\n```")
            await player.queue.put(track)

        if not player.is_playing:
            await player.do_next()

    @commands.command(usage="`tp!pause`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4, type=commands.BucketType.user)
    async def pause(self, ctx):
        """Pause the currently playing song."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if player.is_paused or not player.is_connected:
            return
        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has paused the player.", delete_after=10)
            player.pause_votes.clear()
            return await player.set_pause(True)
        required = self.required(ctx)
        player.pause_votes.add(ctx.author)
        if len(player.pause_votes) >= required:
            await ctx.send("Vote to pause passed. Pausing player.", delete_after=10)
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to pause the player.", delete_after=15
            )

    @commands.command(usage="`tp!resume`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def resume(self, ctx):
        """Resume a currently paused player."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_paused or not player.is_connected:
            return
        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has resumed the player.", delete_after=10)
            player.resume_votes.clear()
            return await player.set_pause(False)
        required = self.required(ctx)
        player.resume_votes.add(ctx.author)
        if len(player.resume_votes) >= required:
            await ctx.send("Vote to resume passed. Resuming player.", delete_after=10)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to resume the player.", delete_after=15
            )

    @commands.command(usage="`tp!skip`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def skip(self, ctx):
        """Skip the currently playing song."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has skipped the song.", delete_after=10)
            player.skip_votes.clear()
            return await player.stop()
        if ctx.author == player.current.requester:
            await ctx.send("The song requester has skipped the song.", delete_after=10)
            player.skip_votes.clear()
            return await player.stop()
        required = self.required(ctx)
        player.skip_votes.add(ctx.author)
        if len(player.skip_votes) >= required:
            await ctx.send("Vote to skip passed. Skipping song.", delete_after=10)
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to skip the song.", delete_after=15
            )

    @commands.command(aliases=["disconnect", "dc"], usage="`tp!disconnect`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def stop(self, ctx):
        """Disconnect the player."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        if not self.is_privileged(ctx):
            return await ctx.send(
                "Only admins and the DJ may use this command.", delete_after=15
            )
        await player.teardown()
        try:
            await player.disconnect()
        except:
            pass
        await ctx.send("Disconnected from the channel.", delete_after=15)

    @commands.command(aliases=["v", "vol"], usage="`tp!vol <amount>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def volume(self, ctx, *, vol: int):
        """Change the players volume, between 1 and 100."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        if not self.is_privileged(ctx):
            return await ctx.send("Only the DJ or admins may change the volume.")
        if not 0 < vol < 101:
            return await ctx.send("Please enter a value between 1 and 100.")
        await player.set_volume(vol)
        await ctx.send(f"Set the volume to **{vol}**%", delete_after=7)

    @commands.command(aliases=["mix"], usage="`tp!mix`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def shuffle(self, ctx):
        """Shuffle the players queue."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        if player.queue.qsize() < 3:
            return await ctx.send(
                "Add more songs to the queue before shuffling.", delete_after=15
            )
        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has shuffled the playlist.", delete_after=10)
            player.shuffle_votes.clear()
            return random.shuffle(player.queue._queue)
        required = self.required(ctx)
        player.shuffle_votes.add(ctx.author)
        if len(player.shuffle_votes) >= required:
            await ctx.send(
                "Vote to shuffle passed. Shuffling the playlist.", delete_after=10
            )
            player.shuffle_votes.clear()
            random.shuffle(player.queue._queue)
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to shuffle the playlist.",
                delete_after=15,
            )

    @commands.command(hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    async def vol_up(self, ctx):
        """Command used for volume up button."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected or not self.is_privileged(ctx):
            return
        vol = int(math.ceil((player.volume + 10) / 10)) * 10
        if vol > 100:
            vol = 100
            await ctx.send("Maximum volume reached", delete_after=7)
        await player.set_volume(vol)

    @commands.command(hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    async def vol_down(self, ctx):
        """Command used for volume down button."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected or not self.is_privileged(ctx):
            return
        vol = int(math.ceil((player.volume - 10) / 10)) * 10
        if vol < 0:
            vol = 0
            await ctx.send("Player is currently muted", delete_after=10)
        await player.set_volume(vol)

    @commands.command(aliases=["eq"], usage="`tp!eq <value>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def equalizer(self, ctx, *, equalizer: str):
        """Change the players equalizer.
        Valid Equalizers:flat, boost, metal, piano"""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        if not self.is_privileged(ctx):
            return await ctx.send("Only the DJ or admins may change the equalizer.")
        eqs = {
            "flat": wavelink.Equalizer.flat(),
            "boost": wavelink.Equalizer.boost(),
            "metal": wavelink.Equalizer.metal(),
            "piano": wavelink.Equalizer.piano(),
        }
        eq = eqs.get(equalizer.lower(), None)
        if not eq:
            joined = "\n".join(eqs.keys())
            return await ctx.send(f"Invalid EQ provided. Valid EQs:\n\n{joined}")
        await ctx.send(
            f"Successfully changed equalizer to {equalizer}", delete_after=15
        )
        await player.set_eq(eq)

    @commands.command(aliases=["q", "que"], usage="`tp!q`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def queue(self, ctx):
        """Display the players queued songs."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        if player.queue.qsize() == 0:
            return await ctx.send(
                "There are no more songs in the queue.", delete_after=15
            )
        entries = [track.title for track in player.queue._queue]
        pages = PaginatorSource(entries=entries)
        paginator = menus.MenuPages(
            source=pages, timeout=None, delete_message_after=True
        )
        await paginator.start(ctx)

    @commands.command(aliases=["np", "now_playing", "current"], usage="`tp!np`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def nowplaying(self, ctx):
        """Update the player controller."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        await player.invoke_controller()

    @commands.command(aliases=["swap"], usage="`tp!swap <user>`")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(rate=1, per=4.5, type=commands.BucketType.user)
    async def swap_dj(self, ctx, *, member: discord.Member = None):
        """Swap the current DJ to another member in the voice channel."""
        await ctx.send(
            "This currently isnt working as we're experiencing a lot of issues right now. Please try again later."
        )
        return
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return
        if not self.is_privileged(ctx):
            return await ctx.send(
                "Only admins and the DJ may use this command.", delete_after=15
            )
        members = self.bot.get_channel(int(player.channel_id)).members
        if member and member not in members:
            return await ctx.send(
                f"{member} is not currently in voice, so can not be a DJ.",
                delete_after=15,
            )
        if member and member == player.dj:
            return await ctx.send(
                "Cannot swap DJ to the current DJ... :)", delete_after=15
            )
        if len(members) <= 2:
            return await ctx.send("No more members to swap to.", delete_after=15)
        if member:
            player.dj = member
            return await ctx.send(f"{member.mention} is now the DJ.")
        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await ctx.send(f"{member.mention} is now the DJ.")


def setup(bot):
    bot.add_cog(Music(bot))
