from django.core.management.base import BaseCommand
from django.conf import settings
from sis_provisioner.dao.term import (
    get_term_by_year_and_quarter, get_term_by_date)
from sis_provisioner.builders.courses import UnusedCourseBuilder
from datetime import datetime


class Command(BaseCommand):
    args = "<term_sis_id>"
    help = "Create a csv import file of unused courses for the specified \
            term. The csv file can be used to delete unused courses from \
            Canvas."

    def handle(self, *args, **options):

        if len(args):
            (year, quarter) = args[0].split('-')
            term = get_term_by_year_and_quarter(year, quarter)
        else:
            term = get_term_by_date(datetime.now().date())

        csv_path = UnusedCourseBuilder().build()

        if not settings.SIS_IMPORT_CSV_DEBUG:
            print csv_path
