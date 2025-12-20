import asyncio
import logging
from argparse import ArgumentParser

from lattebot.core.bot import LatteBot
from lattebot.logging import setup_logging


async def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate translator generation without syncing commands to Discord',
    )

    args = parser.parse_args()

    with setup_logging(logging.DEBUG):
        async with LatteBot() as bot:

            @bot.event
            async def on_ready() -> None:
                await bot.translator.wait_until_ready()

                if args.dry_run:
                    await bot.tree.fake_translator()
                else:
                    await bot.tree.sync()

                await bot.close()

            await bot.start()


if __name__ == '__main__':
    asyncio.run(main())
