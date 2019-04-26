from compare.PluginBase import CompareBasePlugin as ComparePlugin
from test.unit.compare.compare_plugin_test_class import TestComparePlugin


class TestComparePluginBase(TestComparePlugin):

    # This name must be changed according to the name of plug-in to test
    PLUGIN_NAME = 'base'

    def setup_plugin(self):
        """
        This function must be overwritten by the test instance.
        In most cases it is sufficient to copy this function.
        """
        return ComparePlugin(self, config=self.config)

    def test_compare_missing_dep(self):
        self.c_plugin.DEPENDENCIES = ['test_ana']
        self.root_fo_one.processed_analysis['test_ana'] = {}
        expected_result = {'Compare Skipped': {'all': 'Required analysis not present: [\'test_ana\']'}}
        assert self.c_plugin.compare([self.root_fo_one, self.root_fo_two]) == expected_result, 'missing dep result not correct'

    def test_compare(self):
        assert self.c_plugin.compare([self.fw_one, self.fw_two]) == {'dummy': {'all': 'dummy-content', 'collapse': False}}, 'result not correct'
