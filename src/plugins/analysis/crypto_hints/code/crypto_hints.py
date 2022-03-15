from analysis.YaraPluginBase import YaraBasePlugin


class AnalysisPlugin(YaraBasePlugin):

    NAME = 'crypto_hints'
    DESCRIPTION = 'find indicators of specific crypto algorithms'
    DEPENDENCIES = []
    VERSION = '0.1'
    FILE = __file__

    def __init__(self, plugin_administrator, recursive=True):
        super().__init__(plugin_administrator, recursive=recursive, plugin_path=__file__)
