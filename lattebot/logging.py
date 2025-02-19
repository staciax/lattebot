from __future__ import annotations

import contextlib
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from collections.abc import Generator

# TODO: improve logging level, location, etc.
# TODO: migrate to loguru, https://github.com/Delgan/loguru


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
        discord.utils.setup_logging()

        max_bytes = 32 * 1024 * 1024  # 32 MiB

        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        log.setLevel(level)

        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')

        # TODO: dynamically set log directory
        directory = Path('logs')
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

        rotating_file_handler = RotatingFileHandler(
            filename=directory / 'lattebot.log',
            encoding='utf-8',
            mode='w',
            maxBytes=max_bytes,
            backupCount=5,
        )
        rotating_file_handler.setFormatter(fmt)
        log.addHandler(rotating_file_handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for handler in handlers:
            handler.close()
            log.removeHandler(handler)
