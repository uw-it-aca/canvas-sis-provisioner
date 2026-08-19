# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import csv
from logging import getLogger

from django.core.management.base import BaseCommand
from uw_canvas.collaborations import Collaborations

from sis_provisioner.dao.canvas import DataFailureException, get_course_report_data

logger = getLogger(__name__)


class Command(BaseCommand):
    help = ('Create a report of all course collaborations')

    def handle(self, *args, **options):
        client = Collaborations()

        report_data = get_course_report_data()
        _header = report_data.pop(0)

        outpath = 'course-collaborations.csv'
        with open(outpath, 'w') as outfile:
            csv.register_dialect('unix_newline', lineterminator='\n')
            writer = csv.writer(outfile, dialect='unix_newline')
            writer.writerow([
                'course_id', 'course_sis_id', 'collaboration_id',
                'collaboration_type', 'document_id', 'url', 'title'])

            for row in csv.reader(report_data):
                if not len(row):
                    continue

                canvas_id = row[0]
                course_sis_id = row[1]
                try:
                    for col in client.get_collaborations_for_course(canvas_id):
                        writer.writerow([
                            canvas_id, course_sis_id, col.collaboration_id,
                            col.collaboration_type, col.document_id, col.url,
                            col.title])
                except DataFailureException as ex:
                    logger.info(f'ERROR fetching collaborations, {ex}')
                    continue
