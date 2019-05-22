# pylint: disable=attribute-defined-outside-init,wrong-import-order
from multiprocessing import Event, Value
from tempfile import TemporaryDirectory
from unittest import mock

import gc

from helperFunctions.data_conversion import normalize_compare_id
from helperFunctions.fileSystem import get_test_data_dir
from helperFunctions.web_interface import ConnectTo
from objects.file import FileObject
from objects.firmware import Firmware
from scheduler.Analysis import AnalysisScheduler
from scheduler.Compare import CompareScheduler
from scheduler.Unpacking import UnpackingScheduler
from storage.MongoMgr import MongoMgr
from storage.db_interface_backend import BackEndDbInterface
from storage.db_interface_compare import CompareDbInterface
from test.common_helper import clean_test_database, get_database_names
from test.integration.common import MockFSOrganizer, initialize_config


class TestFileAddition:

    @mock.patch('unpacker.unpack.FS_Organizer', MockFSOrganizer)
    def setup_method(self):
        self._tmp_dir = TemporaryDirectory()
        self._config = initialize_config(self._tmp_dir)
        self.elements_finished_analyzing = Value('i', 0)
        self.analysis_finished_event = Event()
        self.compare_finished_event = Event()

        self._mongo_server = MongoMgr(config=self._config, auth=False)
        self.backend_interface = BackEndDbInterface(config=self._config)

        self._analysis_scheduler = AnalysisScheduler(config=self._config, post_analysis=self.count_analysis_finished_event)
        self._unpack_scheduler = UnpackingScheduler(config=self._config, post_unpack=self._analysis_scheduler.add_task)
        self._compare_scheduler = CompareScheduler(config=self._config, callback=self.trigger_compare_finished_event)

    def count_analysis_finished_event(self, fw_object):
        self.backend_interface.add_analysis(fw_object)
        self.elements_finished_analyzing.value += 1
        if self.elements_finished_analyzing.value == 4 * 2 * 2:  # 2 container with 3 files each and 2 plugins
            self.analysis_finished_event.set()

    def trigger_compare_finished_event(self):
        self.compare_finished_event.set()

    def teardown_method(self):
        self._compare_scheduler.shutdown()
        self._unpack_scheduler.shutdown()
        self._analysis_scheduler.shutdown()

        clean_test_database(self._config, get_database_names(self._config))
        self._mongo_server.shutdown()

        self._tmp_dir.cleanup()
        gc.collect()

    def test_unpack_analyse_and_compare(self):
        test_fo_1 = FileObject(file_path='{}/container/test.zip'.format(get_test_data_dir()))
        test_fw_1 = Firmware(uid=test_fo_1.get_uid())
        test_fw_1.release_date = '2017-01-01'

        test_fo_2 = FileObject(file_path='{}/regression_one'.format(get_test_data_dir()))
        test_fw_2 = Firmware(uid=test_fo_2.get_uid())
        test_fw_2.release_date = '2017-01-01'

        self._unpack_scheduler.add_task(test_fo_1)
        self._unpack_scheduler.add_task(test_fo_2)

        self.analysis_finished_event.wait(timeout=20)

        compare_id = normalize_compare_id(';'.join([fw.uid for fw in [test_fw_1, test_fw_2]]))

        assert self._compare_scheduler.add_task((compare_id, False)) is None, 'adding compare task creates error'

        self.compare_finished_event.wait(timeout=10)

        with ConnectTo(CompareDbInterface, self._config) as sc:
            result = sc.get_compare_result(compare_id)

        assert result['plugins']['Software'] == self._expected_result()['Software']
        assert len(result['plugins']['File_Coverage']['files_in_common']) == len(self._expected_result()['File_Coverage']['files_in_common'])

    @staticmethod
    def _expected_result():
        return {
            'File_Coverage': {
                'files_in_common': {
                    'all': [],
                    'collapse': False
                }
            },
            'Software': {
                'Compare Skipped': {
                    'all': 'Required analysis not present: [\'software_components\', \'software_components\']'
                }
            }
        }
