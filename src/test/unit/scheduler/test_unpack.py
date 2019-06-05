# pylint: disable=protected-access,wrong-import-order,attribute-defined-outside-init

from configparser import ConfigParser
from multiprocessing import Queue
from tempfile import TemporaryDirectory
from time import sleep

import gc

from helperFunctions.fileSystem import get_test_data_dir
from objects.file import FileObject
from scheduler.Unpacking import UnpackingScheduler
from test.common_helper import DatabaseMock


class TestUnpackScheduler:

    def setup_method(self):
        self.tmp_dir = TemporaryDirectory()
        self.config = ConfigParser()
        self.config.add_section('unpack')
        self.config.set('unpack', 'threads', '2')
        self.config.set('unpack', 'max_depth', '3')
        self.config.set('unpack', 'whitelist', '')
        self.config.add_section('ExpertSettings')
        self.config.set('ExpertSettings', 'block_delay', '1')
        self.config.set('ExpertSettings', 'unpack_throttle_limit', '10')
        self.config.add_section('data_storage')
        self.config.set('data_storage', 'firmware_file_storage_directory', self.tmp_dir.name)
        self.tmp_queue = Queue()
        self.sched = None

    def teardown_method(self):
        if self.sched:
            self.sched.shutdown()
        self.tmp_dir.cleanup()
        self.tmp_queue.close()
        gc.collect()

    def test_unpack_a_container_including_another_container(self):
        self._start_scheduler()
        test_fw = FileObject(file_path='{}/container/test_zip.tar.gz'.format(get_test_data_dir()))
        self.sched.add_task(test_fw)
        outer_container = self.tmp_queue.get(timeout=5)
        assert len(outer_container.files_included) == 2, 'not all childs of root found'
        assert 'ab4153d747f530f9bc3a4b71907386f50472ea5ae975c61c0bacd918f1388d4b_227' in outer_container.files_included, 'included container not extracted. Unpacker tar.gz modul broken?'
        included_files = [self.tmp_queue.get(timeout=5), self.tmp_queue.get(timeout=5)]
        for item in included_files:
            if item.get_uid() == 'ab4153d747f530f9bc3a4b71907386f50472ea5ae975c61c0bacd918f1388d4b_227':
                assert len(item.files_included) == 1, 'number of files in included container not correct'
            else:
                assert item.get_uid() == 'faa11db49f32a90b51dfc3f0254f9fd7a7b46d0b570abd47e1943b86d554447a_28', 'none container file not rescheduled'

    def test_get_combined_analysis_workload(self):
        self._start_scheduler()
        result = self.sched._get_combined_analysis_workload()
        assert result == 3, 'workload calculation not correct'

    def test_throttle(self):
        self.config.set('ExpertSettings', 'unpack_throttle_limit', '-1')
        self._start_scheduler()
        sleep(0.5)
        assert self.sched.throttle_condition.value == 1, 'throttle not functional'

    def _start_scheduler(self):
        self.sched = UnpackingScheduler(config=self.config, post_unpack=self._mock_callback, analysis_workload=self._mock_get_analysis_workload, db_interface=DatabaseMock())

    def _mock_callback(self, fw):
        self.tmp_queue.put(fw)

    @staticmethod
    def _mock_get_analysis_workload():
        return {'a': 1, 'b': 2}
