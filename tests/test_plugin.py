from api.plugins import get_installed_plugins, PLUGIN_PREFIX

import unittest


class MockPkgResources(object):
    def __init__(self, working_set):
        self.working_set = working_set


class MockPackage(object):
    class __plugin__:
        pass

    def __init__(self, key):
        self.key = key


class MockPackagePluginNotBeingAClass(object):
    __plugin__ = object()

    def __init__(self, key):
        self.key = key


class MockPackageWitoutPlugin(object):
    def __init__(self, key):
        self.key = key


class MockImportLib(object):
    def __init__(self, _return):
        self._return = _return

    def import_module(self, *args, **kwargs):
        return self._return


class PluginTest(unittest.TestCase):
    def test_non_installed_plugins(self):
        pkgs = []
        plugins = get_installed_plugins(pkg_resources=MockPkgResources(pkgs))
        assert plugins == {}

    def test_find_installed_plugins_valid(self):
        plugin_name = "is-a-test"
        pkgs = [MockPackage(PLUGIN_PREFIX+plugin_name)]
        mocked_import_lib = MockImportLib(pkgs[0])
        plugins = get_installed_plugins(pkg_resources=MockPkgResources(pkgs),
                                        importlib=mocked_import_lib)
        assert plugin_name in plugins

    def test_find_installed_plugins_without_prefix(self):
        pkgs = [MockPackage("non"+PLUGIN_PREFIX)]
        plugins = get_installed_plugins(pkg_resources=MockPkgResources(pkgs))
        assert plugins == {}

    def test_find_installed_plugins_with_prefix_without_plugin_declaration(self):
        pkgs = [MockPackageWitoutPlugin(PLUGIN_PREFIX+"is-a-test")]
        mocked_import_lib = MockImportLib(pkgs[0])
        plugins = get_installed_plugins(pkg_resources=MockPkgResources(pkgs),
                                        importlib=mocked_import_lib)
        assert plugins == {}

    def test_find_installed_plugins_with_prefix_without_plugin_being_a_class(self):
        pkgs = [MockPackagePluginNotBeingAClass(PLUGIN_PREFIX+"is-a-test")]
        mocked_import_lib = MockImportLib(pkgs[0])
        plugins = get_installed_plugins(pkg_resources=MockPkgResources(pkgs),
                                        importlib=mocked_import_lib)
        assert plugins == {}

