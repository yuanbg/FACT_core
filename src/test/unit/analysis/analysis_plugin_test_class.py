import gc
import unittest
import unittest.mock
from configparser import ConfigParser

import pytest

from test.common_helper import DatabaseMock, create_docker_mount_base_dir, fake_exit, load_users_from_main_config


@pytest.mark.usefixtures('patch_cfg')
class AnalysisPluginTest(unittest.TestCase):
    '''
    This is the base class for analysis plugin test.unit
    '''

    PLUGIN_NAME = 'plugin_test'

    def setUp(self):
        self.mocked_interface = DatabaseMock()

        self.enter_patch = unittest.mock.patch(target='helperFunctions.database.ConnectTo.__enter__', new=lambda _: self.mocked_interface)
        self.enter_patch.start()

        self.exit_patch = unittest.mock.patch(target='helperFunctions.database.ConnectTo.__exit__', new=fake_exit)
        self.exit_patch.start()

        self.docker_mount_base_dir = create_docker_mount_base_dir()

    def tearDown(self):

        self.analysis_plugin.shutdown()  # pylint: disable=no-member

        self.enter_patch.stop()
        self.exit_patch.stop()

        self.mocked_interface.shutdown()
        gc.collect()

    def init_basic_config(self):
        config = ConfigParser()
        config.add_section(self.PLUGIN_NAME)
        config.set(self.PLUGIN_NAME, 'threads', '1')
        config.add_section('expert-settings')
        config.set('expert-settings', 'block-delay', '0.1')
        config.add_section('data-storage')
        load_users_from_main_config(config)
        config.set('data-storage', 'mongo-server', 'localhost')
        config.set('data-storage', 'mongo-port', '54321')
        config.set('data-storage', 'view-storage', 'tmp_view')
        config.set('data-storage', 'docker-mount-base-dir', str(self.docker_mount_base_dir))
        return config

    def register_plugin(self, name, plugin_object):
        '''
        This is a mock checking if the plugin registers correctly
        '''
        self.assertEqual(name, self.PLUGIN_NAME, 'plugin registers with wrong name')
        self.assertEqual(plugin_object.NAME, self.PLUGIN_NAME, 'plugin object has wrong name')
        self.assertIsInstance(plugin_object.DESCRIPTION, str)
        self.assertIsInstance(plugin_object.VERSION, str)
        self.assertNotEqual(plugin_object.VERSION, 'not set', 'Plug-in version not set')
