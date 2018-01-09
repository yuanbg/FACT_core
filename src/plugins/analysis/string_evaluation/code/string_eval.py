import os
import sys

from common_helper_files import get_dir_of_file

from analysis.PluginBase import BasePlugin

THIS_FILE_DIR = get_dir_of_file(__file__)
sys.path.append(os.path.join(THIS_FILE_DIR, '..', 'internal'))
from string_eval import eval_strings


class AnalysisPlugin(BasePlugin):
    '''
    Sort strings by relevance

    Credits:
    Original version by Paul Schiffer created during Firmware Bootcamp WT16/17 at University of Bonn
    Refactored and improved by Fraunhofer FKIE
    '''
    NAME = 'string_evaluator'
    DEPENDENCYS = ['printable_strings']
    DESCRIPTION = 'Tries to sort strings based on usefulness'
    VERSION = '0.2'

    def __init__(self, plugin_adminstrator, config=None, recursive=True, timeout=300):
        super().__init__(plugin_adminstrator, config=config, recursive=recursive, timeout=timeout, plugin_path=__file__)

    def process_object(self, file_object):
        list_of_printable_strings = file_object.processed_analysis['printable_strings']['strings']
        file_object.processed_analysis[self.NAME] = dict(string_eval=eval_strings(list_of_printable_strings))
        return file_object
