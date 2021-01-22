import flask
from flask import jsonify, make_response

from . import SettingsController
from core.model import (
    ConfigurationSetting,
    get_one,
    Library,
)


class PluginSettingsController(SettingsController):
    def process_request(self, library_short_name, plugin_name, plugin):
        if flask.request.method == 'GET':
            return self.get_plugin_fields(plugin)
        else:
            # return self.process_post()
            return "not implemented yet"

    def get_plugin_fields(self, library_short_name, plugin_name, plugin):
        error = False
        body = {}
        header = {"Content-Type": "application/json"}
    
        if hasattr(plugin, "FIELDS"):
            try:
                fields_value = self._get_saved_values(library_short_name, plugin_name)
            except Exception as ex:
                error = True
                response_code = 404
                body = {"error": "Library not found"}

            if not error:
                response_code = 200
                body = {
                    "fields": [{
                        "key": field.get("key"),
                        "label": field.get("label") ,
                        "description": field.get("description"),
                        "type": field.get("type"),
                        "required": field.get("required", False),
                        "default": field.get("default"),
                        "format": field.get("format"),
                        "options": field.get("options"),
                        "instructions": field.get("instructions"),
                        "capitalize": field.get("capitalize"),
                        "allowed": field.get("allowed"),
                    } for field in plugin.FIELDS]
                }
                for entry in body["fields"]:
                    if entry["key"] != None and (fields_value.get(entry["key"]) or entry["default"]):
                       entry["value"] = fields_value.get(entry["key"], entry["default"])

        return make_response(jsonify(body), response_code, header)

    def _get_saved_values(self, library_short_name, plugin_name):
        library = self._get_library_from_short_name(library_short_name)
        if not library:
            raise Exception("Library not found")
        response = self._db.query(ConfigurationSetting).filter(
            ConfigurationSetting.library_id == library.id,
            ConfigurationSetting.key.startswith(plugin_name)
        ).all()

        return {r.key[len(plugin_name)+1:]: r._value for r in response}

    def _get_library_from_short_name(self, library_short_name):
        return get_one(
            self._db, Library, short_name=library_short_name,
        )
