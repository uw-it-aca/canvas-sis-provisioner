from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from restclients_core.exceptions import DataFailureException
from uw_canvas.external_tools import ExternalTools
import os
import json


class Command(BaseCommand):
    help = """Insert LTI tools into Canvas.
    see: https://canvas.instructure.com/doc/api/external_tools.html#method.external_tools.show
    for an example of what the JSON config should look like, which can be one or an array of
    app configs.
    """


    def handle(self, *args, **options):
        self.external_tools = ExternalTools()
        self.tool_set = {}
        if len(args) != 1 or not os.access(args[0], os.R_OK):
            print >> self.stderr, "ERROR: invalid json config"
            return

        try:
            with open(args[0], 'r') as jsonfile:
                lticonf = json.loads(jsonfile.read())

            if isinstance(lticonf, list):
                for conf in lticonf:
                    self.load_lti(conf)
            else:
                self.load_lti(lticonf)
        except Exception as err:
            print >> self.stderr, 'ERROR: %s' % err

    def load_lti(self, conf):
        try:
            canvas_account = conf.get('account_canvas_id')
            if not canvas_account:
                sis_id = conf.get('account_sis_id')
                if sis_id:
                    canvas_account = self.external_tools.sis_account_id(sis_id)

            if canvas_account:
                if canvas_account not in self.tool_set:
                    self.tool_set[canvas_account] = self.external_tools.get_external_tools_in_account(canvas_account)

            for tool in self.tool_set[canvas_account]:
                if (tool.get('url') == conf.get('url')
                    and tool.get('consumer_key') == conf.get('consumer_key')):
                    print >> self.stderr, '"%s" already installed in %s' % (conf.get('name'), canvas_account)
                    return

            tool = self.external_tools.add_external_tool_to_account(canvas_account, **conf)

            print('Installed \"%s\" (%s) in %s' % (
                conf.get('name'), tool.get('id'), canvas_account))

        except DataFailureException as err:
            raise
