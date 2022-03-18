# This pytest feature is kinda undocumented.
# All files named conftest.py are executed before test execution.
# So conftest.py is a good place to define fixtures shared by many tests
# See also [1].
# For our use we can not have this file in the test/ directory since some tests
# are not inside the test/ directory.
#
# [1]https://stackoverflow.com/questions/34466027/in-pytest-what-is-the-use-of-conftest-py-files

import pytest

import test.common_helper


@pytest.fixture
def cfg_tuple(request):
    """Returns a `config.Config` and a `configparser.ConfigParser` with testing defaults.
    Defaults can be overwritting with the `cfg_defaults` pytest mark.
    """
    cfg_defaults_marker = request.node.get_closest_marker('cfg_defaults')
    cfg_defaults = cfg_defaults_marker.args[0] if cfg_defaults_marker else None

    cfg, configparser_cfg = test.common_helper.get_test_config(cfg_defaults)
    yield cfg, configparser_cfg

    test.common_helper.test_config_cleanup(cfg)


@pytest.fixture(autouse=True)
def patch_cfg(cfg_tuple):
    """This fixture will replace `config.cfg` and `config.configparser_cfg` with the default test config.
    See `cfg_tuple` on how to change defaults.
    """
    cfg, configparser_cfg = cfg_tuple
    mpatch = pytest.MonkeyPatch()
    mpatch.setattr('config.cfg', cfg)
    mpatch.setattr('config.configparser_cfg', configparser_cfg)
    yield

    mpatch.undo()
