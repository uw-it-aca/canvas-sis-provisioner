# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from django.conf import settings
from uw_canvas.users import Users
from dateutil.parser import parse
from datetime import timedelta
from pytz import timezone
import argparse
import csv
import os

UTC = timezone('UTC')
PST = timezone('US/Pacific')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'login', help='Login for which to get page views')
        parser.add_argument(
            'start', help='Starting date for page views, yyyy-mm-dd')
        parser.add_argument(
            'end', help='Ending date for page views, yyyy-mm-dd')

    def handle(self, *args, **options):
        login = options.get('login')
        start_time = parse(options.get('start'))
        end_time = parse(options.get('end')) + timedelta(hours=24)

        if end_time < start_time:
            raise ValueError('End date is before start date')

        filename = '{}-page-views-{}-{}.csv'.format(
            login, start_time.date(), end_time.date())
        outfile = open(filename, 'w')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')
        writer.writerow([
            'datetime', 'remote_ip', 'user_agent', 'http_method', 'url',
            'session_id', 'context_type', 'action', 'participated',
            'contributed'])

        canvas = Users(per_page=500)
        page_views = canvas.get_user_page_views_by_sis_login_id(
            login, start_time=start_time, end_time=end_time)

        for pv in page_views:
            dt = parse(pv['created_at']).replace(tzinfo=UTC).astimezone(PST)
            participated = 'yes' if pv['participated'] else ''
            contributed = 'yes' if pv['contributed'] else ''
            writer.writerow([
                dt.strftime('%Y-%m-%d %H:%M:%S'), pv['remote_ip'],
                pv['user_agent'], pv['http_method'], pv['url'],
                pv['session_id'], pv['context_type'], pv['action'],
                participated, contributed])

        outfile.close()
