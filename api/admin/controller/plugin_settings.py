import flask
from flask import jsonify, make_response

from . import SettingsController
from core.model import (
    ConfigurationSetting,
    get_one,
    Library,
)


class PluginSettingsController(SettingsController):
    def get_plugin_fields(self, library_short_name, plugin_name, plugin):
        body = {}
        header = {"Content-Type": "application/json"}

        try:
            library = self._get_library_from_short_name(library_short_name)
        except Exception as ex:
            body = {"error": "Library not found"}
            return make_response(jsonify(body), 404, header)

        if not hasattr(plugin, "FIELDS"):
            body = {}
            return make_response(jsonify(), 200, header)

        try:
            fields_from_db = self._get_saved_values(library, plugin_name)
        except Exception as ex:
            body = {"error": "Something went wrong, please try again"}
            return make_response(jsonify(body), 500, header)

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
        for field in body["fields"]:
            if field ["key"] == None:
                continue
            elif fields_from_db.get(field["key"]):
                field["value"] = fields_from_db[field["key"]]._value
            elif field["default"]:
                field["value"] = field["default"]

        return make_response(jsonify(body), 200, header)

    def save_plugin_fields_value(self, library_short_name, plugin_name, plugin, new_values):
        body = {}
        header = {"Content-Type": "application/json"}
    
        try:
            library = self._get_library_from_short_name(library_short_name)
        except Exception as ex:
            body = {"error": "Library not found"}
            return make_response(jsonify(body), 404, header)

        if not hasattr(plugin, "FIELDS"):
            body = {"error": "The plugin does not expect values"}
            return make_response(jsonify(body), 401, header)

        try:
            fields_from_db = self._get_saved_values(library, plugin_name)
        except Exception as ex:
            body = {"error": "Something went wrong, please try again"}
            return make_response(jsonify(body), 500, header)

        to_insert = [] # Expect list of {"id": <id>, "key": <key>, "value": <value>}
        to_update = [] # Expect list of tuples: (<ConfigurationSetting instance>, <new_value>)
        to_delete = [] # Expect list of ConfigurationSetting instaces

        for key, value in new_values.items():
            if key == None:
                continue
            elif not fields_from_db.get(key) and value is not None:
                to_insert.append({ "lib_id": library.id, "key": plugin_name+"."+key, "value": value})
            elif fields_from_db.get(key) and value is None:
                to_delete.append(fields_from_db.get(key))
            elif ( fields_from_db.get(key) and
                  fields_from_db[key]._value != value ):
                fields_from_db[key]._value = value
                to_update.append( (fields_from_db[key], value) )

        no_longer_exist_keys = set(fields_from_db.keys()) - set(new_values.keys())
        to_delete = to_delete + [fields_from_db[key] for key in no_longer_exist_keys]

        try:
            self._perform_db_operations(to_insert, to_update, to_delete)
        except Exception as ex:
            response_code = 500
            body = {"error": "Something went wrong while saving, please try again"}

        return make_response(jsonify(body), 200, header)

    def _perform_db_operations(self, to_insert, to_update, to_delete):
        if not to_insert and not to_update and not to_delete:
            return
        try:
            # Insert
            [self._db.add(ConfigurationSetting(library_id=entry["lib_id"],
                                               key=entry["key"],
                                               _value=entry["value"])
                ) for entry in to_insert
            ]
            # Update
            for entry in to_update:
                entry[0]._value = entry[1]

            # Delete
            [self._db.delete(entry) for entry in to_delete]
        except Exception as ex:
            raise

        try:
            self._db.commit()
        except Exception as ex:
            self._db.rollback()

    def _get_saved_values(self, library, plugin_name):
        response = self._db.query(ConfigurationSetting).filter(
            ConfigurationSetting.library_id == library.id,
            ConfigurationSetting.key.startswith(plugin_name)
        ).all()

        values = {}
        for entry in response:
            values[entry.key[len(plugin_name)+1:]] = entry
        return values

    def _get_library_from_short_name(self, library_short_name):
        library = get_one(
            self._db, Library, short_name=library_short_name,
        )
        if not library:
            raise Exception("Library not found")
        return library

