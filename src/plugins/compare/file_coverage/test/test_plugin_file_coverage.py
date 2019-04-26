# pylint: disable=protected-access,unused-argument,no-self-use,wrong-import-order
from plugins.compare.file_coverage.code.file_coverage import ComparePlugin
from test.unit.compare.compare_plugin_test_class import TestComparePlugin


class DbMock:
    def __init__(self, config):
        pass

    def get_entropy(self, uid):
        return 0.2

    def get_ssdeep_hash(self, uid):
        return '42'


class TestComparePluginFileCoverage(TestComparePlugin):

    # This name must be changed according to the name of plug-in to test
    PLUGIN_NAME = 'File_Coverage'

    def setup_plugin(self):
        '''
        This function must be overwritten by the test instance.
        In most cases it is sufficient to copy this function.
        '''
        return ComparePlugin(self, config=self.config, db_interface=DbMock(None), plugin_path=None)

    def test_get_intersection_of_files(self):
        self.root_fo_one.list_of_all_included_files.append('foo')
        self.root_fo_two.list_of_all_included_files.append('foo')
        result = self.c_plugin._get_intersection_of_files([self.root_fo_one, self.root_fo_two])
        assert isinstance(result, dict), 'result is not a dict'
        assert 'all' in result, 'all field not present'
        assert result['all'] == ['foo'], 'intersection not correct'

    def test_get_exclusive_files(self):
        result = self.c_plugin._get_exclusive_files([self.root_fo_one, self.root_fo_two])
        assert isinstance(result, dict), 'result is not a dict'
        assert self.fw_one.uid in result, 'fw_one entry not found in result'
        assert self.fw_two.uid in result, 'fw_two entry not found in result'
        assert self.fw_one.uid in result[self.fw_one.uid], 'fw_one not exclusive to one'
        assert self.fw_two.uid not in result[self.fw_one.uid], 'fw_two in exclusive file of fw one'

    def test_get_files_in_more_than_one_but_not_in_all(self):
        self.root_fo_one.list_of_all_included_files.append('foo')
        self.root_fo_two.list_of_all_included_files.append('foo')
        fo_list = [self.root_fo_one, self.root_fo_two, self.root_fo_three]
        tmp_result_dict = {
            'files_in_common': {'all': set()},
            'exclusive_files': {fo.get_uid(): {} for fo in fo_list}
        }
        result = self.c_plugin._get_files_in_more_than_one_but_not_in_all(fo_list, tmp_result_dict)
        assert isinstance(result, dict), 'result is not a dict'
        assert 'foo' in result[self.fw_one.uid], 'foo not in result fw one'
        assert 'foo' in result[self.fw_two.uid], 'foo not in result fw_two'
        assert 'foo' not in result[self.fw_three.uid], 'foo in result fw_three'

    def test_run_compare_plugin(self):
        self.root_fo_one.list_of_all_included_files.append('foo')
        self.root_fo_two.list_of_all_included_files.append('foo')
        result = self.c_plugin.compare_function([self.root_fo_one, self.root_fo_two])
        assert len(result.keys()) == 4
