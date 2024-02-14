# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from django.conf import settings
from sis_provisioner.dao.canvas import (
    get_course_report_data, DataFailureException)
from uw_canvas.collaborations import Collaborations
from logging import getLogger
import csv

logger = getLogger(__name__)


class Command(BaseCommand):
    help = ('Create a report of all course collaborations')

    def handle(self, *args, **options):
        client = Collaborations()

        outpath = 'course-collaborations.csv'
        outfile = open(outpath, 'w')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')
        writer.writerow([
            'course_id', 'course_sis_id', 'collaboration_id',
            'collaboration_type', 'document_id', 'url', 'title'])

        report_data = get_course_report_data()
        header = report_data.pop(0)
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

        outfile.close()
