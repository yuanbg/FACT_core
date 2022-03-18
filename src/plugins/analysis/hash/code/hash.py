import logging
from hashlib import algorithms_available

from analysis.PluginBase import AnalysisBasePlugin
from config import _parse_comma_separated_list, cfg
from helperFunctions.hash import get_hash, get_imphash, get_ssdeep, get_tlsh


class AnalysisPlugin(AnalysisBasePlugin):
    '''
    This Plugin creates several hashes of the file
    '''
    NAME = 'file_hashes'
    DEPENDENCIES = ['file_type']
    DESCRIPTION = 'calculate different hash values of the file'
    VERSION = '1.2'

    def __init__(self, plugin_administrator, recursive=True):
        '''
        recursive flag: If True recursively analyze included files
        default flags should be edited above. Otherwise the scheduler cannot overwrite them.
        '''
        hashes = getattr(cfg, self.NAME).get('hashes', 'sha256')
        self.hashes_to_create = _parse_comma_separated_list(hashes)

        # additional init stuff can go here

        super().__init__(plugin_administrator, recursive=recursive, plugin_path=__file__, timeout=600)

    def process_object(self, file_object):
        '''
        This function must be implemented by the plugin.
        Analysis result must be a dict stored in file_object.processed_analysis[self.NAME]
        If you want to propagate results to parent objects store a list of strings 'summary' entry of your result dict
        '''
        file_object.processed_analysis[self.NAME] = {}
        for hash_ in self.hashes_to_create:
            if hash_ in algorithms_available:
                file_object.processed_analysis[self.NAME][hash_] = get_hash(hash_, file_object.binary)
            else:
                logging.debug(f'algorithm {hash_} not available')
        file_object.processed_analysis[self.NAME]['ssdeep'] = get_ssdeep(file_object.binary)
        file_object.processed_analysis[self.NAME]['imphash'] = get_imphash(file_object)

        tlsh_hash = get_tlsh(file_object.binary)
        if tlsh_hash:
            file_object.processed_analysis[self.NAME]['tlsh'] = get_tlsh(file_object.binary)

        return file_object
