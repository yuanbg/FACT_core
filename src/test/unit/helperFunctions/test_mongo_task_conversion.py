# pylint: disable=no-self-use
from pathlib import Path

import pytest

from helperFunctions.mongo_task_conversion import (
    _get_tag_list, check_for_errors, convert_analysis_task_to_fo, get_uid_of_analysis_task, get_uploaded_file_binary,
    is_sanitized_entry,
    convert_analysis_task_to_fw)
from objects.file import FileObject
from objects.firmware import Firmware


TEST_TASK = {
    'binary': b'this is a test',
    'file_name': 'test_file_name',
    'device_name': 'test device',
    'device_part': 'kernel',
    'device_class': 'test class',
    'version': '1.0',
    'vendor': 'test vendor',
    'release_date': '01.01.1970',
    'requested_analysis_systems': ['file_type', 'dummy'],
    'tags': 'a,b',
    'uid': '2e99758548972a8e8822ad47fa1017ff72f06f3ff6a016851f45c398732bc50c_14'
}


class RequestFileMock:
    content = b"test_file_content"

    def save(self, path: str):
        Path(path).write_bytes(self.content)


@pytest.mark.parametrize('input_data, expected', [
    ('', []),
    ('a,b', ['a', 'b'])
])
def test_get_tag_list(input_data, expected):
    assert _get_tag_list(input_data) == expected


class TestMongoTask:

    def test_check_for_errors(self):
        valid_request = {'a': 'some', 'b': 'some data'}
        assert not check_for_errors(valid_request), 'errors found but all entries are valid'
        invalid_request = {'a': 'some_data', 'b': None}
        result = check_for_errors(invalid_request)
        assert len(result) == 1, 'number of invalid fields not correct'
        assert result['b'] == 'Please specify the b'

    def test_get_uploaded_file_binary(self):
        request_file = RequestFileMock()
        assert get_uploaded_file_binary(request_file) == request_file.content

    def test_get_uploaded_file_binary_error(self):
        assert get_uploaded_file_binary(None) is None, 'missing upload file should lead to None'

    def test_get_uid_of_analysis_task(self):
        analysis_task = {'binary': b'this is a test'}
        assert get_uid_of_analysis_task(analysis_task) == '2e99758548972a8e8822ad47fa1017ff72f06f3ff6a016851f45c398732bc50c_14', 'result is not a uid'

    def test_convert_analysis_task(self):
        fo = convert_analysis_task_to_fo(TEST_TASK)
        fw = convert_analysis_task_to_fw(TEST_TASK, fo.uid)
        assert isinstance(fw, Firmware), 'return type not correct'
        assert isinstance(fo, FileObject), 'return type not correct'
        assert fo.get_uid() == '2e99758548972a8e8822ad47fa1017ff72f06f3ff6a016851f45c398732bc50c_14', 'uid not correct -> binary not correct'
        assert fo.file_name == 'test_file_name'
        assert fw.device_name == 'test device'
        assert fw.device_part == 'kernel'
        assert fw.device_class == 'test class'
        assert fw.version == '1.0'
        assert fw.vendor == 'test vendor'
        assert fw.release_date == '01.01.1970'
        assert len(fo.scheduled_analysis) == 2
        assert 'dummy' in fo.scheduled_analysis
        assert isinstance(fw.tags, dict), 'tag type not correct'

    def test_is_sanitized_entry(self):
        sanitized_example = 'crypto_material_summary_81abfc7a79c8c1ed85f6b9fc2c5d9a3edc4456c4aecb9f95b4d7a2bf9bf652da_76415'
        normal_example = 'blah'
        assert is_sanitized_entry(sanitized_example)
        assert not is_sanitized_entry(normal_example)
