# pylint: disable=attribute-defined-outside-init,wrong-import-order
import gc
import magic

from helperFunctions.config import get_config_for_testing
from storage.MongoMgr import MongoMgr
from storage.binary_service import BinaryService
from storage.db_interface_backend import BackEndDbInterface
from test.common_helper import create_test_firmware

_, TEST_FO = create_test_firmware()


class TestBinaryService:

    def setup_method(self):
        self.config = get_config_for_testing()
        self.mongo_server = MongoMgr(config=self.config)
        self._init_test_data()
        self.binary_service = BinaryService(config=self.config)

    def _init_test_data(self):
        self.backend_db_interface = BackEndDbInterface(config=self.config)
        self.backend_db_interface.add_file_object(TEST_FO)
        self.backend_db_interface.shutdown()

    def teardown_method(self):
        self.mongo_server.shutdown()
        gc.collect()

    def test_get_binary_and_file_name(self):
        binary, file_name = self.binary_service.get_binary_and_file_name(TEST_FO.get_uid())
        assert file_name == TEST_FO.file_name, 'file_name not correct'
        assert binary == TEST_FO.binary, 'invalid result not correct'

    def test_get_binary_and_file_name_invalid_uid(self):
        binary, file_name = self.binary_service.get_binary_and_file_name('invalid_uid')
        assert binary is None, 'should be none'
        assert file_name is None, 'should be none'

    def test_get_repacked_binary_and_file_name(self):
        tar, file_name = self.binary_service.get_repacked_binary_and_file_name(TEST_FO.get_uid())
        assert file_name == '{}.tar.gz'.format(TEST_FO.file_name), 'file_name not correct'
        file_type = magic.from_buffer(tar, mime=True)
        assert file_type == 'application/gzip', 'file type not tar'

    def test_get_repacked_binary_and_file_name_invalid_uid(self):
        binary, file_name = self.binary_service.get_repacked_binary_and_file_name('invalid_uid')
        assert binary is None, 'should be none'
        assert file_name is None, 'should be none'
