# pylint: disable=protected-access
from test.unit.compare.compare_plugin_test_class import TestComparePlugin

from ..code.software import ComparePlugin


class TestComparePluginSoftware(TestComparePlugin):

    # This name must be changed according to the name of plug-in to test
    PLUGIN_NAME = "Software"

    def setup_plugin(self):
        """
        This function must be overwritten by the test instance.
        In most cases it is sufficient to copy this function.
        """
        return ComparePlugin(self, config=self.config)

    def test_get_intersection_of_software(self):
        self.root_fo_one.processed_analysis['software_components'] = {'summary': {'software a': self.fw_one.uid}}
        self.root_fo_two.processed_analysis['software_components'] = {'summary': {'software a': self.fw_two.uid, 'software b': self.fw_two.uid}}
        result = self.c_plugin._get_intersection_of_software([self.root_fo_one, self.root_fo_two])
        assert isinstance(result, dict), "result is not a dict"
        assert 'all' in result, "all field not present"
        assert result['all'] == ['software a'], "intersection not correct"
        assert result['collapse']

    def test_get_exclustive_software(self):
        self.root_fo_one.processed_analysis['software_components'] = {'summary': {'software a': self.fw_one.uid}}
        self.root_fo_two.processed_analysis['software_components'] = {'summary': {}}
        result = self.c_plugin._get_exclusive_software([self.root_fo_one, self.root_fo_two])
        assert isinstance(result, dict), "result is not a dict"
        assert self.fw_one.uid in result, "fw_one entry not found in result"
        assert self.fw_two.uid in result, "fw_two entry not found in result"
        assert 'software a' in result[self.fw_one.uid], "fw_one not exclusive to one"
        assert 'software a' not in result[self.fw_two.uid], "fw_two in exclusive file of fw one"
        assert result['collapse']

    def test_get_software_in_more_than_one_but_not_in_all(self):
        self.root_fo_one.processed_analysis['software_components'] = {'summary': {'software a': self.fw_one.uid}}
        self.root_fo_two.processed_analysis['software_components'] = {'summary': {'software a': self.fw_two.uid}}
        self.root_fo_three.processed_analysis['software_components'] = {'summary': {}}
        fo_list = [self.root_fo_one, self.root_fo_two, self.root_fo_three]
        tmp_result_dict = {
            'software_in_common': {'all': set()},
            'exclusive_software': {fo.get_uid(): {} for fo in fo_list}
        }
        result = self.c_plugin._get_software_in_more_than_one_but_not_in_all(fo_list, tmp_result_dict)
        assert isinstance(result, dict), "result is not a dict"
        assert 'software a' in result[self.fw_one.uid], "foo not in result fw one"
        assert 'software a' in result[self.fw_two.uid], "foo not in result fw_two"
        assert 'software a' not in result[self.fw_three.uid], "foo in result fw_three"
        assert result['collapse']
