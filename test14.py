import asyncio
import logging

from anyio import Path

from lattebot.core.bot import LatteBot
from lattebot.core.config import settings
from lattebot.core.translator import save_yaml

log = logging.getLogger('test')


async def main() -> None:
    async with LatteBot() as bot:
        await bot.login(settings.DISCORD_TOKEN)
        # await bot.tree_sync()

        await bot.translator.load_translations()
        await bot.tree.fake_translator()

        # print(bot.translator.locales)

        # filepath = Path('translations.yaml')
        # await save_yaml(bot.translator._localization, filepath)

        bot.translator.clear()


if __name__ == '__main__':
    asyncio.run(main())
