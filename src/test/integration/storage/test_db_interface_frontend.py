import gc
from os import path
from tempfile import TemporaryDirectory

from helperFunctions.config import get_config_for_testing
from helperFunctions.fileSystem import get_test_data_dir
from helperFunctions.file_tree import FileTreeNode
from storage.MongoMgr import MongoMgr
from storage.db_interface_backend import BackEndDbInterface
from storage.db_interface_frontend import FrontEndDbInterface
from test.common_helper import create_test_firmware, create_test_file_object

TESTS_DIR = get_test_data_dir()
TEST_FILE = path.join(TESTS_DIR, 'get_files_test/testfile1')
TMP_DIR = TemporaryDirectory(prefix='fact_test_')


class TestStorageDbInterfaceFrontend:

    @classmethod
    def setup_class(cls):
        cls._config = get_config_for_testing(TMP_DIR)
        cls.mongo_server = MongoMgr(config=cls._config)

    def setup_method(self):
        self.db_frontend_interface = FrontEndDbInterface(config=self._config)
        self.db_backend_interface = BackEndDbInterface(config=self._config)
        self.test_firmware, self.test_root_fo = create_test_firmware()

    def teardown_method(self):
        self.db_frontend_interface.shutdown()
        self.db_backend_interface.client.drop_database(self._config.get('data_storage', 'main_database'))
        self.db_backend_interface.shutdown()
        gc.collect()

    @classmethod
    def teardown_class(cls):
        cls.mongo_server.shutdown()
        TMP_DIR.cleanup()

    def test_get_meta_list(self):
        self.db_backend_interface.add_firmware(self.test_firmware)
        self.db_backend_interface.add_file_object(self.test_root_fo)
        result = self.db_frontend_interface.get_meta_list_from_id_list([self.test_firmware.firmware_id])
        assert len(result) == 1
        _, hid, tags, _ = result.pop()
        assert hid == 'test_vendor test_router - 0.1 (Router)', 'Firmware not successfully received'
        assert isinstance(tags, dict), 'tag field is not a dict'

    def test_get_meta_list_of_fo(self):
        test_fo = create_test_file_object()
        self.db_backend_interface.add_file_object(test_fo)
        files = self.db_frontend_interface.file_objects.find()
        meta_list = self.db_frontend_interface.get_meta_list(files)
        assert meta_list[0][0] == test_fo.get_uid(), 'uid of object not correct'
        assert meta_list[0][3] == 0, 'non existing submission date should lead to 0'

    def test_get_hid_firmware(self):
        self.db_backend_interface.add_firmware(self.test_firmware)
        self.db_backend_interface.add_file_object(self.test_root_fo)
        result = self.db_frontend_interface.get_hid(self.test_firmware.firmware_id)
        assert result == 'test_vendor test_router - 0.1 (Router)', 'fw hid not correct'

    def test_get_hid_fo(self):
        test_fo = create_test_file_object(bin_path='get_files_test/testfile2')
        test_fo.virtual_file_path = {'a': ['|a|/test_file'], 'b': ['|b|/get_files_test/testfile2']}
        self.db_backend_interface.add_file_object(test_fo)
        result = self.db_frontend_interface.get_hid(test_fo.get_uid(), root_uid='b')
        assert result == '/get_files_test/testfile2', 'fo hid not correct'
        result = self.db_frontend_interface.get_hid(test_fo.get_uid())
        assert isinstance(result, str), 'result is not a string'
        assert result[0] == '/', 'first character not correct if no root_uid set'
        result = self.db_frontend_interface.get_hid(test_fo.get_uid(), root_uid='c')
        assert result[0] == '/', 'first character not correct if invalid root_uid set'

    def test_get_hid_invalid_uid(self):
        result = self.db_frontend_interface.get_hid('foo')
        assert result == '', 'invalid uid should result in empty string'

    def test_get_file_name(self):
        self.db_backend_interface.add_file_object(self.test_root_fo)
        result = self.db_frontend_interface.get_file_name(self.test_root_fo.get_uid())
        assert result == 'test.zip', 'name not correct'

    def test_get_firmware_attribute_list(self):
        self.db_backend_interface.add_firmware(self.test_firmware)
        assert self.db_frontend_interface.get_device_class_list() == ['Router']
        assert self.db_frontend_interface.get_vendor_list() == ['test_vendor']
        result = self.db_frontend_interface.get_firmware_attribute_list('device_name', {'vendor': 'test_vendor', 'device_class': 'Router'})
        assert result == ['test_router']
        assert self.db_frontend_interface.get_firmware_attribute_list('version') == ['0.1']
        assert self.db_frontend_interface.get_device_name_dict() == {'Router': {'test_vendor': ['test_router']}}

    def test_get_data_for_nice_list(self):
        uid_list = [self.test_root_fo.get_uid()]
        self.db_backend_interface.add_file_object(self.test_root_fo)
        nice_list_data = self.db_frontend_interface.get_data_for_nice_list(uid_list, uid_list[0])
        assert sorted(['files_included', 'mime-type', 'size', 'uid', 'virtual_file_paths']) == sorted(nice_list_data[0].keys())
        assert nice_list_data[0]['uid'] == self.test_root_fo.get_uid()

    def test_generic_search(self):
        self.db_backend_interface.add_file_object(self.test_root_fo)
        result = self.db_frontend_interface.generic_search({'file_name': 'test.zip'})
        assert result == [self.test_root_fo.get_uid()], 'Firmware not successfully received'

    def test_all_uids_found_in_database(self):
        self.db_backend_interface.client.drop_database(self._config.get('data_storage', 'main_database'))
        uid_list = [self.test_root_fo.get_uid()]
        assert self.db_frontend_interface.all_uids_found_in_database(uid_list) is False
        self.db_backend_interface.add_file_object(self.test_root_fo)
        assert self.db_frontend_interface.all_uids_found_in_database([self.test_root_fo.get_uid()]) is True

    def test_get_last_added_firmwares(self):
        assert self.db_frontend_interface.get_last_added_firmwares() == [], 'empty db should result in empty list'
        test_fw_1, root_fo_1 = create_test_firmware(device_name='fw_one')
        self.db_backend_interface.add_firmware(test_fw_1)
        self.db_backend_interface.add_file_object(root_fo_1)
        test_fw_2, root_fo_2 = create_test_firmware(device_name='fw_two', bin_path='container/test.7z')
        self.db_backend_interface.add_firmware(test_fw_2)
        self.db_backend_interface.add_file_object(root_fo_2)
        test_fw_3, root_fo_3 = create_test_firmware(device_name='fw_three', bin_path='container/test.cab')
        self.db_backend_interface.add_firmware(test_fw_3)
        self.db_backend_interface.add_file_object(root_fo_3)
        result = self.db_frontend_interface.get_last_added_firmwares(limit=2)
        assert len(result) == 2, 'Number of results should be 2'
        assert result[0][0] == test_fw_3.uid, 'last firmware is not first entry'
        assert result[1][0] == test_fw_2.uid, 'second last firmware is not the second entry'

    def test_generate_file_tree_node(self):
        _, parent_fo = create_test_firmware()
        child_fo = create_test_file_object()
        child_fo.processed_analysis['file_type'] = {'mime': 'sometype'}
        uid = parent_fo.get_uid()
        child_fo.virtual_file_path = {uid: ['|{}|/folder/{}'.format(uid, child_fo.file_name)]}
        parent_fo.files_included = {child_fo.get_uid()}
        self.db_backend_interface.add_object(parent_fo)
        self.db_backend_interface.add_object(child_fo)
        for node in self.db_frontend_interface.generate_file_tree_node(uid, uid):
            assert isinstance(node, FileTreeNode)
            assert node.name == parent_fo.file_name
            assert node.has_children
        for node in self.db_frontend_interface.generate_file_tree_node(child_fo.get_uid(), uid):
            assert isinstance(node, FileTreeNode)
            assert node.name == 'folder'
            assert node.has_children
            virtual_grand_child = node.get_list_of_child_nodes()[0]
            assert virtual_grand_child.type == 'sometype'
            assert virtual_grand_child.has_children is False
            assert virtual_grand_child.name == child_fo.file_name

    def test_get_number_of_total_matches(self):
        fw, parent_fo = create_test_firmware()
        child_fo = create_test_file_object()
        uid = parent_fo.get_uid()
        child_fo.virtual_file_path = {uid: ['|{}|/folder/{}'.format(uid, child_fo.file_name)]}
        self.db_backend_interface.add_firmware(fw)
        self.db_backend_interface.add_object(parent_fo)
        self.db_backend_interface.add_object(child_fo)
        query = '{{"$or": [{{"_id": "{}"}}, {{"_id": "{}"}}]}}'.format(uid, child_fo.get_uid())
        matches = self.db_frontend_interface.get_number_of_total_matches(query, only_parent_firmwares=False)
        assert matches == 2
        matches = self.db_frontend_interface.get_number_of_total_matches(query, only_parent_firmwares=True)
        assert matches == 1

    def test_get_other_versions_of_firmware(self):
        parent_fw1, _ = create_test_firmware(version='1')
        self.db_backend_interface.add_firmware(parent_fw1)
        parent_fw2, _ = create_test_firmware(version='2', bin_path='container/test.7z')
        self.db_backend_interface.add_firmware(parent_fw2)
        parent_fw3, _ = create_test_firmware(version='3', bin_path='container/test.cab')
        self.db_backend_interface.add_firmware(parent_fw3)

        other_versions = self.db_frontend_interface.get_other_versions_of_firmware(parent_fw1)
        assert len(other_versions) == 2, 'wrong number of other versions'
        assert {'_id': parent_fw2.firmware_id, 'version': '2'} in other_versions
        assert {'_id': parent_fw3.firmware_id, 'version': '3'} in other_versions

        other_versions = self.db_frontend_interface.get_other_versions_of_firmware(parent_fw2)
        assert {'_id': parent_fw3.firmware_id, 'version': '3'} in other_versions
