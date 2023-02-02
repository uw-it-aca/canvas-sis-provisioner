from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.utils.timezone import utc
from sis_provisioner.models.course import Course
from uw_canvas.terms import Terms
from dateutil.parser import parse
import csv


class Command(BaseCommand):
    help = "Insert courses from file."

    def add_arguments(self, parser):
        parser.add_argument(
            'course_file', help='Course file path')

    def get_all_terms(self):
        terms = {}
        for term in Terms().get_all_terms():
            # print('Term id: "{}", sis_id: "{}", name: "{}"'.format(
            #     term.term_id, term.sis_term_id, term.name))
            terms[term.term_id] = term.sis_term_id or 'default'
        return terms

    def handle(self, *args, **options):
        course_file = options.get('course_file')
        terms = self.get_all_terms()

        with default_storage.open(course_file, mode='r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                canvas_id = row[1]
                term_id = row[4]
                created_at = parse(row[8]).replace(tzinfo=utc)
                sis_source_id = row[13]
                workflow_state = row[14]
                term_sis_id = terms.get(term_id)

                course = None
                if sis_source_id:
                    try:
                        course = Course.objects.get(course_id=sis_source_id)
                        course.created_date = created_at
                    except Course.DoesNotExist:
                        pass

                if course is None:
                    course = Course(
                        course_id=sis_source_id,
                        canvas_course_id=canvas_id,
                        course_type=Course.ADHOC_TYPE,
                        term_id=terms.get(term_id),
                        created_date=created_at,
                        priority=Course.PRIORITY_NONE)

                course.save()
