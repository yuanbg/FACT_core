import pytest

from helperFunctions.tag import TagColor
from objects.firmware import Firmware


@pytest.mark.parametrize('input_data, expected_count', [
    (['a'], 1),
    (['a', 'b', 'a'], 2)
])
def test_add_tag(input_data, expected_count):
    test_object = Firmware()
    for item in input_data:
        test_object.set_tag(item)
    for item in input_data:
        assert item in test_object.tags
    assert len(test_object.tags.keys()) == expected_count


@pytest.mark.parametrize('input_data, expected_output', [
    ('complete', ''),
    ('some_part', 'some_part')
])
def test_set_part_name(input_data, expected_output):
    test_object = Firmware()
    test_object.device_part = input_data
    assert test_object.device_part == expected_output


@pytest.mark.parametrize('tag_set, remove_items, expected_count', [
    ({'a': TagColor.GRAY, 'b': TagColor.GREEN}, ['a'], 1),
    ({'a': TagColor.GRAY, 'b': TagColor.BLUE}, ['a', 'b', 'a'], 0)
])
def test_remove_tag(tag_set, remove_items, expected_count):
    test_fw = Firmware()
    test_fw.tags = tag_set
    for item in remove_items:
        test_fw.remove_tag(item)
    assert len(test_fw.tags.keys()) == expected_count


@pytest.mark.parametrize('input_data, expected_output', [
    ('complete', 'foo test_device v. 1.0'),
    ('some_part', 'foo test_device - some_part v. 1.0')
])
def test_get_hid(input_data, expected_output):
    test_fw = Firmware(
        device_name='test_device',
        vendor='foo',
        version='1.0',
    )
    test_fw.device_part = input_data
    assert test_fw.hid == expected_output


def test_repr_and_str():
    test_fw = Firmware()
    assert 'None None v. None' in test_fw.__str__()
    assert test_fw.__str__() == test_fw.__repr__()
