import pytest

from helperFunctions.objects import get_top_of_virtual_path, get_root_of_virtual_path, get_base_of_virtual_path


@pytest.mark.parametrize('input_data, expected', [
    ('foo|bar|test', 'test'),
    ('foo|bar/test', 'bar/test')
])
def test_get_top_of_virtual_path(input_data, expected):
    assert get_top_of_virtual_path(input_data) == expected


@pytest.mark.parametrize('input_data, expected', [
    ('foo|bar|test', 'foo'),
    ('foo|bar/test', 'foo'),
    ('foo', 'foo')
])
def test_get_root_of_virtual_path(input_data, expected):
    assert get_root_of_virtual_path(input_data) == expected


@pytest.mark.parametrize('input_data, expected', [
    ('foo|bar|test', 'foo|bar'),
    ('foo', '')
])
def test_get_base_of_virtual_path(input_data, expected):
    assert get_base_of_virtual_path(input_data) == expected
