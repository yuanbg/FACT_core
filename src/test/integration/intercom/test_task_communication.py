# pylint: disable=no-self-use,invalid-name,attribute-defined-outside-init,wrong-import-order
import os
from tempfile import TemporaryDirectory
from unittest import mock

import gc
import pytest

from helperFunctions.config import get_config_for_testing
from intercom.back_end_binding import (
    InterComBackEndAnalysisPlugInsPublisher, InterComBackEndAnalysisTask, InterComBackEndCompareTask,
    InterComBackEndRawDownloadTask, InterComBackEndReAnalyzeTask, InterComBackEndTarRepackTask,
)
from intercom.front_end_binding import InterComFrontEndBinding
from storage.MongoMgr import MongoMgr
from storage.fs_organizer import FS_Organizer
from test.common_helper import create_test_firmware

TMP_DIR = TemporaryDirectory(prefix='fact_test_')


class AnalysisServiceMock:

    def __init__(self, config=None):
        pass

    def get_plugin_dict(self):
        return {'dummy': 'dummy description'}


class TestInterComTaskCommunication:

    @classmethod
    def setup_class(cls):
        cls.config = get_config_for_testing(temp_dir=TMP_DIR)
        cls.config.set('ExpertSettings', 'communication_timeout', '1')
        cls.mongo_server = MongoMgr(config=cls.config)

    def setup_method(self):
        self.frontend = InterComFrontEndBinding(config=self.config)
        self.backend = None

    def teardown_method(self):
        for item in self.frontend.connections.keys():
            self.frontend.client.drop_database(self.frontend.connections[item]['name'])
        if self.backend:
            self.backend.shutdown()
        self.frontend.shutdown()
        gc.collect()

    @classmethod
    def teardown_class(cls):
        cls.mongo_server.shutdown()
        TMP_DIR.cleanup()

    def test_analysis_task(self):
        self.backend = InterComBackEndAnalysisTask(config=self.config)
        _, root_fo = create_test_firmware()
        root_fo.file_path = None
        self.frontend.add_analysis_task(root_fo)
        task = self.backend.get_next_task()
        assert task.get_uid() == root_fo.get_uid(), 'uid not correct'
        assert task.file_path is not None, 'file_path not set'
        assert os.path.exists(task.file_path), 'file does not exist'

    def test_re_analyze_task(self):
        self.backend = InterComBackEndReAnalyzeTask(config=self.config)
        fs_organizer = FS_Organizer(config=self.config)
        _, root_fo = create_test_firmware()
        fs_organizer.store_file(root_fo)
        original_file_path = root_fo.file_path
        original_binary = root_fo.binary
        root_fo.file_path = None
        root_fo.binary = None
        self.frontend.add_re_analyze_task(root_fo)
        task = self.backend.get_next_task()
        assert task.get_uid() == root_fo.get_uid(), 'uid not correct'
        assert task.file_path is not None, 'file path not set'
        assert task.file_path == original_file_path
        assert task.binary is not None, 'binary not set'
        assert task.binary == original_binary, 'binary content not correct'

    def test_compare_task(self):
        self.backend = InterComBackEndCompareTask(config=self.config)
        self.frontend.add_compare_task('valid_id', force=False)
        result = self.backend.get_next_task()
        assert result == ('valid_id', False)

    def test_analysis_plugin_publication(self):
        self.backend = InterComBackEndAnalysisPlugInsPublisher(config=self.config, analysis_service=AnalysisServiceMock())
        plugins = self.frontend.get_available_analysis_plugins()
        assert len(plugins) == 1, 'Not all plug-ins found'
        assert plugins == {'dummy': 'dummy description'}, 'content not correct'

    def test_analysis_plugin_publication_not_available(self):
        with pytest.raises(Exception):
            self.frontend.get_available_analysis_plugins()

    @mock.patch('intercom.front_end_binding.generate_task_id')
    @mock.patch('intercom.back_end_binding.BinaryService')
    def test_raw_download_task(self, binaryServiceMock, generateTaskIdMock):
        binaryServiceMock().get_binary_and_file_name.return_value = (b'test', 'test.txt')
        generateTaskIdMock.return_value = 'valid_uid_0.0'

        result = self.frontend.get_binary_and_filename('valid_uid')
        assert result is None, 'should be none because of timeout'

        self.backend = InterComBackEndRawDownloadTask(config=self.config)
        task = self.backend.get_next_task()
        assert task == 'valid_uid', 'task not correct'
        result = self.frontend.get_binary_and_filename('valid_uid_0.0')
        assert result == (b'test', 'test.txt'), 'retrieved binary not correct'

    @mock.patch('intercom.front_end_binding.generate_task_id')
    @mock.patch('intercom.back_end_binding.BinaryService')
    def test_tar_repack_task(self, binaryServiceMock, generateTaskIdMock):
        binaryServiceMock().get_repacked_binary_and_file_name.return_value = (b'test', 'test.tar')
        generateTaskIdMock.return_value = 'valid_uid_0.0'

        result = self.frontend.get_repacked_binary_and_file_name('valid_uid')
        assert result is None, 'should be none because of timeout'

        self.backend = InterComBackEndTarRepackTask(config=self.config)
        task = self.backend.get_next_task()
        assert task == 'valid_uid', 'task not correct'
        result = self.frontend.get_repacked_binary_and_file_name('valid_uid_0.0')
        assert result == (b'test', 'test.tar'), 'retrieved binary not correct'
