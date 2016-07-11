from sis_provisioner.models import Course, Term, User, Enrollment,\
    PRIORITY_NONE, PRIORITY_DEFAULT, PRIORITY_HIGH
from sis_provisioner.policy import UserPolicy, CoursePolicy
from restclients.sws.term import get_term_by_date, get_term_after
from restclients.sws.section import get_changed_sections_by_term,\
    get_section_by_label
from restclients.gws import GWS
from restclients.canvas.reports import Reports
from restclients.exceptions import DataFailureException
from django.utils.timezone import utc, localtime
from django.conf import settings
from django.db.models import Q
from logging import getLogger
from datetime import datetime, timedelta
import csv


class Loader():
    def __init__(self):
        self._user_policy = UserPolicy()
        self._course_policy = CoursePolicy()
        self._log = getLogger(__name__)

    def load_all_courses(self):
        """
        Loads all courses for the current and next terms with default
        priority, and updates all courses from previous term to priority
        none.
        """
        curr_term = get_term_by_date(datetime.now().date())

        if curr_term.bterm_last_day_add is not None:
            curr_last_date = curr_term.bterm_last_day_add
        else:
            curr_last_date = curr_term.last_day_add

        if datetime.now().date() <= curr_last_date:
            self.load_courses_for_term(curr_term)
        else:
            self.unload_courses_for_term(curr_term)

        if datetime.now() > curr_term.grade_submission_deadline:
            curr_term = get_term_after(curr_term)

        # Load courses for the next two terms
        next_term = get_term_after(curr_term)
        self.load_courses_for_term(next_term)
        self.load_courses_for_term(get_term_after(next_term))

    def queue_active_courses(self):
        """
        Finds all active Canvas courses for the current or next term, and
        updates them to priority high.
        """
        term = get_term_by_date(datetime.now().date())

        if datetime.now() > term.grade_submission_deadline:
            term = get_term_after(term)

        self.queue_active_courses_for_term(term)

    def queue_active_courses_for_term(self, term):
        client = Reports()
        canvas_term = client.get_term_by_sis_id(term.canvas_sis_id())
        canvas_account_id = getattr(settings, 'RESTCLIENTS_CANVAS_ACCOUNT_ID',
                                    None)

        # Canvas report of "unused" courses for the term
        unused_course_report = client.create_unused_courses_report(
            canvas_account_id, term_id=canvas_term.term_id)

        unused_courses = {}
        for row in csv.reader(client.get_report_data(unused_course_report)):
            # Create a lookup by unused course_sis_id
            try:
                unused_courses[row[1]] = True
            except Exception as ex:
                continue

        # Canvas report of all courses for the term
        all_course_report = client.create_course_provisioning_report(
            canvas_account_id, term_id=canvas_term.term_id)

        for row in csv.reader(client.get_report_data(all_course_report)):
            try:
                sis_course_id = row[1]
                self._course_policy.valid_academic_course_sis_id(sis_course_id)
            except Exception as ex:
                continue

            if sis_course_id not in unused_courses:
                try:
                    course = Course.objects.get(course_id=sis_course_id)
                    course.priority = PRIORITY_HIGH
                    course.save()
                except Course.DoesNotExist:
                    continue

        client.delete_report(unused_course_report)
        client.delete_report(all_course_report)

    def load_courses_for_term(self, term):
        """
        Loads all unseen course sections for the passed year and quarter with
        high priority.
        """
        term_id = term.canvas_sis_id()

        existing_course_ids = dict((c, p) for c, p in Course.objects.filter(
            term_id=term_id, course_type=Course.SDB_TYPE
        ).values_list("course_id", "priority"))

        tsc = dict((t.campus.lower(),
                    t.is_on) for t in term.time_schedule_construction)

        try:
            delta = Term.objects.get(term_id=term_id)
        except Term.DoesNotExist:
            delta = Term(term_id=term_id)

        delta.last_course_search_date = datetime.utcnow().replace(tzinfo=utc)
        if delta.courses_changed_since_date is None:
            days = getattr(settings, 'COURSES_CHANGED_SINCE_DAYS', 120)
            delta.courses_changed_since_date = (
                term.get_bod_first_day() - timedelta(days=days))
        delta.save()

        sections = get_changed_sections_by_term(
            localtime(delta.courses_changed_since_date).date(), term,
            transcriptable_course='all')

        new_courses = []
        for section_ref in sections:
            course_id = generate_course_id(section_ref)

            if course_id in existing_course_ids:
                if existing_course_ids[course_id] == PRIORITY_NONE:
                    Course.objects.filter(course_id=course_id).update(
                        priority=PRIORITY_HIGH)
                continue

            # Get the full section resource
            try:
                label = section_ref.section_label()
                section = get_section_by_label(label)
            except DataFailureException:
                continue
            except ValueError:
                continue

            # valid time schedule construction for campus
            campus = section.course_campus.lower()
            if campus not in tsc or tsc[campus]:
                continue

            if section.is_independent_study:
                for meeting in section.meetings:
                    for instructor in meeting.instructors:
                        if not instructor.uwregid:
                            continue

                        ind_course_id = "-".join([course_id,
                                                  instructor.uwregid])

                        if ind_course_id in existing_course_ids:
                            continue

                        course = Course(course_id=ind_course_id,
                                        course_type=Course.SDB_TYPE,
                                        term_id=term_id,
                                        priority=PRIORITY_HIGH)

                        new_courses.append(course)
            else:
                if section.is_primary_section:
                    primary_id = None
                else:
                    primary_id = generate_primary_course_id(section)

                course = Course(course_id=course_id,
                                course_type=Course.SDB_TYPE,
                                term_id=term_id,
                                primary_id=primary_id,
                                priority=PRIORITY_HIGH)

                new_courses.append(course)

        Course.objects.bulk_create(new_courses)

        delta.courses_changed_since_date = datetime.utcnow().replace(
            tzinfo=utc)
        delta.save()

    def unload_courses_for_term(self, term):
        """
        Updates all courses for the passed term with priority none.
        """
        Course.objects.filter(
            term_id=term.canvas_sis_id()).update(priority=PRIORITY_NONE)

    def load_enrollment(self, data):
        """
        Loads an enrollment from the passed data
        """
        section = data.get('Section')
        course_id = generate_course_id(section)
        reg_id = data.get('UWRegID')
        role = data.get('Role', Enrollment.STUDENT_ROLE)
        status = data.get('Status').lower()
        last_modified = data.get('LastModified')
        request_date = data.get('RequestDate')

        primary_course_id = None
        if not section.is_primary_section:
            primary_course_id = generate_primary_course_id(section)
        instructor_reg_id = data.get('InstructorUWRegID', None)
        full_course_id = '-'.join([course_id, instructor_reg_id]) if (
            instructor_reg_id is not None) else course_id

        try:
            course = Course.objects.get(course_id=full_course_id)
            if course.provisioned_date:
                enrollment = Enrollment.objects.get(course_id=course_id,
                                                    reg_id=reg_id,
                                                    role=role)
                if (last_modified > enrollment.last_modified or (
                        last_modified == enrollment.last_modified and
                        status == Enrollment.ACTIVE_STATUS)):
                    self._log.info('UPDATE: %s %s %s on %s status %s' % (
                        course_id, reg_id, role, last_modified, status))

                    enrollment.status = status
                    enrollment.last_modified = last_modified
                    enrollment.request_date = request_date
                    enrollment.primary_course_id = primary_course_id
                    enrollment.instructor_reg_id = instructor_reg_id

                    if enrollment.queue_id is None:
                        enrollment.priority = PRIORITY_DEFAULT
                    else:
                        enrollment.priority = PRIORITY_HIGH
                        self._log.info(
                            'IN QUEUE: %s %s status %s, queue_id %s' % (
                                course_id, reg_id, status, enrollment.queue_id)
                        )

                    enrollment.save()
                else:
                    self._log.info('LATE: %s %s before %s' % (
                        reg_id, last_modified, enrollment.last_modified))
            else:
                self._log.info('DROP: %s %s %s status %s' % (
                    full_course_id, reg_id, role, status))
                course.priority = PRIORITY_HIGH
                course.save()

        except Enrollment.DoesNotExist:
            self._log.info('LOAD: %s %s on %s status %s' % (
                course_id, reg_id, last_modified, status))
            enrollment = Enrollment(course_id=course_id, reg_id=reg_id,
                                    role=role, status=status,
                                    last_modified=last_modified,
                                    primary_course_id=primary_course_id,
                                    instructor_reg_id=instructor_reg_id)
            enrollment.save()
        except Course.DoesNotExist:
            # course provision effectively picks up event
            self._log.info('NO COURSE: %s %s status %s' % (
                full_course_id, reg_id, status))
            course = Course(course_id=full_course_id,
                            course_type=Course.SDB_TYPE,
                            term_id=self._course_policy.term_sis_id(section),
                            primary_id=primary_course_id,
                            added_date=datetime.utcnow().replace(tzinfo=utc),
                            priority=PRIORITY_HIGH)
            course.save()

    def load_all_users(self):
        """
        Loads users from pre-defined groups. Priority is set as
        New users: PRIORITY_DEFAULT
        Existing users: PRIORITY_DEFAULT
        Existing users no longer found in groups: PRIORITY_NONE
        """
        uwnetids = User.objects.all().values_list('net_id', flat=True)
        existing_netids = dict((u, True) for u in uwnetids)

        gws = GWS()
        policy = self._user_policy
        for group_id in getattr(settings, 'SIS_IMPORT_GROUPS', []):
            members = gws.get_effective_members(group_id)
            for member in members:
                if member.is_uwnetid() and member.name not in existing_netids:
                    try:
                        load_user(policy.get_person_by_netid(member.name))
                        existing_netids[member.name] = True
                    except Exception as err:
                        self._log.info('load_all_users: Skipped %s (%s)' % (
                            member.name, err))


def load_user(person):
    """
    Loads a single user from PWS-returned json
    """
    if person.uwnetid is None or person.uwregid is None:
        return

    users = User.objects.filter(Q(reg_id=person.uwregid) |
                                Q(net_id=person.uwnetid))

    user = None
    if len(users) == 1:
        user = users[0]
    elif len(users) > 1:
        users.delete()

    if user is None:
        user = User(added_date=datetime.utcnow().replace(tzinfo=utc))

    if (user.reg_id != person.uwregid or
            user.net_id != person.uwnetid):
        user.reg_id = person.uwregid
        user.net_id = person.uwnetid
        user.priority = PRIORITY_HIGH
        user.save()

    return user


def generate_course_id(section):
    """
    Generates the unique identifier for a course.
    """
    return '-'.join([section.term.canvas_sis_id(),
                     section.curriculum_abbr.upper(),
                     section.course_number,
                     section.section_id.upper()])


def generate_primary_course_id(section):
    """
    Generates the unique identifier for a course.
    """
    return '-'.join([section.term.canvas_sis_id(),
                     section.primary_section_curriculum_abbr.upper(),
                     section.primary_section_course_number,
                     section.primary_section_id.upper()])
