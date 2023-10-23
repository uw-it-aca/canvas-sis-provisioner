# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.db.utils import IntegrityError
from django.utils.timezone import utc
from sis_provisioner.dao.canvas import update_course_sis_id
from sis_provisioner.dao.course import adhoc_course_sis_id
from sis_provisioner.models.course import Course
from uw_canvas.terms import Terms
from dateutil.parser import parse
from dateutil.parser._parser import ParserError
from logging import getLogger
import codecs
import csv

logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Insert courses from a Canvas course provisioning report file"

    def add_arguments(self, parser):
        parser.add_argument('course_file', help='Course file path')
        parser.add_argument('-c', '--commit', action='store_true',
                            dest='commit', default=False,
                            help='Insert/update course models')

    def get_all_terms(self):
        terms = {}
        for term in Terms().get_all_terms():
            terms[str(term.term_id)] = term.sis_term_id or 'default'
        return terms

    def handle(self, *args, **options):
        course_file = options.get('course_file')
        terms = self.get_all_terms()

        with default_storage.open(course_file, mode='r') as csvfile:
            reader = csv.reader(codecs.iterdecode(csvfile, 'utf-8'))

            for row in reader:
                canvas_id = row[1]
                term_id = row[4].lstrip('1').lstrip('0')
                sis_source_id = None if (row[12] == "\\N") else row[12]
                try:
                    created_at = parse(row[8]).replace(tzinfo=utc)
                except ParserError as ex:
                    pass

                if not options.get('commit'):
                    logger.info(
                        f'Canvas ID: {canvas_id}, SIS ID: {sis_source_id}, '
                        f'Created: {created_at}')
                    continue

                try:
                    course = Course.objects.find_course(
                        canvas_id, sis_source_id)
                    if course.expiration_date is None:
                        # Backfill sis course with new attrs
                        course.course_id = sis_source_id
                        course.canvas_course_id = canvas_id
                        course.created_date = created_at
                        course.expiration_date = \
                            course.default_expiration_date
                        course.save()

                except Course.DoesNotExist:
                    course = Course(
                        course_id=sis_source_id,
                        canvas_course_id=canvas_id,
                        course_type=Course.ADHOC_TYPE,
                        term_id=terms.get(term_id),
                        created_date=created_at,
                        priority=Course.PRIORITY_NONE)
                    expiration_date = course.default_expiration_date

                    # Temporary logic for first round of expirations
                    if expiration_date.year == 2023:
                        expiration_date = expiration_date.replace(
                            month=12, day=18)

                    course.save()
