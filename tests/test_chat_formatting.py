import pytest

from lattebot.chat_formatting import (
    block_quotes,
    bold,
    bold_italics,
    code_block,
    headers,
    inline,
    italics,
    italics2,
    lists,
    masked_links,
    spoiler,
    strikethrough,
    underline,
    underline_bold,
    underline_bold_italics,
    underline_italics,
)


def test_bold() -> None:
    assert bold('text') == '**text**'


def test_bold_italics() -> None:
    assert bold_italics('text') == '***text***'


def test_strikethrough() -> None:
    assert strikethrough('text') == '~~text~~'


def test_spoiler() -> None:
    assert spoiler('text') == '||text||'


def test_italics() -> None:
    assert italics('text') == '*text*'


def test_italics2() -> None:
    assert italics2('text') == '_text_'


def test_underline() -> None:
    assert underline('text') == '__text__'


def test_underline_bold() -> None:
    assert underline_bold('text') == '__**text**__'


def test_underline_italics() -> None:
    assert underline_italics('text') == '__*text*__'


def test_underline_bold_italics() -> None:
    assert underline_bold_italics('text') == '__***text***__'


def test_inline() -> None:
    assert inline('text') == '`text`'
    assert inline('text with `backticks`') == '``text with `backticks```'


def test_headers() -> None:
    assert headers('Header', level=1) == '# Header'
    assert headers('Header', level=2) == '## Header'
    assert headers('Header', level=3) == '### Header'
    with pytest.raises(ValueError, match='Level must be between 1 and 3'):
        headers('Header', level=4)  # type: ignore[arg-type]


def test_masked_links() -> None:
    assert masked_links('text', link='http://example.com') == '[text](http://example.com)'


def test_lists() -> None:
    assert lists('item', level=1) == ' - item'
    assert lists('item', level=2) == '  - item'
    assert lists('item', level=3) == '   - item'


def test_code_block() -> None:
    assert code_block('code') == '```\ncode```'
    assert code_block('code', lang='python') == '```python\ncode```'


def test_block_quotes() -> None:
    assert block_quotes('quote') == '>>> quote'
    assert block_quotes('quote', multi=True) == '> quote'
