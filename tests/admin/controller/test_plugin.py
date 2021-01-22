from api.admin.controller.plugin_settings import PluginSettingsController
from test_controller import SettingsControllerTest
import unittest
from flask import Flask
from alchemy_mock.mocking import UnifiedAlchemyMagicMock
from nose.tools import assert_raises

from core.model import Library, ConfigurationSetting

# Varibles for test cases
DEFAULT_VALUE = "a simple value"
KEY_WITHOUT_DFAULT = "plugin-without-default"
VALUE_WITHOUT_DEFAULT = "first value"
KEY_WITH_DFAULT = "plugin-with-default"
VALUE_WITH_DEFAULT = "second value"

testApp = Flask(__name__)

class MockPluginWithDefault(object):
    FIELDS = [
        {
            "key": KEY_WITH_DFAULT,
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
            "key": KEY_WITHOUT_DFAULT,
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

            def _get_saved_values(self, *args, **kwargs):
                return {
                    KEY_WITHOUT_DFAULT: VALUE_WITHOUT_DEFAULT,
                    KEY_WITH_DFAULT: VALUE_WITH_DEFAULT,
                }

        with testApp.app_context():
            mocked_controller = MockPluginSettingsController()
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                            MockPluginWithoutDefault()).json
            assert "value" in result["fields"][0]
            assert result["fields"][0]["value"] == VALUE_WITHOUT_DEFAULT

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

        with testApp.app_context():
            mocked_controller = MockPluginSettingsController()
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                            MockPluginWithoutDefault()).json
            assert "value" not in result["fields"][0]

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

        with testApp.app_context():
            mocked_controller = MockPluginSettingsController()
            result = mocked_controller.get_plugin_fields("a-library", "a plugin",
                                                            MockPluginWithoutDefault()).json
            assert "error" in result


class TestPluginSettingsControllerGetSavedValues(unittest.TestCase):
    def test_plugin_empty_values(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, _db, *args, **kwargs):
                self._db = _db

            def _get_library_from_short_name(self, *arg, **kwargs):
                return Library(id=1, name="Lib", short_name="L1")
        
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_controller = MockPluginSettingsController(mocked_db)
        saved_values = mocked_controller._get_saved_values("any_library", "any_plugin")
        assert saved_values == {}

    def test_plugin_raise_exception(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, _db, *args, **kwargs):
                self._db = _db

            def _get_library_from_short_name(self, *arg, **kwargs):
                None
        
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_controller = MockPluginSettingsController(mocked_db)
        assert_raises(Exception, mocked_controller._get_saved_values, "any_library", "any_plugin")

    def test_plugin_find_values(self):
        class MockPluginSettingsController(PluginSettingsController):
            def __init__(self, _db, *args, **kwargs):
                self._db = _db

            def _get_library_from_short_name(self, *arg, **kwargs):
                return Library(id=1, name="Lib", short_name="L1")
        
        # Inside db.filter doesn't work with UnifiedAlchemyMagicMock
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_db.add(ConfigurationSetting(id=1, library_id=1, key="pname.key1", _value="value1"))
        mocked_db.add(ConfigurationSetting(id=2, library_id=1, key="pname.key2", _value="value2"))
        mocked_controller = MockPluginSettingsController(mocked_db)
        saved_values = mocked_controller._get_saved_values("any_library", "pname")
        assert "key1" in saved_values
        assert saved_values["key1"] == "value1"
        assert "key2" in saved_values
        assert saved_values["key2"] == "value2"


class TestPluginSettingsControllerLibraryFromShortName(unittest.TestCase):
    class MockPluginSettingsController(PluginSettingsController):
        def __init__(self, _db, *args, **kwargs):
            self._db = _db

    def test_plugin_find_library(self):
        _id = 1
        name = "Test Library Name"
        short_name = "T1"
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_db.add(Library(id=_id, name=name, short_name=short_name))
        mocked_controller = self.MockPluginSettingsController(mocked_db)
        library = mocked_controller._get_library_from_short_name("any_name")
        assert library.name == name 
        assert library.id == _id
        assert short_name == short_name

    def test_plugin_find_library(self):
        mocked_db = UnifiedAlchemyMagicMock()
        mocked_controller = self.MockPluginSettingsController(mocked_db)
        library = mocked_controller._get_library_from_short_name("any_name")
        assert_raises(Exception, mocked_controller, "any_name")

