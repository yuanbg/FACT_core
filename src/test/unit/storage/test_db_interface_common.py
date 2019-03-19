import pytest

from test.common_helper import CommonDbInterfaceMock

CURRENT_DATA_FORMAT = {
    '_id': 'some_ID',
    'uid': 'some UID',
    'size': 1,
    'file_name': 'name_of_the_file',
    'device_name': 'test_device',
    'device_class': 'class_of_the_device',
    'release_date': 0,
    'vendor': 'test_vendor',
    'version': '0.1',
    'processed_analysis': {},
    'files_included': [],
    'virtual_file_path': {},
    'tags': {},
    'analysis_tags': {},
    'device_part': 'bootloader'
}

OLD_DATA_FORMAT = {
    '_id': 'some_ID',
    'uid': 'some UID',
    'size': 1,
    'file_name': 'name_of_the_file',
    'device_name': 'test_device',
    'device_class': 'class_of_the_device',
    'release_date': 0,
    'vendor': 'test_vendor',
    'version': '0.1',
    'processed_analysis': {},
    'files_included': [],
    'virtual_file_path': {},
    'comment': 'some comment'
}


@pytest.mark.parametrize('input_data, expected', [
    (CURRENT_DATA_FORMAT, 'bootloader'),
    (OLD_DATA_FORMAT, '')
])
def test_convert_to_firmware(input_data, expected):
    test_interface = CommonDbInterfaceMock()
    result = test_interface._convert_to_firmware(input_data, analysis_filter=None)
    assert result.part == expected
