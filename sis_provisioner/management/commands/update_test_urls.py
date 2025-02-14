# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test.utils import override_settings
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.external_tools import ExternalTool
from sis_provisioner.dao.canvas import (
    update_external_tool, get_developer_keys, update_developer_key)
from restclients_core.dao import LiveDAO
from restclients_core.exceptions import DataFailureException
from logging import getLogger
import json


logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = "Update LTI URLs for non-production Canvas instances"

    BLTI_HOSTS = {
        'canvas': {
            'prod': 'https://apps.canvas.uw.edu',
            'test': 'https://test-apps.canvas.uw.edu'},
        'panopto': {
            'prod': 'https://panopto-app.uw.edu',
            'test': 'https://test.panopto-app.uw.edu'},
        'course-users': {
            'prod': 'https://course-users.canvas.uw.edu',
            'test': 'https://test-course-users.canvas.uw.edu'},
        'course-roster': {
            'prod': 'https://courseroster.canvas.uw.edu',
            'test': 'https://test-courseroster.canvas.uw.edu'},
        'grading-standards': {
            'prod': 'https://grading-standards.canvas.uw.edu',
            'test': 'https://test-grading-standards.canvas.uw.edu'},
        'libguides': {
            'prod': 'https://libguides.canvas.uw.edu',
            'test': 'https://test-libguides.canvas.uw.edu'},
        'infohub': {
            'prod': 'https://infohub.canvas.uw.edu',
            'test': 'https://test-infohub.canvas.uw.edu'},
    }

    def handle(self, *args, **options):
        self.update_canvas_test()
        self.update_canvas_beta()
        self.update_job()

    def update_blti_urls(self):
        LiveDAO.pools = {}
        for service in self.BLTI_HOSTS:
            prod_host = self.BLTI_HOSTS.get(service).get('prod')
            test_host = self.BLTI_HOSTS.get(service).get('test')

            for tool in ExternalTool.objects.get_by_hostname(prod_host):
                new_config = tool.config.replace(prod_host, test_host)
                try:
                    update_external_tool(
                        tool.account.canvas_id, tool.canvas_id,
                        json.loads(new_config))
                except DataFailureException as err:
                    # 404s OK
                    if err.status != 404:
                        raise

    def update_developer_keys(self):
        for key in get_developer_keys():
            for service in self.BLTI_HOSTS:
                prod_host = self.BLTI_HOSTS.get(service).get('prod')
                test_host = self.BLTI_HOSTS.get(service).get('test')

                tool = key.get('tool_configuration', {}) or {}
                if (tool.get('target_link_uri', '').startswith(prod_host)):
                    tool_json = json.dumps(tool).replace(prod_host, test_host)
                    tool_update = json.loads(tool_json)

                    key_update = {
                        'tool_configuration': {
                            'settings': tool_update
                        },
                        'developer_key': {
                            'name': key.get(
                                'name', f"Key {key['id']}") + ' (TEST)',
                            'redirect_uris': tool_update.get(
                                'target_link_uri'),
                            'scopes': tool.get('scopes', [])
                        }
                    }

                    try:
                        logger.info(f"Updating developer key {key['id']}")
                        update_developer_key(key['id'], key_update)
                    except DataFailureException as err:
                        # 404s OK
                        logger.error(f"Canvas API {err.status}: {err}")
                        if err.status != 404:
                            raise

    @override_settings(
        RESTCLIENTS_CANVAS_HOST="https://uw.beta.instructure.com")
    def update_canvas_beta(self):
        self.update_blti_urls()
        self.update_developer_keys()

    @override_settings(
        RESTCLIENTS_CANVAS_HOST="https://uw.test.instructure.com")
    def update_canvas_test(self):
        self.update_blti_urls()
        self.update_developer_keys()
