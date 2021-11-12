import logging


class AgbFormatter(logging.Formatter):
    grey = "\033[;90m"
    yellow = "\033[;33m"
    red = "\033[1;31m"
    bold_red = "\033[;31m"
    green = "\033[;32m"
    reset = "\033[0;m"
    format = "%(asctime)s - %(name)s | [%(levelname)s]: %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
