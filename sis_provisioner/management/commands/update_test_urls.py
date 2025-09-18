# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test.utils import override_settings
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.dao.canvas import (
    get_lti_registrations, update_lti_registration)
from restclients_core.exceptions import DataFailureException
import json
from logging import getLogger


logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = "Update LTI URLs for non-production Canvas instances"

    BLTI_HOSTS = [
        # canvas
        ('https://apps.canvas.uw.edu',
         'https://test-apps.canvas.uw.edu'),
        # panopto
        ('https://panopto-app.uw.edu',
         'https://test.panopto-app.uw.edu'),
        # course-users
        ('https://course-users.canvas.uw.edu',
         'https://test-course-users.canvas.uw.edu'),
        # course-roster
        ('https://courseroster.canvas.uw.edu',
         'https://test-courseroster.canvas.uw.edu'),
        # grading-standards
        ('https://grading-standards.canvas.uw.edu',
         'https://test-grading-standards.canvas.uw.edu'),
        # libguides
        ('https://libguides.canvas.uw.edu',
         'https://test-libguides.canvas.uw.edu'),
        # infohub
        ('https://infohub.canvas.uw.edu',
         'https://test-infohub.canvas.uw.edu')
    ]
    TEST_LABEL = '(TEST)'

    def handle(self, *args, **options):
        self.update_canvas_test()
        self.update_canvas_beta()
        self.update_job()

    def update_lti_registrations(self):
        for reg in get_lti_registrations(
                params={'include': 'overlaid_configuration'}):

            conf = reg.get('overlaid_configuration', {}) or {}
            target_link_uri = conf.get('target_link_uri', '') or ''

            for prod_host, test_host in self.BLTI_HOSTS:
                if target_link_uri.startswith(prod_host):

                    logger.info(f"Update LTI URLs: {prod_host}")

                    registration_json = json.dumps({
                        'name': self._label_test(reg.get('name', '')),
                        'configuration': {
                            'title': self._label_test(conf.get('title', ''))
                        } | (self._property('target_link_uri', conf) |
                             self._property('oidc_initiation_url', conf) |
                             self._property('public_jwk_url',  conf) |
                             self._property('redirect_uris', conf) |
                             self._property('redirect_uris', conf) |
                             self._property('scopes', conf) |
                             self._property('placements', conf) |
                             self._property('launch_settings', conf))
                    })

                    registration_update = json.loads(
                        registration_json.replace(prod_host, test_host))

                    logger.debug(f"{reg.get('id')} --> {registration_update}")
                    logger.info("Updating "
                                f"LTI {registration_update['name']}"
                                f" ({reg['id']})")

                    try:
                        update_lti_registration(
                            reg.get('id'), registration_update)
                    except DataFailureException as err:
                        logger.error(f"Canvas API {err.status}: {err}")
                        if err.status != 404:
                            raise

    def _label_test(self, name):
        return name if name.endswith(self.TEST_LABEL) else (
            f"{name} {self.TEST_LABEL}")

    def _property(self, prop, conf):
        try:
            return {prop: conf[prop]}
        except KeyError:
            return {}

    @override_settings(
        RESTCLIENTS_CANVAS_HOST="https://uw.beta.instructure.com")
    def update_canvas_beta(self):
        self.update_lti_registrations()

    @override_settings(
        RESTCLIENTS_CANVAS_HOST="https://uw.test.instructure.com")
    def update_canvas_test(self):
        self.update_lti_registrations()
