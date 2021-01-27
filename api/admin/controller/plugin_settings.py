import flask
from flask import jsonify, make_response

from . import SettingsController
from core.model import get_one
from core.model.plugin import Plugin


class PluginSettingsController(SettingsController):
    def get_plugin_fields(self, library_short_name, plugin_name, plugin):
        body = {}
        header = {"Content-Type": "application/json"}

        if not hasattr(plugin, "FIELDS"):
            body = {}
            return make_response(jsonify(), 200, header)

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

        try:
            plugin_saved_values = Plugin().get_saved_values(self._db, library_short_name, plugin_name)
        except:
            body = {"error": "Something went wrong, please try again."}
            return make_response(jsonify(body), 500, header)

        for field in body["fields"]:
            if field["key"] == None:
                continue
            elif plugin_saved_values.get(field["key"]):
                field["value"] = plugin_saved_values[field["key"]]._value
            elif field["default"]:
                field["value"] = field["default"]

        return make_response(jsonify(body), 200, header)

    def save_plugin_fields_value(self, library_short_name, plugin_name, plugin, new_values):
        body = {}
        header = {"Content-Type": "application/json"}
    
        if not hasattr(plugin, "FIELDS"):
            body = {"error": "The plugin does not expect values"}
            return make_response(jsonify(body), 401, header)

        try:
            plugin_saved_values = Plugin().save_values(self._db, library_short_name, plugin_name,
                                                            new_values)
        except Exception as ex:
            body = {"error": "Something went wrong, please try again"}
            return make_response(jsonify(body), 500, header)

        return make_response(jsonify(body), 200, header)

