import asyncio
import datetime
import itertools
import json
import textwrap
import time
import traceback
from collections import namedtuple
from io import BytesIO
from typing import Iterator, List, Optional, Sequence, SupportsInt, Union

import discord
import timeago as timesince

from . import common_filters


def config(filename: str = "config"):
    """ Fetch default config file """
    try:
        with open(f"{filename}.json", encoding='utf-8') as data:
            return json.load(data)
    except FileNotFoundError:
        raise FileNotFoundError("config.json file wasn't found")


def emoji_config(filename: str = "emojis"):
    """ Fetch emoji config file """
    try:
        with open(f"{filename}.json", encoding='utf-8') as emogee:
            return json.load(emogee)
    except FileNotFoundError:
        raise FileNotFoundError("emojis.json file wasn't found")


def db_conf(filename: str = "db_config"):
    """ Fetch database config """
    try:
        with open(f"{filename}.json", encoding='utf-8') as dabase:
            return json.load(dabase)
    except FileNotFoundError:
        raise FileNotFoundError("db_config.json file wasn't found")


def get(file):
    try:
        with open(file, encoding='utf-8') as data:
            return json.load(data, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
    except AttributeError:
        raise AttributeError("Unknown argument")
    except FileNotFoundError:
        raise FileNotFoundError("JSON file wasn't found")


def traceback_maker(err, advance: bool = True):
    _traceback = ''.join(traceback.format_tb(err.__traceback__))
    error = ('```py\n{1}{0}: {2}\n```').format(
        type(err).__name__, _traceback, err)
    return error if advance else f"{type(err).__name__}: {err}"


def timetext(name):
    return f"{name}_{int(time.time())}.txt"


def timeago(target):
    return timesince.format(target)


def date(clock=True):
    """Get the date and time.
    Parameters
    ----------
    clock : `bool`, optional
        Set to :code:`False` to not show the time.
    Returns
    -------
    `str`
        The date and time.
    """
    date = datetime.datetime.utcnow()
    date = date.strftime("%a %d %b %Y")
    if clock:
        date = date + " " + time.strftime("%H:%M:%S")
    return date


def responsible(target, reason):
    responsible = f"[ {target} ]"
    if reason is None:
        return f"{responsible} no reason given..."
    return f"{responsible} {reason}"


def actionmessage(case, mass=False):
    output = f"{case} them"

    if mass is True:
        output = f"**{case}** the IDs/Users"

    return f"Alright it's been done, I've {output} <:doge:752674874681458748>"


async def type_message(
    destination: discord.abc.Messageable, content: str, **kwargs
) -> discord.Message:
    """Simulate typing and sending a message to a destination.
    Will send a typing indicator, wait a variable amount of time based on the length
    of the text (to simulate typing speed), then send the message.
    """
    content = common_filters.filter_urls(content)
    try:
        async with destination.typing():
            await asyncio.sleep(len(content) * 0.01)
            return await destination.send(content=content, **kwargs)
    except discord.HTTPException:
        # Not allowed to send messages to this destination (or, sending the message failed)
        pass


def error(text: str) -> str:
    """Get text prefixed with an error emoji.
    Returns
    -------
    str
        The new message.
    """
    return "\N{NO ENTRY SIGN} {}".format(text)


def warning(text: str) -> str:
    """Get text prefixed with a warning emoji.
    Returns
    -------
    str
        The new message.
    """
    return "\N{WARNING SIGN}\N{VARIATION SELECTOR-16} {}".format(text)


def info(text: str) -> str:
    """Get text prefixed with an info emoji.
    Returns
    -------
    str
        The new message.
    """
    return "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} {}".format(text)


def question(text: str) -> str:
    """Get text prefixed with a question emoji.
    Returns
    -------
    str
        The new message.
    """
    return "\N{BLACK QUESTION MARK ORNAMENT}\N{VARIATION SELECTOR-16} {}".format(text)


def bold(text: str, escape_formatting: bool = True) -> str:
    """Get the given text in bold.
    Note: By default, this function will escape ``text`` prior to emboldening.
    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.
    Returns
    -------
    str
        The marked up text.
    """
    text = escape(text, formatting=escape_formatting)
    return "**{}**".format(text)


def box(text: str, lang: str = "") -> str:
    """Get the given text in a code block.
    Parameters
    ----------
    text : str
        The text to be marked up.
    lang : `str`, optional
        The syntax highlighting language for the codeblock.
    Returns
    -------
    str
        The marked up text.
    """
    ret = "```{}\n{}\n```".format(lang, text)
    return ret


def inline(text: str) -> str:
    """Get the given text as inline code.
    Parameters
    ----------
    text : str
        The text to be marked up.
    Returns
    -------
    str
        The marked up text.
    """
    if "`" in text:
        return "``{}``".format(text)
    else:
        return "`{}`".format(text)


def italics(text: str, escape_formatting: bool = True) -> str:
    """Get the given text in italics.
    Note: By default, this function will escape ``text`` prior to italicising.
    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.
    Returns
    -------
    str
        The marked up text.
    """
    text = escape(text, formatting=escape_formatting)
    return "*{}*".format(text)


def bordered(*columns: Sequence[str], ascii_border: bool = False) -> str:
    """Get two blocks of text in a borders.
    Note
    ----
    This will only work with a monospaced font.
    Parameters
    ----------
    *columns : `sequence` of `str`
        The columns of text, each being a list of lines in that column.
    ascii_border : bool
        Whether or not the border should be pure ASCII.
    Returns
    -------
    str
        The bordered text.
    """
    borders = {
        "TL": "+" if ascii_border else "┌",  # Top-left
        "TR": "+" if ascii_border else "┐",  # Top-right
        "BL": "+" if ascii_border else "└",  # Bottom-left
        "BR": "+" if ascii_border else "┘",  # Bottom-right
        "HZ": "-" if ascii_border else "─",  # Horizontal
        "VT": "|" if ascii_border else "│",  # Vertical
    }

    sep = " " * 4  # Separator between boxes
    widths = tuple(max(len(row) for row in column) +
                   9 for column in columns)  # width of each col
    colsdone = [False] * len(columns)  # whether or not each column is done
    lines = [sep.join("{TL}" + "{HZ}" * width + "{TR}" for width in widths)]

    for line in itertools.zip_longest(*columns):
        row = []
        for colidx, column in enumerate(line):
            width = widths[colidx]
            done = colsdone[colidx]
            if column is None:
                if not done:
                    # bottom border of column
                    column = "{HZ}" * width
                    row.append("{BL}" + column + "{BR}")
                    colsdone[colidx] = True  # mark column as done
                else:
                    # leave empty
                    row.append(" " * (width + 2))
            else:
                column += " " * (width - len(column))  # append padded spaces
                row.append("{VT}" + column + "{VT}")

        lines.append(sep.join(row))

    final_row = []
    for width, done in zip(widths, colsdone):
        if not done:
            final_row.append("{BL}" + "{HZ}" * width + "{BR}")
        else:
            final_row.append(" " * (width + 2))
    lines.append(sep.join(final_row))

    return "\n".join(lines).format(**borders)


def pagify(
    text: str,
    delims: Sequence[str] = ["\n"],
    *,
    priority: bool = False,
    escape_mass_mentions: bool = True,
    shorten_by: int = 8,
    page_length: int = 2000,
) -> Iterator[str]:
    """Generate multiple pages from the given text.
    Note
    ----
    This does not respect code blocks or inline code.
    Parameters
    ----------
    text : str
        The content to pagify and send.
    delims : `sequence` of `str`, optional
        Characters where page breaks will occur. If no delimiters are found
        in a page, the page will break after ``page_length`` characters.
        By default this only contains the newline.
    Other Parameters
    ----------------
    priority : `bool`
        Set to :code:`True` to choose the page break delimiter based on the
        order of ``delims``. Otherwise, the page will always break at the
        last possible delimiter.
    escape_mass_mentions : `bool`
        If :code:`True`, any mass mentions (here or everyone) will be
        silenced.
    shorten_by : `int`
        How much to shorten each page by. Defaults to 8.
    page_length : `int`
        The maximum length of each page. Defaults to 2000.
    Yields
    ------
    `str`
        Pages of the given text.
    """
    in_text = text
    page_length -= shorten_by
    while len(in_text) > page_length:
        this_page_len = page_length
        if escape_mass_mentions:
            this_page_len -= in_text.count("@here", 0, page_length) + in_text.count(
                "@everyone", 0, page_length
            )
        closest_delim = (in_text.rfind(d, 1, this_page_len) for d in delims)
        if priority:
            closest_delim = next((x for x in closest_delim if x > 0), -1)
        else:
            closest_delim = max(closest_delim)
        closest_delim = closest_delim if closest_delim != -1 else this_page_len
        if escape_mass_mentions:
            to_send = escape(in_text[:closest_delim], mass_mentions=True)
        else:
            to_send = in_text[:closest_delim]
        if len(to_send.strip()) > 0:
            yield to_send
        in_text = in_text[closest_delim:]

    if len(in_text.strip()) > 0:
        if escape_mass_mentions:
            yield escape(in_text, mass_mentions=True)
        else:
            yield in_text


def strikethrough(text: str, escape_formatting: bool = True) -> str:
    """Get the given text with a strikethrough.
    Note: By default, this function will escape ``text`` prior to applying a strikethrough.
    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.
    Returns
    -------
    str
        The marked up text.
    """
    text = escape(text, formatting=escape_formatting)
    return "~~{}~~".format(text)


def underline(text: str, escape_formatting: bool = True) -> str:
    """Get the given text with an underline.
    Note: By default, this function will escape ``text`` prior to underlining.
    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.
    Returns
    -------
    str
        The marked up text.
    """
    text = escape(text, formatting=escape_formatting)
    return "__{}__".format(text)


def quote(text: str) -> str:
    """Quotes the given text.
    Parameters
    ----------
    text : str
        The text to be marked up.
    Returns
    -------
    str
        The marked up text.
    """
    return textwrap.indent(text, "> ", lambda l: True)


def escape(text: str, *, mass_mentions: bool = False, formatting: bool = False) -> str:
    """Get text with all mass mentions or markdown escaped.
    Parameters
    ----------
    text : str
        The text to be escaped.
    mass_mentions : `bool`, optional
        Set to :code:`True` to escape mass mentions in the text.
    formatting : `bool`, optional
        Set to :code:`True` to escape any markdown formatting in the text.
    Returns
    -------
    str
        The escaped text.
    """
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = discord.utils.escape_markdown(text)
    return text

def text_to_file(
    text: str, filename: str = "file.txt", *, spoiler: bool = False, encoding: str = "utf-8"
):
    """Prepares text to be sent as a file on Discord, without character limit.
    This writes text into a bytes object that can be used for the ``file`` or ``files`` parameters
    of :meth:`discord.abc.Messageable.send`.
    Parameters
    ----------
    text: str
        The text to put in your file.
    filename: str
        The name of the file sent. Defaults to ``file.txt``.
    spoiler: bool
        Whether the attachment is a spoiler. Defaults to ``False``.
    Returns
    -------
    discord.File
        The file containing your text.
    """
    file = BytesIO(text.encode(encoding))
    return discord.File(file, filename, spoiler=spoiler)


async def prettyResults(ctx, filename: str = "Results", resultmsg: str = "Here's the results:", loop=None):
    if not loop:
        return await ctx.send("The result was empty...")

    pretty = "\r\n".join(
        [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)])

    if len(loop) < 15:
        return await ctx.send(f"{resultmsg}```ini\n{pretty}```")

    data = BytesIO(pretty.encode('utf-8'))
    await ctx.send(
        content=resultmsg,
        file=discord.File(data, filename=timetext(filename.title()))
    )
