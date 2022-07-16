import json
from collections import namedtuple


def config(filename: str = "config"):
    """Fetch default config file"""
    try:
        with open(f"{filename}.json", encoding="utf-8") as data:
            return json.load(data)
    except FileNotFoundError as e:
        raise FileNotFoundError("config.json file wasn't found") from e


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
