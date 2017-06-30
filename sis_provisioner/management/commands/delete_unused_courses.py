from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import (
    Term, EmptyQueueException, MissingImportPathException)
from sis_provisioner.dao.term import (
    get_term_by_date, get_term_before, get_term_by_year_and_quarter)
from sis_provisioner.builders.courses import UnusedCourseBuilder
from datetime import datetime
import traceback


class Command(SISProvisionerCommand):
    help = "Create a csv import file of unused courses for a specified \
            term. The csv file will be used to delete unused courses from \
            Canvas."

    def add_arguments(self, parser):
        parser.add_argument('-t', '--term-sis-id', help='Term SIS ID')

    def handle(self, *args, **options):
	term_sis_id = options.get('term-sis-id')
        if term_sis_id:
            (year, quarter) = term_sis_id.split('-')
            target_term = get_term_by_year_and_quarter(year, quarter)

        else:
            curr_date = datetime.now().date()
            curr_term = get_term_by_date(curr_date)

            if curr_date < curr_term.census_day:
                self.update_job()
                return

            target_term = get_term_before(get_term_before(curr_term))

        term_sis_id = target_term.canvas_sis_id()
        try:
            imp = Term.objects.queue_unused_courses(term_sis_id)
        except EmptyQueueException:
            self.update_job()
            return

        try:
            imp.csv_path = UnusedCourseBuilder().build(term_sis_id=term_sis_id)
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
