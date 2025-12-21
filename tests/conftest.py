from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from lattebot.core.bot import LatteBot
from lattebot.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# from lattebot.logging import setup_logging


@pytest.fixture(scope='session')
def anyio_backend() -> Any:
    return ('asyncio', {'use_uvloop': True})


@pytest.fixture(scope='session')
async def bot() -> AsyncGenerator[LatteBot]:
    async with LatteBot() as bot:
        await bot.login(settings.DISCORD_TOKEN)
        yield bot
