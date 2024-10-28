import asyncio

import uvloop

from lattebot.core.bot import LatteBot
from lattebot.logging import setup_logging

# inspired by robodanny - Danny (Rapptz)

# TODO: coverage, tests, etc.
# TODO: pre-commit for linting, formatting, etc.


async def run_bot() -> None:
    async with LatteBot() as bot:
        try:
            from autoreload import Reloader

            reloader = Reloader('lattebot/cogs')
            reloader.start(bot)

        except ImportError:
            pass
        await bot.start()


async def main() -> None:
    with setup_logging():
        await run_bot()


if __name__ == '__main__':
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
