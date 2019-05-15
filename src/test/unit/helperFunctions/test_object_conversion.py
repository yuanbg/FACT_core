import unittest
from test.common_helper import create_test_firmware, create_test_file_object
from helperFunctions.object_conversion import create_fo_meta_dict, create_fw_meta_dict


class TestHelperFunctionsObjectConversion(unittest.TestCase):

    def test_create_fw_meta_dict(self):
        fw, _ = create_test_firmware()
        meta = create_fw_meta_dict(fw)
        assert meta['device_name'] == 'test_router'
        assert meta['device_class'] == 'Router'
        assert meta['vendor'] == 'test_vendor'
        assert meta['device_part'] == ''
        assert meta['version'] == '0.1'
        assert meta['release_date'] == '1970-01-01'
        assert meta['hid'] == 'test_vendor test_router v. 0.1'
        assert len(meta.keys()) == 7

    def test_create_meta_dict_fo(self):
        fo = create_test_file_object()
        fo.list_of_all_included_files = []
        meta = create_fo_meta_dict(fo)
        assert meta['firmwares_including_this_file'] == ['d558c9339cb967341d701e3184f863d3928973fccdc1d96042583730b5c7b76a_62']
        assert meta['virtual_file_path'] == ['d558c9339cb967341d701e3184f863d3928973fccdc1d96042583730b5c7b76a_62']
        assert meta['number_of_files'] == 0
        assert len(meta.keys()) == 5
