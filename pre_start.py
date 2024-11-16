import asyncio
import logging

from lattebot.core.bot import LatteBot
from lattebot.logging import setup_logging


async def main() -> None:
    with setup_logging(logging.DEBUG):
        async with LatteBot() as bot:

            @bot.event
            async def on_ready() -> None:
                await bot.translator.wait_until_ready()
                # await bot.tree.fake_translator()
                await bot.tree_sync()
                await bot.close()

            await bot.start()


if __name__ == '__main__':
    asyncio.run(main())
