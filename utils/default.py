import asyncio
import contextlib
import datetime
import itertools
import json
import logging
import textwrap
import time
import traceback
from collections import namedtuple
from io import BytesIO
from typing import Iterator, Sequence

import discord
import requests
import timeago as timesince
from Cogs.Utils import Translator
from colorama import Fore, Style

from . import common_filters

_ = Translator("Nsfw", __file__)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format=f"{f'{Style.DIM}(%(asctime)s){Style.RESET_ALL}'} [{Fore.CYAN}%(levelname)s{Style.RESET_ALL}]: %(message)s",
    datefmt="[%a]-%I:%M-%p",
)


def uptime(start_time):
    delta_uptime = datetime.datetime.now(datetime.timezone.utc) - start_time
    hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def config(filename: str = "config"):
    """Fetch default config file"""
    try:
        with open(f"{filename}.json", encoding="utf-8") as data:
            return json.load(data)
    except FileNotFoundError as e:
        raise FileNotFoundError("config.json file wasn't found") from e


def emoji_config(filename: str = "emojis"):
    """Fetch emoji config file"""
    try:
        with open(f"{filename}.json", encoding="utf-8") as emogee:
            return json.load(emogee)
    except FileNotFoundError as e:
        raise FileNotFoundError("emojis.json file wasn't found") from e


def draw_box(usage, active, inactive):
    usage = int(usage)
    if usage < 20:
        return f"{active}{inactive * 9}"
    elif usage == 100:
        return active * 10

    activec = usage // 10
    black = 10 - activec
    return f"{active * activec}{inactive * black}"


def db_conf(filename: str = "db_config"):
    """Fetch database config"""
    try:
        with open(f"{filename}.json", encoding="utf-8") as dabase:
            return json.load(dabase)
    except FileNotFoundError as e:
        raise FileNotFoundError("db_config.json file wasn't found") from e


def pycode(text: str, escape_formatting: bool = True) -> str:
    """Get the given text in code block.
    Note: By default, this function will escape ``text`` prior to embedding.
    Parameters
    """
    text = escape(text, formatting=escape_formatting)
    return f"```py\n{text}\n```"


def get(file):
    try:
        with open(file, encoding="utf-8") as data:
            return json.load(
                data, object_hook=lambda d: namedtuple("X", d.keys())(*d.values())
            )
    except AttributeError as e:
        raise AttributeError("Unknown argument") from e
    except FileNotFoundError as e:
        raise FileNotFoundError("JSON file wasn't found") from e


def traceback_maker(err, advance: bool = True):
    _traceback = "".join(traceback.format_tb(err.__traceback__))
    error = ("```py\n{1}{0}: {2}\n```").format(type(err).__name__, _traceback, err)
    return error if advance else f"{type(err).__name__}: {err}"


def log(text: str):
    """Log the given text to a file.
    Parameters
    ----------
    text : `str`
            The text to log.
    """
    with open("logs.txt", "a+", encoding="utf-8") as log_file:
        log_file.write(f"[{date()}] {text}\n")
    # output the text to the console
    logger.info(text)


def code_traceback(err, advance: bool = True):
    _traceback = "".join(traceback.format_tb(err.__traceback__))
    error = ("{1}{0}: {2}").format(type(err).__name__, _traceback, err)
    return error if advance else f"{type(err).__name__}: {err}"


def download(url, name):
    with open(name, "wb") as f:
        f.write(requests.get(url).content)


def ascii_art(word):
    return f"{word}".encode("ascii", "ignore").decode("ascii")


def addcommas(number):
    if number < 1000:
        return number
    number = str(number)
    return f"{addcommas(number[:-3])},{number[-3:]}"


def commify(n):
    n = str(n)
    return n if len(n) <= 3 else f"{commify(n[:-3])},{n[-3:]}"


def timetext(name):
    return f"{name}_{int(time.time())}.txt"


def add_one(num):
    num = int(num) + 1
    return num


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
    date = datetime.datetime.now(datetime.timezone.utc)
    date = date.strftime("%a %d %b %Y")
    if clock:
        date = f"{date} " + time.strftime("%H:%M:%S")
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

    return f"Alright it's been done, I've {output} <:doge:964087593648132146>"


async def type_message(
    destination: discord.abc.Messageable, content: str, **kwargs
) -> discord.Message:
    """Simulate typing and sending a message to a destination.
    Will send a typing indicator, wait a variable amount of time based on the length
    of the text (to simulate typing speed), then send the message.
    """
    content = common_filters.filter_urls(content)
    with contextlib.suppress(discord.HTTPException):
        async with destination.typing():
            await asyncio.sleep(len(content) * 0.05)
            return await destination.send(content=content, **kwargs)


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
    return f"**{text}**"


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
    return f"```{lang}\n{text}\n```"


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
    return f"``{text}``" if "`" in text else f"`{text}`"


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
    return f"*{text}*"


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
    widths = tuple(
        max(len(row) for row in column) + 9 for column in columns
    )  # width of each col
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
    delims: Sequence[str] = None,
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
    if delims is None:
        delims = ["\n"]
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
    return f"~~{text}~~"


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
    return f"__{text}__"


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
    text: str,
    filename: str = "file.txt",
    *,
    spoiler: bool = False,
    encoding: str = "utf-8",
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


async def prettyResults(
    ctx, filename: str = "Results", resultmsg: str = "Here's the results:", loop=None
):
    if not loop:
        return await ctx.send("The result was empty...")

    pretty = "\r\n".join(
        [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
    )

    if len(loop) < 15:
        return await ctx.send(f"{resultmsg}```ini\n{pretty}```")

    data = BytesIO(pretty.encode("utf-8"))
    await ctx.send(
        content=resultmsg, file=discord.File(data, filename=timetext(filename.title()))
    )


def bytesto(bytes, to, bsize=1024):
    """convert bytes to megabytes, etc.
    sample code:
            print('mb= ' + str(bytesto(314575262000000, 'm')))
    sample output:
            mb= 300002347.946
    """

    a = {"k": 1, "m": 2, "g": 3, "t": 4, "p": 5, "e": 6}
    r = float(bytes)
    for _ in range(a[to]):
        r = r / bsize

    return r
