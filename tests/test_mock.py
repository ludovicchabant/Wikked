import pytest
from .mock import MockFileSystem


@pytest.mark.parametrize('flat, expected', [
    ({}, {}),
    ({'/foo.txt': 'Bar'}, {'foo.txt': 'Bar'}),
    ({'/tmp/foo.txt': 'Bar'}, {'tmp': {'foo.txt': 'Bar'}}),
    (
        {'/tmp/foo.txt': 'Bar', '/tmp/bar': 'Foo'},
        {'tmp': {'foo.txt': 'Bar', 'bar': 'Foo'}})])
def test_flat_to_nested(flat, expected):
    actual = MockFileSystem.flat_to_nested(flat)
    assert actual == expected
