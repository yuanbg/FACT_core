import logging
from typing import List, Optional

from helperFunctions.plugin import import_plugins
from objects.file import FileObject
from objects.firmware import Firmware
from storage.binary_service import BinaryService
from storage.db_interface_compare import CompareDbInterface


class Compare:
    '''
    This Module compares firmware images
    '''

    compare_plugins = {}

    def __init__(self, config=None, db_interface: CompareDbInterface = None):
        '''
        Constructor
        '''
        self.config = config
        self.db_interface = db_interface
        self._setup_plugins()
        logging.info('Plug-ins available: {}'.format(list(self.compare_plugins.keys())))

    def compare(self, id_list):
        logging.info('Compare in progress: {}'.format(id_list))
        bs = BinaryService(config=self.config)

        fo_list, fw_list = [], []
        for id_ in id_list:
            try:
                if self.db_interface.is_firmware_id(id_):
                    fw = self.db_interface.get_firmware(id_)
                    uid = fw.uid
                else:
                    fw = None
                    uid = id_
                fo = self.db_interface.get_complete_object_including_all_summaries(uid)
                fo.binary = bs.get_binary_and_file_name(fo.uid)[0]
                fo_list.append(fo)
                fw_list.append(fw)
            except Exception as exception:
                return exception

        return self.compare_objects(fo_list, fw_list)

    def compare_objects(self, fo_list: List[FileObject], fw_list: List[Optional[Firmware]]) -> dict:
        return {
            'general': self._create_general_section_dict(fo_list, fw_list),
            'plugins': self._execute_compare_plugins(fo_list)
        }

    @staticmethod
    def _create_general_section_dict(fo_list: List[FileObject], fw_list: List[Optional[Firmware]]) -> dict:
        general = {}
        for fo, fw in zip(fo_list, fw_list):
            if fw:
                fo.root_uid = fw.uid
                for attribute in ['device_name', 'device_part', 'device_class', 'vendor', 'version', 'release_date']:
                    general.setdefault(attribute, {})[fw.uid] = getattr(fw, attribute)
            else:
                general.setdefault('firmwares_including_this_file', {})[fo.get_uid()] = list(fo.get_virtual_file_paths())
            general.setdefault('hid', {})[fo.get_uid()] = fo.get_hid()
            general.setdefault('size', {})[fo.get_uid()] = fo.size
            general.setdefault('virtual_file_path', {})[fo.get_uid()] = fo.get_virtual_paths_for_one_uid()
            general.setdefault('number_of_files', {})[fo.get_uid()] = len(fo.list_of_all_included_files)
        return general

# --- plug-in system ---

    def _setup_plugins(self):
        self.compare_plugins = {}
        self._init_plugins()

    def _init_plugins(self):
        self.source = import_plugins('compare.plugins', 'plugins/compare')
        for plugin_name in self.source.list_plugins():
            plugin = self.source.load_plugin(plugin_name)
            plugin.ComparePlugin(self, config=self.config, db_interface=self.db_interface)

    def register_plugin(self, name, c_plugin_instance):
        self.compare_plugins[name] = c_plugin_instance

    def _execute_compare_plugins(self, fo_list):
        plugin_results = {}
        for plugin in self.compare_plugins:
            plugin_results[plugin] = self.compare_plugins[plugin].compare(fo_list)
        return plugin_results
