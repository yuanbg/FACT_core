# pylint: disable=attribute-defined-outside-init,unused-variable,wrong-import-order
from tempfile import TemporaryDirectory

import gc

from helperFunctions.config import get_config_for_testing
from storage.MongoMgr import MongoMgr
from storage.db_interface_backend import BackEndDbInterface
from storage.db_interface_frontend import FrontEndDbInterface
from storage.db_interface_frontend_editing import FrontendEditingDbInterface
from test.common_helper import create_test_firmware

TMP_DIR = TemporaryDirectory(prefix='fact_test_')


class TestStorageDbInterfaceFrontendEditing:

    @classmethod
    def setup_class(cls):
        cls._config = get_config_for_testing(TMP_DIR)
        cls.mongo_server = MongoMgr(config=cls._config)

    def setup_method(self):
        self.db_frontend_editing = FrontendEditingDbInterface(config=self._config)
        self.db_frontend_interface = FrontEndDbInterface(config=self._config)
        self.db_backend_interface = BackEndDbInterface(config=self._config)

    def teardown_method(self):
        self.db_frontend_editing.shutdown()
        self.db_frontend_interface.shutdown()
        self.db_backend_interface.client.drop_database(self._config.get('data_storage', 'main_database'))
        self.db_backend_interface.shutdown()
        gc.collect()

    @classmethod
    def teardown_class(cls):
        cls.mongo_server.shutdown()
        TMP_DIR.cleanup()

    def test_add_comment_to_fo(self):
        _, test_fo = create_test_firmware()
        self.db_backend_interface.add_object(test_fo)
        comment, author, uid, time = 'this is a test comment!', 'author', test_fo.get_uid(), 1234567890
        self.db_frontend_editing.add_comment_to_object(uid, comment, author, time)
        test_fw = self.db_backend_interface.get_object(uid)
        assert test_fw.comments[0] == {'time': str(time), 'author': author, 'comment': comment}

    def test_add_comment_to_fw(self):
        test_fw, _ = create_test_firmware()
        self.db_backend_interface.add_firmware(test_fw)
        comment, author, uid, time = 'this is a test comment!', 'author', test_fw.firmware_id, 1234567890
        self.db_frontend_editing.add_comment_to_object(test_fw.firmware_id, comment, author, time)
        test_fw = self.db_backend_interface.get_firmware(test_fw.firmware_id)
        assert test_fw.comments[0] == {'time': str(time), 'author': author, 'comment': comment}

    def test_get_latest_comments(self):
        test_comments = [
            {'time': '1234567890', 'author': 'author1', 'comment': 'test comment'},
            {'time': '1234567899', 'author': 'author2', 'comment': 'test comment2'}
        ]
        test_fw = self._add_test_fw_with_comments_to_db()
        latest_comments = self.db_frontend_interface.get_latest_comments()
        test_comments.sort(key=lambda x: x['time'], reverse=True)
        assert len(test_comments) == len(latest_comments)
        for test_comment, retrieved_comment in zip(test_comments, latest_comments):
            for key in ['time', 'author', 'comment']:
                assert test_comment[key] == retrieved_comment[key]
            assert retrieved_comment['uid'] == test_fw.firmware_id

    def test_remove_element_from_array_in_field(self):
        test_fw = self._add_test_fw_with_comments_to_db()
        retrieved_fw = self.db_backend_interface.get_firmware(test_fw.firmware_id)
        assert len(retrieved_fw.comments) == 2, 'comments were not saved correctly'

        self.db_frontend_editing.remove_element_from_array_in_field(test_fw.firmware_id, 'comments', {'time': '1234567899'})
        retrieved_fw = self.db_backend_interface.get_firmware(test_fw.firmware_id)
        assert len(retrieved_fw.comments) == 1, 'comment was not deleted'

    def test_delete_comment(self):
        test_fw = self._add_test_fw_with_comments_to_db()
        retrieved_fw = self.db_backend_interface.get_firmware(test_fw.firmware_id)
        assert len(retrieved_fw.comments) == 2, 'comments were not saved correctly'

        self.db_frontend_editing.delete_comment(test_fw.firmware_id, '1234567899')
        retrieved_fw = self.db_backend_interface.get_firmware(test_fw.firmware_id)
        assert len(retrieved_fw.comments) == 1, 'comment was not deleted'

    def _add_test_fw_with_comments_to_db(self):
        test_fw, _ = create_test_firmware()
        comments = [
            {'time': '1234567890', 'author': 'author1', 'comment': 'test comment'},
            {'time': '1234567899', 'author': 'author2', 'comment': 'test comment2'}
        ]
        test_fw.comments.extend(comments)
        self.db_backend_interface.add_firmware(test_fw)
        return test_fw
