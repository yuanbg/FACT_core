import gc
import os
import unittest
from tempfile import TemporaryDirectory
from unittest import mock

from intercom.back_end_dispatcher import (
    InterComBackEndAnalysisPlugInsPublisher, InterComBackEndAnalysisTask, InterComBackEndCompareTask,
    InterComBackEndRawDownloadTask, InterComBackEndReAnalyzeTask, InterComBackEndSingleFileTask,
    InterComBackEndTarRepackTask
)
from intercom.back_end_interface import InterComBackEndInterface
from intercom.front_end_dispatcher import InterComFrontEndWebhookTask
from intercom.front_end_interface import InterComFrontEndInterface
from storage.fs_organizer import FS_Organizer
from storage.MongoMgr import MongoMgr
from test.common_helper import create_test_firmware, get_config_for_testing


class AnalysisServiceMock:

    def __init__(self, config=None):
        pass

    def get_plugin_dict(self):  # pylint: disable=no-self-use
        return {'dummy': 'dummy description'}


class TestInterComTaskCommunication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = TemporaryDirectory(prefix='fact_test_')
        cls.config = get_config_for_testing(temp_dir=cls.tmp_dir)
        cls.config.set('ExpertSettings', 'communication_timeout', '1')
        cls.mongo_server = MongoMgr(config=cls.config)

    def setUp(self):
        self.listener = None
        self.interface = None

    def tearDown(self):
        if self.interface:
            for item in self.interface.connections.keys():
                self.interface.client.drop_database(self.interface.connections[item]['name'])
            self.interface.shutdown()
        if self.listener:
            self.listener.shutdown()
        gc.collect()

    @classmethod
    def tearDownClass(cls):
        cls.mongo_server.shutdown()
        cls.tmp_dir.cleanup()


class TestInterComFrontendToBackend(TestInterComTaskCommunication):

    def setUp(self):
        self.interface = InterComFrontEndInterface(config=self.config)
        self.listener = None

    def test_analysis_task(self):
        self.listener = InterComBackEndAnalysisTask(config=self.config)
        test_fw = create_test_firmware()
        test_fw.file_path = None
        self.interface.add_analysis_task(test_fw)
        task = self.listener.get_next_task()
        self.assertEqual(task.uid, test_fw.uid, 'uid not correct')
        self.assertIsNotNone(task.file_path, 'file_path not set')
        self.assertTrue(os.path.exists(task.file_path), 'file does not exist')

    def test_single_file_task(self):
        self.listener = InterComBackEndSingleFileTask(config=self.config)
        test_fw = create_test_firmware()
        test_fw.file_path = None
        test_fw.scheduled_analysis = ['binwalk']
        self.interface.add_single_file_task(test_fw)
        task = self.listener.get_next_task()

        assert task.uid == test_fw.uid, 'uid not transported correctly'
        assert task.scheduled_analysis

    def test_re_analyze_task(self):
        self.listener = InterComBackEndReAnalyzeTask(config=self.config)
        fs_organizer = FS_Organizer(config=self.config)
        test_fw = create_test_firmware()
        fs_organizer.store_file(test_fw)
        original_file_path = test_fw.file_path
        original_binary = test_fw.binary
        test_fw.file_path = None
        test_fw.binary = None
        self.interface.add_re_analyze_task(test_fw)
        task = self.listener.get_next_task()
        self.assertEqual(task.uid, test_fw.uid, 'uid not correct')
        self.assertIsNotNone(task.file_path, 'file path not set')
        self.assertEqual(task.file_path, original_file_path)
        self.assertIsNotNone(task.binary, 'binary not set')
        self.assertEqual(task.binary, original_binary, 'binary content not correct')

    def test_compare_task(self):
        self.listener = InterComBackEndCompareTask(config=self.config)
        self.interface.add_compare_task('valid_id', force=False)
        result = self.listener.get_next_task()
        self.assertEqual(result, ('valid_id', False))

    def test_analysis_plugin_publication(self):
        self.listener = InterComBackEndAnalysisPlugInsPublisher(config=self.config, analysis_service=AnalysisServiceMock())
        plugins = self.interface.get_available_analysis_plugins()
        self.assertEqual(len(plugins), 1, 'Not all plug-ins found')
        self.assertEqual(plugins, {'dummy': 'dummy description'}, 'content not correct')

    def test_analysis_plugin_publication_not_available(self):
        with self.assertRaises(Exception):
            self.interface.get_available_analysis_plugins()

    @mock.patch('intercom.front_end_interface.generate_task_id')
    @mock.patch('intercom.back_end_dispatcher.BinaryService')
    def test_raw_download_task(self, binary_service_mock, generate_task_id_mock):
        binary_service_mock().get_binary_and_file_name.return_value = (b'test', 'test.txt')
        generate_task_id_mock.return_value = 'valid_uid_0.0'

        result = self.interface.get_binary_and_filename('valid_uid')
        self.assertIsNone(result, 'should be none because of timeout')

        self.listener = InterComBackEndRawDownloadTask(config=self.config)
        task = self.listener.get_next_task()
        self.assertEqual(task, 'valid_uid', 'task not correct')
        result = self.interface.get_binary_and_filename('valid_uid_0.0')
        self.assertEqual(result, (b'test', 'test.txt'), 'retrieved binary not correct')

    @mock.patch('intercom.front_end_interface.generate_task_id')
    @mock.patch('intercom.back_end_dispatcher.BinaryService')
    def test_tar_repack_task(self, binary_service_mock, generate_task_id_mock):
        binary_service_mock().get_repacked_binary_and_file_name.return_value = (b'test', 'test.tar')
        generate_task_id_mock.return_value = 'valid_uid_0.0'

        result = self.interface.get_repacked_binary_and_file_name('valid_uid')
        self.assertIsNone(result, 'should be none because of timeout')

        self.listener = InterComBackEndTarRepackTask(config=self.config)
        task = self.listener.get_next_task()
        self.assertEqual(task, 'valid_uid', 'task not correct')
        result = self.interface.get_repacked_binary_and_file_name('valid_uid_0.0')
        self.assertEqual(result, (b'test', 'test.tar'), 'retrieved binary not correct')


class TestInterComBackendToFrontend(TestInterComTaskCommunication):

    def setUp(self):
        self.interface = InterComBackEndInterface(config=self.config)
        self.listener = None

    def test_webhook_task(self):
        self.listener = InterComFrontEndWebhookTask(config=self.config)
        test_url = 'https://foo.bar'
        self.interface.send_webhook_message(test_url, 'deadbeef_123456')
        task = self.listener.get_next_task()

        assert task == test_url
