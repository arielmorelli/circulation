from api.plugins import (
    get_installed_plugins,
    PLUGIN_PREFIX,
    pid_is_running,
    PluginController,
)
from core.model import ConfigurationSetting, Timestamp
from core.testing import DatabaseTest, create
from nose.tools import assert_raises
from mock import MagicMock

import os
import datetime
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


class TestGetInstalledPlugins(unittest.TestCase):
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


class TestPidIsRunning(unittest.TestCase):
    def test_pid_empty(self):
        assert not pid_is_running(None)

    def test_pid_non_valid(self):
        assert_raises(Exception, pid_is_running, "abc")

    def test_pid_of_current_test(self):
        current_pid = os.getpid()
        assert pid_is_running(current_pid)

    def test_pid_of_exited_child(self):
        current = os.fork()
        if current == 0:
            # Child process
            os._exit(1)
        else:
            child_process_info = os.wait() # Wait child exit
            child_pid = child_process_info[0] # child pid is the first info
            assert not pid_is_running(child_pid)


# class PluginControllerTest(DatabaseTest, unittest.TestCase):
class TestPluginController(DatabaseTest):
    class MockedPlugin(object):
        def run_scripts(*args, **kwargs):
            pass

    def test_shoud_run_without_config_in_db(self):
        pid = os.getpid()
        controller = PluginController(pid, None, False, _db=self._db)

        assert controller._should_run()

    def test_shoud_run_true_pid_of_exited_child(self):
        pid = os.getpid()
        controller = PluginController(pid, None, False, _db=self._db)

        current = os.fork()
        if current == 0:
            # Child process
            os._exit(1)
        else:
            child_process_info = os.wait() # Wait child exit
            child_pid = child_process_info[0] # child pid is the first info
            create(
                self._db, ConfigurationSetting, key=controller.KEY_NAME, _value=child_pid
            )
            assert controller._should_run()

    def test_shoud_run_true_pid_of_current_process(self):
        pid = os.getpid()
        controller = PluginController(pid, None, False, _db=self._db)

        create(
            self._db, ConfigurationSetting, key=controller.KEY_NAME, _value=pid
        )

        assert not controller._should_run()

    def test_plugin_should_run_without_timestap(self):
        pid = os.getpid()
        p_name = "a-plugin"
        controller = PluginController(pid, p_name, False, _db=self._db)

        assert controller._plugin_should_run(p_name, 1)

    def test_plugin_should_run_with_timestap_lower_than_threshold(self):
        pid = os.getpid()
        p_name = "a-plugin"
        controller = PluginController(pid, p_name, False, _db=self._db)

        now = datetime.datetime.utcnow()
        create(
            self._db, Timestamp, service=controller._get_service_name(p_name),
            service_type=Timestamp.SCRIPT_TYPE, finish=now
        )

        assert not controller._plugin_should_run(p_name, 1)

    def test_plugin_should_run_without_timestap_bigger_than_threshold(self):
        pid = os.getpid()
        p_name = "a-plugin"
        controller = PluginController(pid, p_name, False, _db=self._db)

        now = datetime.datetime.utcnow()
        day_in_past = now -  datetime.timedelta(days=2)
        create(
            self._db, Timestamp, service=controller._get_service_name(p_name),
            service_type=Timestamp.SCRIPT_TYPE, finish=day_in_past
        )

        assert controller._plugin_should_run(p_name, 1)

    def test_run_plugin_with_instance(self):
        pid = os.getpid()
        p_name = "a-plugin"
        def plugins():
            return {p_name: self.MockedPlugin()}

        controller = PluginController(pid, p_name, True, _db=self._db, get_mocked_plugins=plugins)
        controller._run_plugin = MagicMock()

        controller.run()
        assert controller._run_plugin.call_count == 1
        plugin_arg_name, plugin_arg_instance = controller._run_plugin.call_args[0]
        assert plugin_arg_name == p_name

    def test_run_plugin_with_instance_plugin_not_exist(self):
        pid = os.getpid()
        p_name = "a-plugin"
        def plugins():
            return {"any-other-plugin": self.MockedPlugin()}

        controller = PluginController(pid, p_name, True, _db=self._db, get_mocked_plugins=plugins)
        controller._run_plugin = MagicMock()

        controller.run()
        assert controller._run_plugin.call_count == 0

    def test_run_plugin_without_instance(self):
        pid = os.getpid()
        def plugins():
            return {
                "a-plugin": self.MockedPlugin(),
                "other-plugin": self.MockedPlugin(),
                "some-other-plugin": self.MockedPlugin(),
            }

        controller = PluginController(pid, None, True, _db=self._db, get_mocked_plugins=plugins)
        controller._run_plugin = MagicMock()

        controller.run()
        assert controller._run_plugin.call_count == 3

