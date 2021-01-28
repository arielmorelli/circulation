from api.controller import CirculationManager
from api.admin.controller.plugin_settings import PluginSettingsController
from test_controller import SettingsControllerTest
import unittest
from mock import MagicMock
from flask import Flask
from nose.tools import assert_raises

from core.model.plugin_configuration import PluginConfiguration
from core.model.library import Library
from core.model import create
from core.tests import DatabaseTest

# Varibles for test cases
DEFAULT_VALUE = "a simple value"
VALUE_WITHOUT_DEFAULT = "first value"
PLUGIN_KEY= "plugin-key"
VALUE_WITH_DEFAULT = "second value"
LIB_ID = 1

testApp = Flask(__name__)

class MockPluginWithDefault(object):
    FIELDS = [
        {
            "key": PLUGIN_KEY,
            "label": "with-default",
            "description": "a example with default",
            "type": "input",
            "required": True,
            "default": DEFAULT_VALUE,
        }
    ]


class MockPluginWithoutDefault(object):
    FIELDS = [
        {
            "key": PLUGIN_KEY,
            "label": "label-test",
            "description": "a example description",
            "type": "input",
            "required": True,
        }
    ]

class TestPluginSettingsControllerGetValues(DatabaseTest):
    def test_plugin_library_not_found(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)
        with testApp.app_context():
            result = controller.get_plugin_fields("a-library", "a plugin", MockPluginWithDefault())
            result = result.json

        assert "error" in result

    def test_plugin_without_saved_values(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)

        lib_name = "a-library"
        plugin_name = "a-plugin"
        inserted_library, ignore = create(
            self._db, Library, id=LIB_ID, name="a name", short_name=lib_name
        )

        # Without default
        with testApp.app_context():
            result = controller.get_plugin_fields(lib_name, plugin_name, MockPluginWithoutDefault())
            result = result.json

        assert "fields" in result
        assert "value" not in result["fields"][0]

        # With default
        with testApp.app_context():
            result = controller.get_plugin_fields(lib_name, plugin_name, MockPluginWithDefault())
            result = result.json

        assert "fields" in result
        assert "value" in result["fields"][0]
        assert result["fields"][0]["value"] == DEFAULT_VALUE

    def test_plugin_without_saved_values(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)

        lib_name = "a-library"
        plugin_name = "a-plugin"
        test_value =  "a-value"
        
        library, _ = create(
            self._db, Library, id=LIB_ID, name="a name", short_name=lib_name
        )
        create(
            self._db, PluginConfiguration, id=2, library_id=library.id, key=plugin_name+"."+PLUGIN_KEY,
            _value=test_value
        )

        # Without default
        with testApp.app_context():
            result = controller.get_plugin_fields(lib_name, plugin_name, MockPluginWithoutDefault())
            result = result.json

        assert "fields" in result
        assert "value" in result["fields"][0]
        assert result["fields"][0]["value"] == test_value

        # With default
        with testApp.app_context():
            result = controller.get_plugin_fields(lib_name, plugin_name, MockPluginWithDefault())
            result = result.json

        assert "fields" in result
        assert "value" in result["fields"][0]
        assert result["fields"][0]["value"] == test_value


class TestPluginSettingsControllerSaveValues(DatabaseTest):
    def test_plugin_library_not_found(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)
        with testApp.app_context():
            result = controller.save_plugin_fields_value("a-lib", "a plugin", MockPluginWithDefault(),
                                                         {})
            result = result.json

        assert "error" in result

    def test_plugin_without_fields(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)
        with testApp.app_context():
            result = controller.save_plugin_fields_value("a-lib", "a plugin", object(),
                                                         {})
            result = result.json

        assert "error" in result

    def test_insert_value_with_empty_data(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)

        lib_name = "a-library"
        plugin_name = "a-plugin"
        test_value =  "a-value"
        
        library, _ = create(
            self._db, Library, id=LIB_ID, name="a name", short_name=lib_name
        )

        with testApp.app_context():
            result = controller.save_plugin_fields_value(lib_name, plugin_name,
                                                         MockPluginWithoutDefault(), {})
            result = result.json

        assert "error" not in result

    def test_insert_value(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)

        lib_name = "a-library"
        plugin_name = "a-plugin"
        test_value =  "a-value"
        
        library, _ = create(
            self._db, Library, id=LIB_ID, name="a name", short_name=lib_name
        )
        create(
            self._db, PluginConfiguration, id=2, library_id=library.id, key=plugin_name+"."+PLUGIN_KEY,
            _value=test_value
        )

        with testApp.app_context():
            result = controller.save_plugin_fields_value(lib_name, plugin_name,
                                                         MockPluginWithoutDefault(), {"a": "b"})
            result = result.json

        assert "error" not in result

    def test_update_value(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)

        lib_name = "a-library"
        plugin_name = "a-plugin"
        test_value =  "a-value"
        
        library, _ = create(
            self._db, Library, id=LIB_ID, name="a name", short_name=lib_name
        )
        create(
            self._db, PluginConfiguration, id=2, library_id=library.id, key=plugin_name+"."+PLUGIN_KEY,
            _value=test_value+" old"
        )

        with testApp.app_context():
            result = controller.save_plugin_fields_value(lib_name, plugin_name,
                                                         MockPluginWithoutDefault(),
                                                         {PLUGIN_KEY: test_value})
            result = result.json

        assert "error" not in result

    def test_delete_value(self):
        manager = CirculationManager(self._db, testing=True)
        controller = PluginSettingsController(manager)

        lib_name = "a-library"
        plugin_name = "a-plugin"
        test_value =  "a-value"
        
        library, _ = create(
            self._db, Library, id=LIB_ID, name="a name", short_name=lib_name
        )
        create(
            self._db, PluginConfiguration, id=2, library_id=library.id, key=plugin_name+"."+PLUGIN_KEY,
            _value=test_value+" old"
        )

        with testApp.app_context():
            result = controller.save_plugin_fields_value(lib_name, plugin_name,
                                                         MockPluginWithoutDefault(),
                                                         {})
            result = result.json

        assert "error" not in result

