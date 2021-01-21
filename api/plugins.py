import logging
import pkg_resources
import importlib
import inspect

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

