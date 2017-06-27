#!/usr/bin/env python
"""Move per-library settings from the Configuration file
into the database as ConfigurationSettings.
"""
import os
import sys
import json
import logging
from nose.tools import set_trace

bin_dir = os.path.split(__file__)[0]
package_dir = os.path.join(bin_dir, "..")
sys.path.append(os.path.abspath(package_dir))

from core.model import (
    ConfigurationSetting,
    ExternalIntegration,
    get_one_or_create,
    production_session,
    Library,
    create,
)

from api.config import Configuration

_db = production_session()
try:
    Configuration.load()
    integrations = []

    # If the secret key is set, make it a sitewide setting.
    secret_key = Configuration.get('secret_key')
    if secret_key:
        secret_setting = ConfigurationSetting.sitewide(
            _db, Configuration.SECRET_KEY
        )
        secret_setting.value = secret_key
    
    libraries = _db.query(Library).all()
    
    # Copy default email address into each library.
    key = 'default_notification_email_address'
    value = Configuration.get(key)
    if value:
        for library in libraries:
            ConfigurationSetting.for_library(key, library).value = value

    # Copy maximum fines into each library.
    for key in ['max_outstanding_fines', 'minimum_featured_quality',
                'featured_lane_size']:
        value = Configuration.policy(key)
        if value:
            for library in libraries:
                ConfigurationSetting.for_library(key, library).value = value

    # Convert the string hold_policy into the boolean allow_holds.
    hold_policy = Configuration.policy('holds')
    if hold_policy == 'hide':
        for library in libraries:
            library.setting("allow_holds").value = "False"

    # Copy facet configuration
    facet_policy = Configuration.policy("facets", default={})
    enabled = facet_policy.get("enabled", {})
    default = facet_policy.get("default", {})
    for library in libraries:
        for k, v in enabled.items():
            library.enabled_facets_setting(k).value = json.dumps(v)
        for k, v in default.items():
            library.default_facet_setting(k).value = v
            
    # Copy external type regular expression into each collection for each
    # library.
    key = 'external_type_regular_expression'
    value = Configuration.policy(key)
    if value:
        for library in libraries:
            for collection in library.collections:
                integration = collection.external_integration
                if not integration:
                    continue
                ConfigurationSetting.for_library_and_externalintegration(
                    _db, key, library, integration).value = value
                
finally:
    _db.commit()
    _db.close()
