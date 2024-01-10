# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from uw_canvas.external_tools import ExternalTools
import os
import sys
import json


class Command(BaseCommand):
    """
    For an example of what the JSON config should look like, which can be
    one or an array of app configs, see:

    https://canvas.instructure.com/doc/api/external_tools.html#method.external_tools.show
    """
    help = "Insert LTI tools into Canvas."

    def add_arguments(self, parser):
        parser.add_argument('config_path', help='Config filepath')

    def handle(self, *args, **options):
        config_path = options.get('config_path')
        self.external_tools = ExternalTools()
        self.tool_set = {}
        if not os.access(config_path, os.R_OK):
            print("ERROR: invalid json config", file=sys.stderr)
            return

        try:
            with open(config_path, 'r') as jsonfile:
                lticonf = json.loads(jsonfile.read())

            if isinstance(lticonf, list):
                for conf in lticonf:
                    self.load_lti(conf)
            else:
                self.load_lti(lticonf)
        except Exception as err:
            print('ERROR: {}'.format(err), file=sys.stderr)

    def load_lti(self, conf):
        canvas_account = conf.get('account_canvas_id')
        if not canvas_account:
            sis_id = conf.get('account_sis_id')
            if sis_id:
                canvas_account = self.external_tools.sis_account_id(sis_id)

        if canvas_account:
            if canvas_account not in self.tool_set:
                tools = self.external_tools.get_external_tools_in_account(
                    canvas_account)
                self.tool_set[canvas_account] = tools

        for tool in self.tool_set[canvas_account]:
            if (tool.get('url') == conf.get('url') and
                    tool.get('consumer_key') == conf.get('consumer_key')):
                print('"{}" already installed in {}'.format(
                    conf.get('name'), canvas_account), file=sys.stderr)
                return

        tool = self.external_tools.add_external_tool_to_account(
            canvas_account, **conf)

        print('Installed "{}" ({}) in {}'.format(
            conf.get('name'), tool.get('id'), canvas_account))
