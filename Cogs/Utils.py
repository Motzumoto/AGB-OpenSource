import random

from discord import Embed
from discord.ext import commands
import io
import os
from index import EMBED_COLOUR
from pathlib import Path
from typing import Callable, Dict, Union
from contextvars import ContextVar
import contextlib

# bot = None
# url_regex =
# re.compile(r"(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?")

WAITING_FOR_MSGID = 1
IN_MSGID = 2
WAITING_FOR_MSGSTR = 3
IN_MSGSTR = 4

MSGID = 'msgid "'
MSGSTR = 'msgstr "'

_translators = []


async def setup(bot):
    # This module isn't actually a cog - but it is a place
    # we can call "a trash fire"
    await bot.add_cog(Utils(bot))
    # global bot
    # bot = bot_start


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def error_embed(title, description):
    return Embed(title=title, description=description, color=0xFF0000)


def success_embed(title, description):
    return Embed(title=title, description=description, color=EMBED_COLOUR)


def maxInt(val: int = 0):
    return random.randint(0, val)


_current_locale = ContextVar("_current_locale", default="en-US")
_current_regional_format = ContextVar("_current_regional_format", default=None)


def _unescape(string):
    string = string.replace(r"\\", "\\")
    string = string.replace(r"\t", "\t")
    string = string.replace(r"\r", "\r")
    string = string.replace(r"\n", "\n")
    string = string.replace(r"\"", '"')
    return string


def get_locale() -> str:
    return str(_current_locale.get())


def _parse(translation_file: io.TextIOWrapper) -> Dict[str, str]:
    """
    Custom gettext parsing of translation files.
    Parameters
    ----------
    translation_file : io.TextIOWrapper
        An open text file containing translations.
    Returns
    -------
    Dict[str, str]
        A dict mapping the original strings to their translations. Empty
        translated strings are omitted.
    """
    step = None
    untranslated = ""
    translated = ""
    locale = get_locale()

    translations = {locale: {}}
    for line in translation_file:
        line = line.strip()

        if line.startswith(MSGID):
            # New msgid
            if step is IN_MSGSTR and translated:
                # Store the last translation
                translations[locale][_unescape(untranslated)] = _unescape(translated)
            step = IN_MSGID
            untranslated = line[len(MSGID) : -1]
        elif line.startswith('"') and line.endswith('"'):
            if step is IN_MSGID:
                # Line continuing on from msgid
                untranslated += line[1:-1]
            elif step is IN_MSGSTR:
                # Line continuing on from msgstr
                translated += line[1:-1]
        elif line.startswith(MSGSTR):
            # New msgstr
            step = IN_MSGSTR
            translated = line[len(MSGSTR) : -1]

    if step is IN_MSGSTR and translated:
        # Store the final translation
        translations[locale][_unescape(untranslated)] = _unescape(translated)
    return translations


def get_locale_path(cog_folder: Path, extension: str) -> Path:
    """
    Gets the folder path containing localization files.
    :param Path cog_folder:
        The cog folder that we want localizations for.
    :param str extension:
        Extension of localization files.
    :return:
        Path of possible localization file, it may not exist.
    """
    return cog_folder / "locales" / f"{get_locale()}.{extension}"


class Translator(Callable[[str], str]):
    """Function to get translated strings at runtime."""

    def __init__(self, name: str, file_location: Union[str, Path, os.PathLike]):
        """
        Initializes an internationalization object.
        Parameters
        ----------
        name : str
            Your cog name.
        file_location : `str` or `pathlib.Path`
            This should always be ``__file__`` otherwise your localizations
            will not load.
        """
        self.cog_folder = Path(file_location).resolve().parent
        self.cog_name = name
        self.translations = {}

        _translators.append(self)

        self.load_translations()

    def __call__(self, untranslated: str) -> str:
        """Translate the given string.
        This will look for the string in the translator's :code:`.pot` file,
        with respect to the current locale.
        """
        locale = get_locale()
        try:
            return self.translations[locale][untranslated]
        except KeyError:
            return untranslated

    def load_translations(self):
        """
        Loads the current translations.
        """
        locale = get_locale()

        if locale.lower() == "en-us":
            # Red is written in en-US, no point in loading it
            return
        if locale in self.translations:
            # Locales cannot be loaded twice as they have an entry in
            # self.translations
            return

        locale_path = get_locale_path(self.cog_folder, "po")
        with contextlib.suppress(IOError, FileNotFoundError):
            with locale_path.open(encoding="utf-8") as file:
                self._parse(file)

    def _parse(self, translation_file):
        self.translations.update(_parse(translation_file))

    def _add_translation(self, untranslated, translated):
        untranslated = _unescape(untranslated)
        if translated := _unescape(translated):
            self.translations[untranslated] = translated
