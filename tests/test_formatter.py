import pytest
from wikked.formatter import PageFormatter, FormattingContext
from tests import format_link, format_include


@pytest.mark.parametrize('in_text, text, meta, links', [
    (
        "Something.\nThat's it.\n",
        "Something.\nThat's it.\n",
        None, None),
    (
        "Some meta.\n\n{{foo: Whatever man}}\n",
        "Some meta.\n\n",
        {'foo': ["Whatever man"]}, None),
    (
        "Some multi-meta.\n\n{{foo: First}}\n{{foo: Second}}\n",
        "Some multi-meta.\n\n\n",
        {'foo': ["First", "Second"]}, None),
    (
        "Multi-line meta:\n\n{{foo: This is a\n     multi-line meta\n}}\n",
        "Multi-line meta:\n\n",
        {'foo': ["This is a\n     multi-line meta"]}, None)
    ])
def test_formatter(in_text, text, meta, links):
    f = PageFormatter()
    ctx = FormattingContext('/foo')
    actual = f.formatText(ctx, in_text)
    assert actual == text
    if meta:
        assert ctx.meta == meta
    else:
        assert ctx.meta == {}
    if links:
        assert ctx.out_links == links
    else:
        assert ctx.out_links == []
