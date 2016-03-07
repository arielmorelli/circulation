from nose.tools import set_trace
import logging
import sys
import os
import base64

import flask
from flask import (
    Response,
    redirect,
)

from core.model import (
    get_one,
    get_one_or_create,
    Admin,
)
from core.util.problem_detail import ProblemDetail
from api.problem_details import *

from config import (
    Configuration, 
    CannotLoadConfiguration
)

from oauth import GoogleAuthService

from api.controller import CirculationManagerController


def setup_admin_controllers(manager):
    """Set up all the controllers that will be used by the admin parts of the web app."""
    if not manager.testing:
        try:
            manager.config = Configuration.load()
        except CannotLoadConfiguration, e:
            self.log.error("Could not load configuration file: %s" % e)
            sys.exit()

    manager.admin_work_controller = WorkController(manager)
    manager.admin_signin_controller = SigninController(manager)


class AdminController(object):

    def __init__(self, manager):
        self.manager = manager
        self._db = self.manager._db
        self.url_for = self.manager.url_for
        self.cdn_url_for = self.manager.cdn_url_for

    @property
    def google(self):
        return GoogleAuthService.from_environment(
            self.url_for('google_auth_callback'), test_mode=self.manager.testing
        )

    def authenticated_admin_from_request(self):
        """Returns an authenticated admin or begins the Google OAuth flow"""

        access_token = flask.session.get("admin_access_token")
        if access_token:
            admin = get_one(self._db, Admin, access_token=access_token)
            if admin and self.google.active_credentials(admin):
                return admin
        return INVALID_ADMIN_CREDENTIALS

    def authenticated_admin(self, admin_details):
        """Creates or updates an admin with the given details"""

        admin, ignore = get_one_or_create(
            self._db, Admin, email=admin_details['email']
        )
        admin.update_credentials(
            self._db, admin_details['access_token'], admin_details['credentials']
        )
        return admin

    def check_csrf_token(self):
        """Verifies that the provided CSRF token is valid."""
        token = self.get_csrf_token()
        if not token or token != flask.request.form.get("csrf_token"):
            return INVALID_CSRF_TOKEN
        return token

    def get_csrf_token(self):
        """Returns the CSRF token for the current session."""
        return flask.session.get("csrf_token")

class SigninController(AdminController):

    ERROR_RESPONSE_TEMPLATE = """<!DOCTYPE HTML>
<html lang="en">
<head><meta charset="utf8"></head>
</body>
<p><strong>%(status_code)d ERROR:</strong> %(message)s</p>
</body>
</html>"""

    def signin(self):
        """Redirects admin if they're signed in."""
        admin = self.authenticated_admin_from_request()

        if isinstance(admin, ProblemDetail):
            redirect_url = flask.request.args.get("redirect")
            return redirect(self.google.auth_uri(redirect_url), Response=Response)
        elif admin:
            return redirect(flask.request.args.get("redirect"), Response=Response)

    def redirect_after_signin(self):
        """Uses the Google OAuth client to determine admin details upon
        callback. Barring error, redirects to the provided redirect url.."""

        admin_details, redirect_url = self.google.callback(flask.request.args)
        if isinstance(admin_details, ProblemDetail):
            return self.error_response(admin_details)

        if not self.staff_email(admin_details['email']):
            return self.error_response(INVALID_ADMIN_CREDENTIALS)
        else:
            admin = self.authenticated_admin(admin_details)
            flask.session["admin_access_token"] = admin_details.get("access_token")
            flask.session["csrf_token"] = base64.b64encode(os.urandom(24))
            return redirect(redirect_url, Response=Response)
    
    def staff_email(self, email):
        """Checks the domain of an email address against the admin-authorized
        domain"""

        staff_domain = Configuration.policy(
            Configuration.ADMIN_AUTH_DOMAIN, required=True
        )
        domain = email[email.index('@')+1:]
        return domain == staff_domain

    def error_response(self, problem_detail):
        """Returns a problem detail as an HTML response"""
        html = self.ERROR_RESPONSE_TEMPLATE % dict(
            status_code=problem_detail.status_code,
            message=problem_detail.detail
        )
        return Response(html, problem_detail.status_code)


class WorkController(CirculationManagerController):

    def suppress(self, data_source, identifier):
        """Suppress the license pool associated with a book."""
        
        # Turn source + identifier into a LicensePool
        pool = self.load_licensepool(data_source, identifier)
        if isinstance(pool, ProblemDetail):
            # Something went wrong.
            return pool
    
        pool.suppressed = True
        return Response("", 200)

    def unsuppress(self, data_source, identifier):
        """Unsuppress the license pool associated with a book."""
        
        # Turn source + identifier into a LicensePool
        pool = self.load_licensepool(data_source, identifier)
        if isinstance(pool, ProblemDetail):
            # Something went wrong.
            return pool
    
        pool.suppressed = False
        return Response("", 200)
    
