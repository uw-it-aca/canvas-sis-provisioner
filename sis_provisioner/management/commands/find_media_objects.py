# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from django.conf import settings
from uw_canvas.reports import Reports
from uw_canvas.media_objects import MediaObjects
from restclients_core.exceptions import DataFailureException
from logging import getLogger
import csv

logger = getLogger(__name__)


class Command(BaseCommand):
    help = ("Create a report of media objects in courses, for the "
            "specified term.")

    def add_arguments(self, parser):
        parser.add_argument('term_sis_id', help='Term SIS ID')

    def handle(self, *args, **options):
        term_sis_id = options.get('term_sis_id')

        outpath = f"/{settings.BASE_DIR}/{term_sis_id}-media-objects.csv"
        outfile = open(outpath, "w")
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')
        writer.writerow([
            'course_id', 'course_sis_id', 'media_id', 'media_type',
            'media_title', 'media_tracks', 'media_source_content_type',
            'media_source_container_format', 'media_source_bitrate',
            'media_source_size'
        ])

        report_client = Reports()

        term = report_client.get_term_by_sis_id(term_sis_id)

        user_report = report_client.create_course_provisioning_report(
            settings.RESTCLIENTS_CANVAS_ACCOUNT_ID, term_id=term.term_id)
        sis_data = report_client.get_report_data(user_report)
        report_client.delete_report(user_report)

        mo_client = MediaObjects()

        for row in csv.reader(sis_data):
            if not len(row) or row[0] == 'canvas_course_id':
                continue

            course_id = row[0]
            sis_course_id = row[1]

            try:
                media_objects = mo_client.get_media_objects_by_course_id(
                    course_id)
            except DataFailureException as ex:
                logger.error(
                    f'GET media_objects failed for course {course_id}: {ex}')
                continue

            for mo in media_objects:
                tracks = [mt.kind for mt in mo.media_tracks]
                for ms in mo.media_sources:
                    writer.writerow([
                        course_id, sis_course_id, mo.media_id, mo.media_type,
                        mo.title, ', '.join(tracks), ms.content_type,
                        ms.container_format, ms.bitrate, ms.size])

        outfile.close()
