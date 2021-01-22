from api.admin.controller.plugin_settings import PluginSettingsController
from test_controller import SettingsControllerTest
import unittest
from mock import MagicMock
from flask import Flask
from alchemy_mock.mocking import UnifiedAlchemyMagicMock
from nose.tools import assert_raises

from core.model import Library, ConfigurationSetting

# Varibles for test cases
DEFAULT_VALUE = "a simple value"
KEY_WITHOUT_DEFAULT = "plugin-without-default"
VALUE_WITHOUT_DEFAULT = "first value"
KEY_WITH_DEFAULT = "plugin-with-default"
VALUE_WITH_DEFAULT = "second value"
LIB_ID = 1

testApp = Flask(__name__)

class MockPluginWithDefault(object):
    FIELDS = [
        {
            "key": KEY_WITH_DEFAULT,
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
            "key": KEY_WITHOUT_DEFAULT,
            "label": "label-test",
            "description": "a example description",
            "type": "input",
            "required": True,
        }
    ]


class TestPluginSettingsControllerGetValues(unittest.TestCase):
    def test_plugin_with_saved_values(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, *args, **kwargs):
                pass

            def _get_library_from_short_name(self, library_short_name):
                return Library(id=LIB_ID, short_name="T1")

            def _get_saved_values(self, *args, **kwargs):
                return {
                    KEY_WITH_DEFAULT: ConfigurationSetting(id=1,
                                                             library_id=LIB_ID,
                                                             key=KEY_WITH_DEFAULT,
                                                             _value=VALUE_WITH_DEFAULT
                                                             ),
                    KEY_WITHOUT_DEFAULT: ConfigurationSetting(id=2,
                                                           library_id=LIB_ID,
                                                           key=KEY_WITHOUT_DEFAULT,
                                                           _value=VALUE_WITHOUT_DEFAULT
                                                           ),
                }

        mocked_controller = MockPluginSettingsController()
        with testApp.app_context():
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                         MockPluginWithoutDefault()).json
        assert "value" in result["fields"][0]
        assert result["fields"][0]["value"] == VALUE_WITHOUT_DEFAULT

        with testApp.app_context():
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                         MockPluginWithDefault()).json
        assert "value" in result["fields"][0]
        assert result["fields"][0]["value"] == VALUE_WITH_DEFAULT

    def test_plugin_without_saved_values(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, *args, **kwargs):
                pass

            def _get_saved_values(*args, **kwargs):
                return {}

        mocked_controller = MockPluginSettingsController()
        with testApp.app_context():
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                         MockPluginWithoutDefault()).json
        assert "value" not in result["fields"][0]

        with testApp.app_context():
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                            MockPluginWithDefault()).json
        assert "value" in result["fields"][0]
        assert result["fields"][0]["value"] == DEFAULT_VALUE

    def test_plugin_without_saved_values(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, *args, **kwargs):
                pass

            def _get_saved_values(*args, **kwargs):
                raise Exception("Library not found")

        mocked_controller = MockPluginSettingsController()
        with testApp.app_context():
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                            MockPluginWithoutDefault()).json
        assert "error" in result


class TestPluginSettingsControllerSaveValues(unittest.TestCase):
    class MockPluginSettingsController(PluginSettingsController):
        def __init__(self, get_library=None, get_values=None, save_to_db=None, *args, **kwargs):
            self.get_library = get_library
            self.get_saved_values = get_values
            self._perform_db_operations=save_to_db
            
        def _get_saved_values(self, *args, **kwargs):
            return self.get_saved_values()

        def _get_library_from_short_name(self, *args, **kwargs):
            return self.get_library()

    def test_library_not_found(self):
        def get_library(*args, **kwargs):
            raise Exception("Library not found")

        mocked_controller = self.MockPluginSettingsController(get_library=get_library)
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                {}).json
        assert "error" in result

    def test_plugin_without_fields(self):
        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        mocked_controller = self.MockPluginSettingsController(get_library=get_library)
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                object(),
                                                                {}).json
        assert "error" in result

    def test_cannot_get_values_from_db(self):
        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            raise Exception("Unable to load data")

        mocked_controller = self.MockPluginSettingsController(get_library=get_library)
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                {}).json
        assert "error" in result

    def test_insert_value_data_empty(self):
        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            return {}
        
        key = "key-to-test"
        val = "value to test"
        data = {key: val}
        mocked_controller = self.MockPluginSettingsController(get_library=get_library,
                                                              get_values=get_values,
                                                              save_to_db=MagicMock()
                                                             )
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                data).json
        assert "error" not in result
        mocked_controller._perform_db_operations.assert_called_with([{"id": LIB_ID,
                                                                      "key": key,
                                                                      "value": val}],
                                                                    [],
                                                                    [],
                                                                    )

    def test_insert_value_with_data_existing(self):
        new_key = "key-to-test"
        new_val = "value to test"
        key_to_keep = "key-to-keep"
        val_to_keep = "val to keep"
        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            return {key_to_keep: ConfigurationSetting(_value=val_to_keep)}
        
        data = {new_key: new_val, key_to_keep: val_to_keep}
        mocked_controller = self.MockPluginSettingsController(get_library=get_library,
                                                              get_values=get_values,
                                                              save_to_db=MagicMock()
                                                             )
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                data).json
        assert "error" not in result
        mocked_controller._perform_db_operations.assert_called_with(
                                                                    [{"id": LIB_ID,
                                                                      "key": new_key,
                                                                      "value": new_val}],
                                                                    [],
                                                                    [],
                                                                    )

    def test_update_value_with_non_other_fields(self):
        config_id = 1
        key = "key-to-test"
        config_instace = ConfigurationSetting(id=config_id, _value="old value")
        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            return {key: config_instace}
        
        new_val = "new val"
        data = {key: new_val}
        mocked_controller = self.MockPluginSettingsController(get_library=get_library,
                                                              get_values=get_values,
                                                              save_to_db=MagicMock()
                                                             )
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                data).json
        assert "error" not in result
        mocked_controller._perform_db_operations.assert_called_with(
                                                                    [],
                                                                    [(config_instace, new_val)],
                                                                    [],
                                                                    )

    def test_update_value_with_other_fields(self):
        config_id = 1
        key = "key-to-test"
        config_instace = ConfigurationSetting(id=config_id, _value="old valeu")
        fixed_key = "fixed-key"
        fixed_value = "fixed-value"

        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            return {key: config_instace,
                    fixed_key: ConfigurationSetting(id=config_id+1, _value=fixed_value)
                   }
        
        new_val = "new val"
        data = {key: new_val,
                fixed_key: fixed_value}
        mocked_controller = self.MockPluginSettingsController(get_library=get_library,
                                                              get_values=get_values,
                                                              save_to_db=MagicMock(),
                                                             )
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                data).json
        assert "error" not in result
        mocked_controller._perform_db_operations.assert_called_with(
                                                                    [],
                                                                    [(config_instace, new_val)],
                                                                    [],
                                                                    )

    def test_delete_value(self):
        key = "key-to-test"
        val = ConfigurationSetting(id=1, _value="a value")
        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            return {key: val}
        
        data = {key: None}
        mocked_controller = self.MockPluginSettingsController(get_library=get_library,
                                                              get_values=get_values,
                                                              save_to_db=MagicMock(),
                                                             )
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                data).json
        assert "error" not in result
        mocked_controller._perform_db_operations.assert_called_with([], [], [val])

    def test_delete_value_exist_in_db_but_dont_exist_in_request(self):
        key = "key-to-test"
        val = ConfigurationSetting(id=1, _value="a value")
        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            return {key: val}
        
        data = {}
        mocked_controller = self.MockPluginSettingsController(get_library=get_library,
                                                              get_values=get_values,
                                                              save_to_db=MagicMock(),
                                                             )
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                data).json
        assert "error" not in result
        mocked_controller._perform_db_operations.assert_called_with([], [], [val])

    def test_insert_one_update_one_delete_one_and_keep_one(self):
        id_to_update = 1
        key_to_insert = "key-to-insert"
        val_to_insert = "value to insert"
        key_to_update = "key-to-update"
        val_to_update_old = ConfigurationSetting(id=id_to_update, _value="old value to update")
        val_to_update_new = "new value"
        key_to_delete = "key-to-delete"
        val_to_delete = ConfigurationSetting(id=2, _value="value to delete")
        key_to_keep = "key-to-keep"
        val_to_keep = ConfigurationSetting(id=3, _value="val to keep")

        def get_library(*args, **kwargs):
            return Library(id=LIB_ID, short_name="T1")

        def get_values(*args, **kwargs):
            return {key_to_update: val_to_update_old,
                    key_to_delete: val_to_delete,
                    key_to_keep: val_to_keep
                   }
           
        data = {key_to_insert: val_to_insert,
                key_to_update: val_to_update_new,
                key_to_keep: val_to_keep._value}
        mocked_controller = self.MockPluginSettingsController(get_library=get_library,
                                                              get_values=get_values,
                                                              save_to_db=MagicMock(),
                                                             )
        with testApp.app_context():
            result = mocked_controller.save_plugin_fields_value("library",
                                                                "plugin",
                                                                MockPluginWithDefault(),
                                                                data).json
        assert "error" not in result
        mocked_controller._perform_db_operations.assert_called_with( [{"id": LIB_ID,
                                                                       "key": key_to_insert,
                                                                       "value": val_to_insert}],
                                                                     [(val_to_update_old, val_to_update_new)],
                                                                     [val_to_delete]
                                                                   )

class TestPluginSettingsControllerGetSavedValues(unittest.TestCase):
    def test_plugin_empty_values(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, _db, *args, **kwargs):
                self._db = _db

        
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_controller = MockPluginSettingsController(mocked_db)
        library = Library(id=LIB_ID, name="Lib", short_name="L1")
        saved_values = mocked_controller._get_saved_values(library, "any_plugin")
        assert saved_values == {}

    def test_plugin_find_values(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, _db, *args, **kwargs):
                self._db = _db

            def _get_library_from_short_name(self, *arg, **kwargs):
                return Library(id=LIB_ID, name="Lib", short_name="L1")
        
        # Inside db.filter doesn't work with UnifiedAlchemyMagicMock
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_db.add(ConfigurationSetting(id=1, library_id=1, key="pname.key1", _value="value1"))
        mocked_db.add(ConfigurationSetting(id=2, library_id=1, key="pname.key2", _value="value2"))
        mocked_controller = MockPluginSettingsController(mocked_db)
        library = Library(id=LIB_ID, name="Lib", short_name="L1")
        saved_values = mocked_controller._get_saved_values(library, "pname")
        assert "key1" in saved_values
        assert saved_values["key1"]._value == "value1"
        assert "key2" in saved_values
        assert saved_values["key2"]._value == "value2"


class TestPluginSettingsControllerLibraryFromShortName(unittest.TestCase):
    class MockPluginSettingsController(PluginSettingsController):
        def __init__(self, _db, *args, **kwargs):
            self._db = _db

    def test_plugin_find_library(self):
        name = "Test Library Name"
        short_name = "T1"
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_db.add(Library(id=LIB_ID, name=name, short_name=short_name))
        mocked_controller = self.MockPluginSettingsController(mocked_db)
        library = mocked_controller._get_library_from_short_name("any_name")
        assert library.name == name 
        assert library.id == LIB_ID
        assert short_name == short_name

    def test_plugin_find_library(self):
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_controller = self.MockPluginSettingsController(mocked_db)
        assert_raises(Exception, mocked_controller._get_library_from_short_name, "any_name")

