from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import app_commands

__all__ = ('LatteTree',)

if TYPE_CHECKING:
    from .bot import LatteBot


log = logging.getLogger('lattebot.tree')


class LatteTree(app_commands.CommandTree['LatteBot']): ...
