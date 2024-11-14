from typing import Literal

# Markdown Text 101 (Chat Formatting: Bold, Italic, Underline)
# https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-

# text formatting


def bold(text: str, /) -> str:
    """Return a bolded string."""
    return f'**{text}**'


def bold_italics(text: str, /) -> str:
    """Return a bolded italicized string."""
    return f'***{text}***'


def strikethrough(text: str, /) -> str:
    """Return a strikethrough string."""
    return f'~~{text}~~'


def spoiler(text: str, /) -> str:
    """Return a spoiler string."""
    return f'||{text}||'


def italics(text: str, /) -> str:
    """Return an italicized string."""
    return f'*{text}*'


def italics2(text: str, /) -> str:
    """Return an italicized string."""
    return f'_{text}_'


def underline(text: str, /) -> str:
    """Return an underlined string."""
    return f'__{text}__'


def underline_bold(text: str, /) -> str:
    """Return an underlined bolded string."""
    return f'__**{text}**__'


def underline_italics(text: str, /) -> str:
    """Return an underlined italicized string."""
    return f'__*{text}*__'


def underline_bold_italics(text: str, /) -> str:
    """Return an underlined bolded italicized string."""
    return f'__***{text}***__'


def inline(text: str, /) -> str:
    """Return an inline string."""
    if '`' in text:
        return f'``{text}``'
    return f'`{text}`'


# organizational text formatting


def headers(text: str, /, *, level: Literal[1, 2, 3] = 1) -> str:
    """Return a header string."""
    if level not in {1, 2, 3}:
        raise ValueError('Level must be between 1 and 3')
    return f'{"#" * level} {text}'


def masked_links(text: str, /, *, link: str) -> str:
    """Return a masked link string."""
    return f'[{text}]({link})'


def lists(text: str, /, *, level: int = 1) -> str:
    """Return a list string."""
    return ' ' * level + f'- {text}'


def code_block(text: str, /, *, lang: str = '') -> str:
    """Return a codeblock string."""
    return f'```{lang}\n{text}```'


def block_quotes(text: str, /, *, multi: bool = False) -> str:
    """Return a block quote string."""
    return f'> {text}' if multi else f'>>> {text}'
