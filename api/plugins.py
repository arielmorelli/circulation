import logging
import datetime
import pkg_resources
import importlib
import inspect
import errno
import os

from core.scripts import Script
from core.model import get_one, create, Timestamp, ConfigurationSetting

PLUGIN_PREFIX = "cm-plugin-"


def get_installed_plugins(pkg_resources=pkg_resources, importlib=importlib):
    plugins = {}
    packages = pkg_resources.working_set
    for package in packages:
        if package.key.startswith(PLUGIN_PREFIX):
            try:
                module = importlib.import_module(package.key.replace('-', "_"))
            except Exception as er:
                logging.error("Unable to import plugin module %s. Er: %s", package.key, er)
                continue
            if not hasattr(module, "__plugin__") or not inspect.isclass(module.__plugin__):
                logging.error("Plugin module %s incomplete, missing __plugin__ entry point",
                              package.key)
                continue

            plugins[package.key[len(PLUGIN_PREFIX):]] = module.__plugin__()

    return plugins

def pid_is_running(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    return True


class PluginController(Script):
    NAME = "Plugin Controller Pid"
    KEY_NAME = "plugin-controller-pid"
    SERVICE_PLUGIN_PREFIX = "plugin "
    def __init__(self, pid, target_script_name, force, _db=None, get_mocked_plugins=None):
        super(Script, self).__init__()
        self.target_script_name = target_script_name
        self.force = force
        self.pid = pid
        self.timestamp = Timestamp()
        if get_mocked_plugins:
            self.plugins = get_mocked_plugins()
        else:
            self.plugins = get_installed_plugins()
        if _db: # used for tests
            self._session = _db

    def run(self):
        if not self._should_run() and not self.force and not self.target_script_name:
            logging.info("Another PluginController is running, finishing this one.")
            return

        if self.target_script_name:
            plugin_instance = self.plugins.get(self.target_script_name)
            if plugin_instance:
                self._run_plugin(self.target_script_name, plugin_instance)
            else:
                logging.error("Cannot find script %s.", self.target_script_name)
                return
        else:
            for plugin_name, plugin_instance in self.plugins.items():
                try:
                    self._run_plugin(plugin_name, plugin_instance)
                except Exception as err:
                    logging.warning("Cannot run plugin %s. %s.", plugin_name, err)

    def _run_plugin(self, plugin_name, plugin_instance):
        logging.info("Start to run plugin %s", plugin_name)
        if not hasattr(plugin_instance, "FREQUENCY"):
                logging.warning("Unable to find FREQUENCY, use the script to run manually.")
        try:
            min_time_diff = int(plugin_instance.FREQUENCY)
        except:
            logging.warning("Unable to convert FREQUENCY to int")
            return

        if not self._plugin_should_run(plugin_name, min_time_diff) and not self.force :
            logging.info("It is not time to run! You can force it using --force argument.")
            return

        start = datetime.datetime.utcnow()
        try:
            plugin_instance.run_scripts(plugin_name)
        except Exception as ex:
            logging.error("Erro while running script: %s. %s.", plugin_name, ex)
        finish = datetime.datetime.utcnow()
        self._update_plugin_last_run(plugin_name, start, finish)

    def _update_plugin_last_run(self, plugin_name, start, finish):
        srv_name = self._get_service_name(plugin_name)
        timestamp = get_one(self._db, Timestamp, service=srv_name)
        if not timestamp:
            create(self._db, Timestamp, service=srv_name, start=start, finish=finish)
        else:
            timestamp.start = start
            timestamp.finish = finish
        try:
            self._db.commit()
        except Exception as er:
            logging.error("Error while updating timestamp. Er: %s", er)
            self._db.rollback()

        logging.error("Plugin %s run in %d seconds", plugin_name, (finish-start).total_seconds())

    def _plugin_should_run(self, plugin_name, min_diff_in_hours):
        srv_name = self._get_service_name(plugin_name)
        finished_timestamp = get_one(self._db, Timestamp, service=srv_name)
        if finished_timestamp and finished_timestamp.finish:
            finished_timestamp = finished_timestamp.finish
        else:
            return True
        expires = finished_timestamp + datetime.timedelta(hours=min_diff_in_hours)
        now = datetime.datetime.utcnow()
        return now > expires

    def _get_service_name(self, plugin_name):
        return self.SERVICE_PLUGIN_PREFIX + plugin_name

    def _should_run(self):
        response = get_one(self._db, ConfigurationSetting,
            ConfigurationSetting.key==self.KEY_NAME
        )
        if not response:
            create(
                self._db, ConfigurationSetting, key=self.KEY_NAME, value=os.getpid()
            )
            return True

        if pid_is_running(response._value):
            return False

        response._value = self.pid
        try:
            self._db.commit()
        except Exception as ex:
            logging.error("Error while saving current PID", ex)
            self._db.rollback()
            return False
        return True

