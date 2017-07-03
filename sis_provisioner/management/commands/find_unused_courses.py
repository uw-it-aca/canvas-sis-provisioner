from django.core.management.base import BaseCommand
from django.conf import settings
from sis_provisioner.dao.term import (
    get_term_by_year_and_quarter, get_term_by_date)
from sis_provisioner.builders.courses import UnusedCourseBuilder
from datetime import datetime


class Command(BaseCommand):
    help = "Create a csv import file of unused courses for the specified \
            term. The csv file can be used to delete unused courses from \
            Canvas."

    def add_arguments(self, parser):
        parser.add_argument('term-sis-id', help='Term SIS ID')

    def handle(self, *args, **options):
        term_sis_id = options.get('term-sis-id')
        if term_sis_id:
            (year, quarter) = term_sis_id.split('-')
            term = get_term_by_year_and_quarter(year, quarter)
        else:
            term = get_term_by_date(datetime.now().date())

        term_sis_id = term.canvas_sis_id()
        csv_path = UnusedCourseBuilder().build(term_sis_id=term_sis_id)

        if not settings.SIS_IMPORT_CSV_DEBUG:
            print(csv_path)
