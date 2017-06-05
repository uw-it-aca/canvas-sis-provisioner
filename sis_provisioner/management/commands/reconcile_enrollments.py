from django.core.management.base import BaseCommand
from uw_canvas.accounts import Accounts as CanvasAccounts
from uw_canvas.courses import Courses as CanvasCourses
from uw_canvas.sections import Sections as CanvasSections
from restclients_core.exceptions import DataFailureException
from sis_provisioner.models import Course, PRIORITY_HIGH
from sis_provisioner.dao.course import get_section_by_label
from optparse import make_option
import re

default_account = 'uwcourse'
default_term = '2013-spring'

class Command(BaseCommand):
    help = "Reconcile enrollment differences between Canvas and UW-SWS"

    _re_canvas_id = re.compile(r'^\d+$')
    _re_independent_study = re.compile(r"""[0-9]{4}-
                                           (winter|spring|summer|autumn)-
                                           [A-Z ]+-
                                           [0-9]+-
                                           [A-Z]{1,3}-
                                           [A-Z0-9]+$
                                        """,
                                       re.X)
    def add_arguments(self, parser):
        parser.add_argument(
            '-r', '--root-account', action='store', dest='root_account',
            default=default_account,
            help='reconcile sections at and below root account (default: %s)' % default_account)
        parser.add_argument(
            '-t', '--term', action='store', dest='term', default=default_term,
            help='reconcile sections offered during term (default: %s)' % default_term)
        parser.add_argument(
            '-o', '--threshold', action='store', dest='threshold',
            default=1, help='ignore deltas below threshold, default 1')
        parser.add_argument(
            '-a', '--all-courses', action='store_true', dest='all_courses',
            default=False, help='reconcile all courses, default is only published courses')
        parser.add_argument(
            '-p', '--print', action='store_true', dest='print', default=False,
            help='print deltas')
        parser.add_argument(
            '-d', '--dry-run', action='store_true', dest='dry_run',
            default=False, help='print deltas, do not update Course models')

    def handle(self, *args, **options):
        if options['print'] or options['dry_run']:
            print("section_id,canvas_enrollments,sws_enrollments,delta")

        canvas_courses = CanvasCourses(per_page=50)
        canvas_sections = CanvasSections(per_page=50)
        canvas_accounts = CanvasAccounts(per_page=50)
        for account in canvas_accounts.get_all_sub_accounts_by_sis_id(options['root_account']):

            if options['print']:
                print('# Account: "%s" (%s, %s)' % (account.name,
                                                    account.sis_account_id,
                                                    account.account_id))

            if (account.sis_account_id is not None
                and re.match(r'^(([^:]+:){4}|curriculum-).*$', str(account.sis_account_id))):

                n_courses = 0
                n_sections = 0
                n_bad_sections = 0

                if options['all_courses']:
                    courses = canvas_courses.get_courses_in_account_by_sis_id(account.sis_account_id)
                else:
                    courses = canvas_courses.get_published_courses_in_account_by_sis_id(account.sis_account_id)

                for course in courses:
                    if (course.sis_course_id is not None
                        and re.match('^%s-' % options['term'], course.sis_course_id)
                        and not self._is_independent_study(course.sis_course_id)):
                        n_courses += 1
                        sections = canvas_sections.get_sections_with_students_in_course_by_sis_id(course.sis_course_id)
                        for section in sections:
                            if section.sis_section_id is not None:
                                section_id = section.sis_section_id
                                n_sections += 1

                                try:
                                    s = self.get_section_by_id(section_id)
                                except DataFailureException as err:
                                    print('# BAD SECTION: %s' % err)
                                    continue

                                enrollments = (s.current_enrollment + s.auditors)
                                delta = len(section.students) - enrollments
                                if delta >= options['threshold']:
                                    n_bad_sections += 1
                                    if options['print'] or options['dry_run']:
                                        print("%s,%s,%s,%s" % (section_id, len(section.students), enrollments, delta))

                                    if not options['dry_run']:
                                        try:
                                            section_model_id = re.sub(r'--$', '', section_id)
                                            section_model = Course.objects.get(course_id=section_model_id)
                                        except Course.DoesNotExist:
                                            section_model = Course(course_id=section_model_id)

                                        if not section_model.queue_id and section_model.priority < PRIORITY_HIGH:
                                            section_model.priority = PRIORITY_HIGH
                                            section_model.save()

                if options['print']:
                    if n_courses and n_sections and n_bad_sections:
                        print('# %s of %s (%.3s%%) sections in %s courses for %s'
                              % (n_bad_sections, n_sections,
                                 ((n_bad_sections/float(n_sections)) * 100),
                                 n_courses, options['term']))

    def get_section_by_id(self, section_id):
        """
        Fetch the section resource for the passed section ID.
        """
        (year, quarter, curr_abbr, course_num, section_id,
            reg_id) = self._section_data_from_id(section_id)

        label = "%s,%s,%s,%s/%s" % (str(year), quarter.lower(),
                                    curr_abbr.upper(), course_num, section_id)

        return get_section_by_label(label)

    def _section_data_from_id(self, section_id):
        section_id = re.sub(r'--$', '', section_id)
        reg_id = None
        try:
            (year, quarter, curr_abbr, course_num,
                section_id, reg_id) = section_id.split('-', 5)
        except ValueError:
            (year, quarter, curr_abbr, course_num,
                section_id) = section_id.split('-', 4)
        return year, quarter, curr_abbr, course_num, section_id, reg_id

    def _is_independent_study(self, sis_id):
        return (self._re_independent_study.match(sis_id) != None)

    def _is_canvas_id(self, id):
        return self._re_canvas_id.match(str(id))

