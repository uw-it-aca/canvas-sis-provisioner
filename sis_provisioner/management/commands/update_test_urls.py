from django.test.utils import override_settings
from django.conf import settings
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.external_tools import ExternalTool
from sis_provisioner.dao.canvas import update_external_tool
from uw_canvas.accounts import Accounts
from restclients_core.dao import LiveDAO
from restclients_core.exceptions import DataFailureException
import json


class Command(SISProvisionerCommand):
    help = "Fixes the discovery and LTI URLs for uw.test and uw.beta"

    HOSTS = {
        'canvas': {
            'prod': 'https://apps.canvas.uw.edu',
            'test': 'https://test-apps.canvas.uw.edu'},
        'panopto': {
            'prod': 'https://panopto-app.uw.edu',
            'test': 'https://panopto-dev.s.uw.edu'},
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

    def update_discovery_url(self, discovery_url):
        account_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID

        LiveDAO.pools = {}
        auth = Accounts().get_auth_settings(account_id)

        if auth.auth_discovery_url != discovery_url:
            auth.auth_discovery_url = discovery_url
            Accounts().update_auth_settings(account_id, auth)

    def update_blti_urls(self):
        for service in self.HOSTS:
            prod_host = self.HOSTS.get(service).get('prod')
            test_host = self.HOSTS.get(service).get('test')

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

    @override_settings(
        RESTCLIENTS_CANVAS_HOST="https://uw.beta.instructure.com")
    def update_canvas_beta(self):
        self.update_discovery_url("{host}/wayf-beta".format(
            host=self.HOSTS['canvas']['test']))
        self.update_blti_urls()

    @override_settings(
        RESTCLIENTS_CANVAS_HOST="https://uw.test.instructure.com")
    def update_canvas_test(self):
        self.update_discovery_url("{host}/wayf-test".format(
            host=self.HOSTS['canvas']['test']))
        self.update_blti_urls()
