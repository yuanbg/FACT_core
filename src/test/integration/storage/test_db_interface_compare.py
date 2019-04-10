# pylint: disable=attribute-defined-outside-init,protected-access
from time import time

import gc
import pytest

from helperFunctions.config import get_config_for_testing
from storage.MongoMgr import MongoMgr
from storage.db_interface_admin import AdminDbInterface
from storage.db_interface_backend import BackEndDbInterface
from storage.db_interface_common import MongoInterfaceCommon
from storage.db_interface_compare import (
    CompareDbInterface, FactCompareException
)
from test.common_helper import create_test_firmware


class TestCompare:

    @classmethod
    def setup_class(cls):
        cls._config = get_config_for_testing()
        cls.mongo_server = MongoMgr(config=cls._config)

    def setup_method(self):
        self.db_interface = MongoInterfaceCommon(config=self._config)
        self.db_interface_backend = BackEndDbInterface(config=self._config)
        self.db_interface_compare = CompareDbInterface(config=self._config)
        self.db_interface_admin = AdminDbInterface(config=self._config)

        self.fw_one, self.root_fo_1 = create_test_firmware()
        self.fw_two, self.root_fo_2 = create_test_firmware(bin_path='container/test.7z', version='0.2')
        self.compare_dict = self._create_compare_dict()
        self.compare_id = '{};{}'.format(self.root_fo_1.get_uid(), self.root_fo_2.get_uid())

    def teardown_method(self):
        self.db_interface_compare.shutdown()
        self.db_interface_admin.shutdown()
        self.db_interface_backend.shutdown()
        self.db_interface.client.drop_database(self._config.get('data_storage', 'main_database'))
        self.db_interface.shutdown()
        gc.collect()

    @classmethod
    def teardown_class(cls):
        cls.mongo_server.shutdown()

    def _create_compare_dict(self):
        return {
            'general': {
                'hid': {self.root_fo_1.get_uid(): 'foo', self.root_fo_2.get_uid(): 'bar'},
                'virtual_file_path': {self.root_fo_1.get_uid(): 'dev_one_name', self.root_fo_2.get_uid(): 'dev_two_name'}
            },
            'plugins': {}
        }

    def test_add_and_get_compare_result(self):
        self.db_interface_backend.add_file_object(self.root_fo_1)
        self.db_interface_backend.add_file_object(self.root_fo_2)
        self.db_interface_compare.add_compare_result(self.compare_dict)
        retrieved = self.db_interface_compare.get_compare_result(self.compare_id)
        assert retrieved['general']['virtual_file_path'][self.root_fo_1.get_uid()] == 'dev_one_name', 'content of retrieval not correct'

    def test_get_not_existing_compare_result(self):
        self.db_interface_backend.add_file_object(self.root_fo_1)
        self.db_interface_backend.add_file_object(self.root_fo_2)
        result = self.db_interface_compare.get_compare_result('{};{}'.format(self.root_fo_1.get_uid(), self.root_fo_2.get_uid()))
        assert result is None, 'result not none'

    def test_calculate_compare_result_id(self):
        comp_id = self.db_interface_compare._calculate_compare_result_id(self.compare_dict)
        assert comp_id == '{};{}'.format(self.root_fo_1.get_uid(), self.root_fo_2.get_uid())

    def test_calculate_compare_result_id_incomple(self):
        compare_dict = {'general': {'stat_1': {'a': None}, 'stat_2': {'b': None}}}
        comp_id = self.db_interface_compare._calculate_compare_result_id(compare_dict)
        assert comp_id == 'a;b'

    def test_object_existence_quick_check(self):
        self.db_interface_backend.add_file_object(self.root_fo_1)
        assert self.db_interface_compare.check_objects_exist(self.root_fo_1.get_uid()) is None, 'existing_object not found'
        with pytest.raises(FactCompareException):
            self.db_interface_compare.check_objects_exist('{};none_existing_object'.format(self.root_fo_1.get_uid()))

    def test_get_compare_result_of_nonexistent_uid(self):
        self.db_interface_backend.add_file_object(self.root_fo_1)
        try:
            self.db_interface_compare.check_objects_exist('{};none_existing_object'.format(self.root_fo_1.get_uid()))
        except FactCompareException as exception:
            assert exception.get_message() == 'none_existing_object not found in database', 'error message not correct'

    def test_get_latest_comparisons(self):
        self.db_interface_backend.add_file_object(self.root_fo_1)
        self.db_interface_backend.add_file_object(self.root_fo_2)
        before = time()
        self.db_interface_compare.add_compare_result(self.compare_dict)
        result = self.db_interface_compare.page_compare_results(limit=10)
        for id_, hids, submission_date in result:
            assert self.root_fo_1.get_uid() in hids
            assert self.root_fo_2.get_uid() in hids
            assert self.root_fo_1.get_uid() in id_
            assert self.root_fo_2.get_uid() in id_
            assert before <= submission_date <= time()

    def test_get_latest_comparisons_removed_firmware(self):
        self.db_interface_backend.add_firmware(self.fw_one)
        self.db_interface_backend.add_firmware(self.fw_two)
        self.db_interface_backend.add_file_object(self.root_fo_1)
        self.db_interface_backend.add_file_object(self.root_fo_2)
        self.db_interface_compare.add_compare_result(self.compare_dict)
        result = self.db_interface_compare.page_compare_results(limit=10)
        assert result != [], 'A compare result should be available'

        self.db_interface_admin.delete_firmware(self.fw_two.firmware_id)
        result = self.db_interface_compare.page_compare_results(limit=10)
        assert result == [], 'No compare result should be available'

    def test_get_total_number_of_results(self):
        self.db_interface_backend.add_file_object(self.root_fo_1)
        self.db_interface_backend.add_file_object(self.root_fo_2)
        self.db_interface_compare.add_compare_result(self.compare_dict)

        number = self.db_interface_compare.get_total_number_of_results()
        assert number == 1, 'no compare result found in database'

    def test_compare_result_is_in_db(self):
        assert not self.db_interface_compare.compare_result_is_in_db(self.compare_id)
        self.db_interface_compare.add_compare_result(self.compare_dict)
        self.db_interface_backend.add_file_object(self.root_fo_1)
        self.db_interface_backend.add_file_object(self.root_fo_2)
        assert self.db_interface_compare.compare_result_is_in_db(self.compare_id)
