import contextlib
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Generator  # noqa: UP035

from discord import utils

# TODO: improve logging level, location, etc.


class RemoveNoise(logging.Filter):
    def __init__(self) -> None:
        super().__init__(name='discord.state')

    def filter(self, record: logging.LogRecord) -> bool:
        # if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
        #     return False
        # return True
        return not (record.levelname == 'WARNING' and 'referencing an unknown' in record.msg)


@contextlib.contextmanager
def setup_logging(level: int = logging.INFO) -> Generator[None]:
    log = logging.getLogger()

    try:
        # __enter__
        max_bytes = 32 * 1024 * 1024  # 32 MiB

        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        log.setLevel(level)

        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')

        # TODO: dynamically set log directory
        directory = Path('logs')
        directory.resolve()

        rotating_file_handler = RotatingFileHandler(
            filename=directory / 'lattebot.log',
            encoding='utf-8',
            mode='w',
            maxBytes=max_bytes,
            backupCount=5,
        )
        rotating_file_handler.setFormatter(fmt)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(
            utils._ColourFormatter() if utils.stream_supports_colour(stream_handler.stream) else fmt
        )

        log.addHandler(rotating_file_handler)
        log.addHandler(stream_handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for handler in handlers:
            handler.close()
            log.removeHandler(handler)
