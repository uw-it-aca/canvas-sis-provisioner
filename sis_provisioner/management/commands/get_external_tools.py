from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from restclients.canvas.external_tools import ExternalTools
from restclients.canvas.accounts import Accounts
from restclients.canvas.courses import Courses
from restclients.exceptions import DataFailureException
from optparse import make_option
import re
import sys
import csv


default_account = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID


class Command(BaseCommand):
    help = "Report externals tools in account"

    option_list = BaseCommand.option_list + (
        make_option('-a', '--account', action='store', dest='account_id', type="string",
                    default=default_account,
                    help='show external tools in account by id or sis_id (default: %s)' % default_account),
        make_option('-r', '--recurse', action='store_true', dest='recurse',
                    default=False, help='recurse through subaccounts'),
        make_option('-c', '--courses', action='store_true', dest='courses',
                    default=False, help='include account courses in report'),
        make_option('-s', '--sessionless-url', action='store_true', dest='sessionless',
                    default=False, help='show sessionless url with each external tool'),
    )

    def handle(self, *args, **options):
        self._tools = ExternalTools()
        self._accounts = Accounts()
        self._courses = Courses()
        self._options = options

        csv.register_dialect("unix_newline", lineterminator="\n")
        self._writer = csv.writer(sys.stdout, dialect="unix_newline")

        self._headers = ['tool_name', 'tool_id', 'tool_type', 'account_name', 'account_id']

        if self._options['courses']:
            self._headers.append('course_name')
            self._headers.append('course_id')

        if options['sessionless']:
            self._headers.append('sessionless url')

        accounter = self._accounts.get_account if re.match(r'^\d+$', options['account_id']) \
                        else self._accounts.get_account_by_sis_id
        try:
            self.report_external_tools(accounter(options['account_id']))

        except DataFailureException as err:
            if err.status == 404:
                print >> sys.stderr, 'Unknown Sub-Account \"%s\"' % (options['account_id'])

    def report_external_tools(self, account):
        tools = self._tools.get_external_tools_in_account(account.account_id)
        self._print_tools(tools, account)

        if self._options['courses']:
            courses = self._courses.get_published_courses_in_account(account.account_id)
            for course in courses:
                tools = self._tools.get_external_tools_in_course(course.course_id)
                self._print_tools(tools, account, course)
                
        if self._options['recurse']:
            for account in self._accounts.get_sub_accounts(account.account_id):
                self.report_external_tools(account)

    def _print_tools(self, tools, account, course=None):
        if len(tools):
            if self._headers:
                self._writer.writerow(self._headers)
                self._headers = None
            
            for tool in tools:
                tool_types = []
                for tt in ['account', 'course', 'user']:
                    if tool.get("%s_navigation" % tt):
                        tool_types.append(tt)

                tool_type = ' & '.join(tool_types)
                line = [tool['name'], tool['id'], tool_type, account.name, account.account_id]

                if self._options['courses']:
                    line.append(course.name)
                    line.append(course.course_id)

                if self._options['sessionless']:
                    try:
                        sessionless = self._tools.get_sessionless_launch_url_from_account(tool['id'], account.account_id)
                        line.append(sessionless['url'])
                    except DataFailureException as ex:
                        line.append('')
                self._writer.writerow(line)
