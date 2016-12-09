from django.db import models
from django.conf import settings
from django.utils.timezone import utc, localtime
from sis_provisioner.dao.group import get_sis_import_members, is_modified_group
from sis_provisioner.dao.user import get_person_by_netid
from sis_provisioner.dao.course import (
    valid_academic_course_sis_id, valid_canvas_section, get_sections_by_term,
    get_section_by_label, is_time_schedule_construction)
from sis_provisioner.dao.canvas import (
    create_course_provisioning_report, create_unused_courses_report,
    get_report_data, delete_report, sis_import_by_path, get_sis_import_status,
    get_term_by_sis_id)
from sis_provisioner.exceptions import (
    CoursePolicyException, MissingLoginIdException, EmptyQueueException,
    MissingImportPathException)
from restclients.exceptions import DataFailureException
from datetime import datetime, timedelta
from logging import getLogger
import json
import csv
import re


logger = getLogger(__name__)


PRIORITY_NONE = 0
PRIORITY_DEFAULT = 1
PRIORITY_HIGH = 2
PRIORITY_IMMEDIATE = 3

PRIORITY_CHOICES = (
    (PRIORITY_NONE, 'none'),
    (PRIORITY_DEFAULT, 'normal'),
    (PRIORITY_HIGH, 'high'),
    (PRIORITY_IMMEDIATE, 'immediate')
)


class Job(models.Model):
    """ Represents provisioning commands.
    """
    name = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    changed_by = models.CharField(max_length=32)
    changed_date = models.DateTimeField()
    last_run_date = models.DateTimeField(null=True)
    is_active = models.NullBooleanField()
    health_status = models.CharField(max_length=512, null=True)
    last_status_date = models.DateTimeField(null=True)

    def json_data(self):
        return {
            'job_id': self.pk,
            'name': self.name,
            'title': self.title,
            'changed_by': self.changed_by,
            'changed_date': localtime(self.changed_date).isoformat() if (
                self.changed_date is not None) else None,
            'last_run_date': localtime(self.last_run_date).isoformat() if (
                self.last_run_date is not None) else None,
            'is_active': self.is_active,
            'health_status': self.health_status,
            'last_status_date': localtime(
                self.last_status_date).isoformat() if (
                    self.last_status_date is not None) else None,
        }


class TermManager(models.Manager):
    def queue_unused_courses(self, term_id):
        try:
            term = Term.objects.get(term_id=term_id)
            if (term.deleted_unused_courses_date is not None or
                    term.queue_id is not None):
                raise EmptyQueueException()
        except Term.DoesNotExist:
            term = Term(term_id=term_id)
            term.save()

        imp = Import(priority=PRIORITY_DEFAULT, csv_type='unused_course')
        imp.save()

        term.queue_id = imp.pk
        term.save()

        return imp

    def queued(self, queue_id):
        return super(TermManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        kwargs = {'queue_id': None}
        if provisioned_date is not None:
            # Currently only handles the 'unused_course' type
            kwargs['deleted_unused_courses_date'] = provisioned_date

        self.queued(queue_id).update(**kwargs)

    def initialize_course_search(self, sws_term):
        try:
            term = Term.objects.get(term_id=sws_term.canvas_sis_id())
        except Term.DoesNotExist:
            term = Term(term_id=sws_term.canvas_sis_id())

        term.last_course_search_date = datetime.utcnow().replace(tzinfo=utc)
        if term.courses_changed_since_date is None:
            term_first_day = sws_term.get_bod_first_day().replace(tzinfo=utc)
            days = getattr(settings, 'COURSES_CHANGED_SINCE_DAYS', 120)
            term.courses_changed_since_date = (
                term_first_day - timedelta(days=days))
        term.save()
        return term


class Term(models.Model):
    """ Represents the provisioned state of courses for a term.
    """
    term_id = models.CharField(max_length=20, unique=True)
    added_date = models.DateTimeField(auto_now_add=True)
    last_course_search_date = models.DateTimeField(null=True)
    courses_changed_since_date = models.DateTimeField(null=True)
    deleted_unused_courses_date = models.DateTimeField(null=True)
    queue_id = models.CharField(max_length=30, null=True)

    objects = TermManager()


class CourseManager(models.Manager):
    def get_linked_course_ids(self, course_id):
        return super(CourseManager, self).get_queryset().filter(
            primary_id=course_id).values_list('course_id', flat=True)

    def get_joint_course_ids(self, course_id):
        return super(CourseManager, self).get_queryset().filter(
            xlist_id=course_id).exclude(course_id=course_id).values_list(
                'course_id', flat=True)

    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        if priority > PRIORITY_DEFAULT:
            filter_limit = settings.SIS_IMPORT_LIMIT['course']['high']
        else:
            filter_limit = settings.SIS_IMPORT_LIMIT['course']['default']

        pks = super(CourseManager, self).get_queryset().filter(
            priority=priority, course_type=Course.SDB_TYPE,
            queue_id__isnull=True, provisioned_error__isnull=True
        ).order_by(
            'provisioned_date', 'added_date'
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='course')
        imp.save()

        # Mark the courses as in process, and reset the priority
        super(CourseManager, self).get_queryset().filter(
            pk__in=list(pks)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queued(self, queue_id):
        return super(CourseManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        kwargs = {'queue_id': None}
        if provisioned_date is not None:
            kwargs['provisioned_date'] = provisioned_date
            kwargs['priority'] = PRIORITY_DEFAULT

        self.queued(queue_id).update(**kwargs)

    def add_to_queue(self, section, queue_id):
        if section.is_primary_section:
            course_id = section.canvas_course_sis_id()
        else:
            course_id = section.canvas_section_sis_id()

        try:
            course = Course.objects.get(course_id=course_id)

        except Course.DoesNotExist:
            if section.is_primary_section:
                primary_id = None
            else:
                primary_id = section.canvas_course_sis_id()

            course = Course(course_id=course_id,
                            course_type=Course.SDB_TYPE,
                            term_id=section.term.canvas_sis_id(),
                            primary_id=primary_id)

        course.queue_id = queue_id
        course.save()
        return course

    def remove_from_queue(self, course_id, error=None):
        try:
            course = Course.objects.get(course_id=course_id)
            course.queue_id = None
            if error is not None:
                course.provisioned_error = True
                course.provisioned_status = error
            course.save()

        except Course.DoesNotExist:
            pass

    def update_status(self, section):
        if section.is_primary_section:
            course_id = section.canvas_course_sis_id()
        else:
            course_id = section.canvas_section_sis_id()

        try:
            course = Course.objects.get(course_id=course_id)
            try:
                valid_canvas_section(section)
                course.provisioned_status = None

            except CoursePolicyException as err:
                course.provisioned_status = 'Primary LMS: %s (%s)' % (
                    section.primary_lms, err)

            if section.is_withdrawn:
                course.priority = PRIORITY_NONE

            course.save()
        except Course.DoesNotExist:
            pass

    def add_all_courses_for_term(self, term):
        term_id = term.canvas_sis_id()
        existing_course_ids = dict((c, p) for c, p in (
            super(CourseManager, self).get_queryset().filter(
                term_id=term_id, course_type=Course.SDB_TYPE
            ).values_list('course_id', 'priority')))

        delta = Term.objects.initialize_course_search(term)

        new_courses = []
        for section_ref in get_sections_by_term(
                localtime(delta.courses_changed_since_date).date(), term):
            course_id = '-'.join([section_ref.term.canvas_sis_id(),
                                  section_ref.curriculum_abbr.upper(),
                                  section_ref.course_number,
                                  section_ref.section_id.upper()])

            if course_id in existing_course_ids:
                if existing_course_ids[course_id] == PRIORITY_NONE:
                    super(CourseManager, self).get_queryset().filter(
                        course_id=course_id).update(priority=PRIORITY_HIGH)
                continue

            try:
                label = section_ref.section_label()
                section = get_section_by_label(label)
                if is_time_schedule_construction(section):
                    logger.info('Course: SKIP %s, TSC on' % label)
                    continue
            except DataFailureException as err:
                logger.info('Course: SKIP %s, %s' % (label, err))
                continue
            except ValueError as err:
                logger.info('Course: SKIP, %s' % err)
                continue

            primary_id = None
            if section.is_independent_study:
                for instructor in section.get_instructors():
                    ind_course_id = '-'.join([course_id, instructor.uwregid])

                    if ind_course_id not in existing_course_ids:
                        course = Course(course_id=ind_course_id,
                                        course_type=Course.SDB_TYPE,
                                        term_id=term_id,
                                        primary_id=primary_id,
                                        priority=PRIORITY_HIGH)
                        new_courses.append(course)
            else:
                if not section.is_primary_section:
                    primary_id = section.canvas_course_sis_id()

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

    def prioritize_active_courses_for_term(self, term):
        canvas_term = get_term_by_sis_id(term.canvas_sis_id())
        canvas_account_id = getattr(settings, 'RESTCLIENTS_CANVAS_ACCOUNT_ID',
                                    None)

        # Canvas report of "unused" courses for the term
        unused_course_report = create_unused_courses_report(
            canvas_account_id, term_id=canvas_term.term_id)

        unused_courses = {}
        for row in csv.reader(get_report_data(unused_course_report)):
            # Create a lookup by unused course_sis_id
            try:
                unused_courses[row[1]] = True
            except Exception as ex:
                continue

        # Canvas report of all courses for the term
        all_course_report = create_course_provisioning_report(
            canvas_account_id, term_id=canvas_term.term_id)

        for row in csv.reader(get_report_data(all_course_report)):
            try:
                sis_course_id = row[1]
                valid_academic_course_sis_id(sis_course_id)
            except Exception as ex:
                continue

            if sis_course_id not in unused_courses:
                try:
                    course = Course.objects.get(course_id=sis_course_id)
                    course.priority = PRIORITY_HIGH
                    course.save()
                except Course.DoesNotExist:
                    continue

        delete_report(unused_course_report)
        delete_report(all_course_report)

    def deprioritize_all_courses_for_term(self, term):
        super(CourseManager, self).get_queryset().filter(
            term_id=term.canvas_sis_id()).update(priority=PRIORITY_NONE)


class Course(models.Model):
    """ Represents the provisioned state of a course.
    """
    SDB_TYPE = 'sdb'
    ADHOC_TYPE = 'adhoc'
    TYPE_CHOICES = ((SDB_TYPE, 'SDB'), (ADHOC_TYPE, 'Ad Hoc'))

    course_id = models.CharField(max_length=80, unique=True)
    course_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    term_id = models.CharField(max_length=20, db_index=True)
    primary_id = models.CharField(max_length=80, null=True)
    xlist_id = models.CharField(max_length=80, null=True)
    added_date = models.DateTimeField(auto_now_add=True)
    provisioned_date = models.DateTimeField(null=True)
    provisioned_error = models.NullBooleanField()
    provisioned_status = models.CharField(max_length=512, null=True)
    priority = models.SmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = CourseManager()

    def is_sdb(self):
        return self.course_type == self.SDB_TYPE

    def is_adhoc(self):
        return self.course_type == self.ADHOC_TYPE

    def sws_url(self):
        try:
            (year, quarter, curr_abbr, course_num,
                section_id) = self.course_id.split('-', 4)
            sws_url = "%s/%s,%s,%s,%s/%s.json" % (
                "/restclients/view/sws/student/v5/course",
                year, quarter, curr_abbr, course_num, section_id)
        except ValueError:
            sws_url = None

        return sws_url

    def json_data(self, include_sws_url=False):
        try:
            group_models = Group.objects.filter(course_id=self.course_id,
                                                is_deleted__isnull=True)
            groups = list(group_models.values_list("group_id", flat=True))
        except Group.DoesNotExist:
            groups = []

        return {
            "course_id": self.course_id,
            "term_id": self.term_id,
            "xlist_id": self.xlist_id,
            "is_sdb_type": self.is_sdb(),
            "added_date": localtime(self.added_date).isoformat() if (
                self.added_date is not None) else None,
            "provisioned_date": localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date is not None) else None,
            "priority": PRIORITY_CHOICES[self.priority][1],
            "provisioned_error": self.provisioned_error,
            "provisioned_status": self.provisioned_status,
            "queue_id": self.queue_id,
            "groups": groups,
            "sws_url": self.sws_url() if (
                include_sws_url and self.is_sdb()) else None,
        }


class EnrollmentManager(models.Manager):
    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        filter_limit = settings.SIS_IMPORT_LIMIT['enrollment']['default']

        pks = super(EnrollmentManager, self).get_queryset().filter(
            priority=priority, queue_id__isnull=True
        ).order_by(
            'last_modified'
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='enrollment')
        imp.save()

        # Mark the enrollments as in process
        super(EnrollmentManager, self).get_queryset().filter(
            pk__in=list(pks)
        ).update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(EnrollmentManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        if provisioned_date is None:
            self.queued(queue_id).update(queue_id=None)
        else:
            super(EnrollmentManager, self).get_queryset().filter(
                queue_id=queue_id,
                priority=PRIORITY_DEFAULT
            ).update(
                priority=PRIORITY_NONE,
                queue_id=None
            )

            super(EnrollmentManager, self).get_queryset().filter(
                queue_id=queue_id,
                priority=PRIORITY_HIGH
            ).update(
                priority=PRIORITY_DEFAULT,
                queue_id=None
            )

    def add_enrollment(self, enrollment_data):
        section = enrollment_data.get('Section')
        reg_id = enrollment_data.get('UWRegID')
        role = enrollment_data.get('Role', Enrollment.STUDENT_ROLE)
        status = enrollment_data.get('Status').lower()
        last_modified = enrollment_data.get('LastModified')
        request_date = enrollment_data.get('RequestDate')
        instructor_reg_id = enrollment_data.get('InstructorUWRegID', None)

        course_id = '-'.join([section.term.canvas_sis_id(),
                              section.curriculum_abbr.upper(),
                              section.course_number,
                              section.section_id.upper()])

        primary_course_id = None
        if section.is_primary_section:
            primary_course_id = None
        else:
            primary_course_id = section.canvas_course_sis_id()

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
                    logger.info('Enrollment: UPDATE %s %s %s %s %s' % (
                        course_id, reg_id, role, status, last_modified))

                    enrollment.status = status
                    enrollment.last_modified = last_modified
                    enrollment.request_date = request_date
                    enrollment.primary_course_id = primary_course_id
                    enrollment.instructor_reg_id = instructor_reg_id

                    if enrollment.queue_id is None:
                        enrollment.priority = PRIORITY_DEFAULT
                    else:
                        enrollment.priority = PRIORITY_HIGH
                        logger.info('Enrollment: IN QUEUE %s %s %s %s' % (
                            course_id, reg_id, role, enrollment.queue_id))

                    enrollment.save()
                else:
                    logger.info('Enrollment: IGNORE %s %s, %s before %s' % (
                        course_id, reg_id, last_modified,
                        enrollment.last_modified))
            else:
                logger.info('Enrollment: IGNORE %s %s Unprovisioned course' % (
                    full_course_id, reg_id))
                course.priority = PRIORITY_HIGH
                course.save()

        except Enrollment.DoesNotExist:
            logger.info('Enrollment: ADD %s %s %s %s %s' % (
                course_id, reg_id, role, status, last_modified))
            enrollment = Enrollment(course_id=course_id, reg_id=reg_id,
                                    role=role, status=status,
                                    last_modified=last_modified,
                                    primary_course_id=primary_course_id,
                                    instructor_reg_id=instructor_reg_id)
            enrollment.save()
        except Course.DoesNotExist:
            # course provisioning effectively picks up event
            logger.info('Enrollment: IGNORE %s %s Unprovisioned course' % (
                full_course_id, reg_id))

            if section.is_independent_study:
                section.independent_study_instructor_regid = instructor_reg_id

            course = Course(course_id=full_course_id,
                            course_type=Course.SDB_TYPE,
                            term_id=section.term.canvas_sis_id(),
                            primary_id=primary_course_id,
                            priority=PRIORITY_HIGH)
            course.save()


class Enrollment(models.Model):
    """ Represents the provisioned state of an enrollment.
    """
    ACTIVE_STATUS = "active"
    INACTIVE_STATUS = "inactive"
    DELETED_STATUS = "deleted"
    COMPLETED_STATUS = "completed"

    STATUS_CHOICES = (
        (ACTIVE_STATUS, "Active"),
        (INACTIVE_STATUS, "Inactive"),
        (DELETED_STATUS, "Deleted"),
        (COMPLETED_STATUS, "Completed")
    )

    STUDENT_ROLE = "Student"
    AUDITOR_ROLE = "Auditor"
    INSTRUCTOR_ROLE = "Teacher"

    ROLE_CHOICES = (
        (STUDENT_ROLE, "Student"),
        (INSTRUCTOR_ROLE, "Teacher"),
        (AUDITOR_ROLE, "Auditor")
    )

    reg_id = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    course_id = models.CharField(max_length=80)
    last_modified = models.DateTimeField()
    request_date = models.DateTimeField(null=True)
    primary_course_id = models.CharField(max_length=80, null=True)
    instructor_reg_id = models.CharField(max_length=32, null=True)
    priority = models.SmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = EnrollmentManager()

    def is_active(self):
        return self.status == self.ACTIVE_STATUS

    def is_student(self):
        return self.role == self.STUDENT_ROLE

    def is_instructor(self):
        return self.role == self.INSTRUCTOR_ROLE

    def is_auditor(self):
        return self.role == self.AUDITOR_ROLE

    def json_data(self):
        return {
            "reg_id": self.reg_id,
            "status": self.status,
            "course_id": self.course_id,
            "last_modified": localtime(self.last_modified).isoformat() if (
                self.last_modified is not None) else None,
            "request_date": localtime(self.request_date).isoformat() if (
                self.request_date is not None) else None,
            "primary_course_id": self.primary_course_id,
            "instructor_reg_id": self.instructor_reg_id,
            "role": self.role,
            "priority": PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    class Meta:
        unique_together = ("course_id", "reg_id", "role")


class UserManager(models.Manager):
    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        if priority > PRIORITY_DEFAULT:
            filter_limit = settings.SIS_IMPORT_LIMIT['user']['high']
        else:
            filter_limit = settings.SIS_IMPORT_LIMIT['user']['default']

        pks = super(UserManager, self).get_queryset().filter(
            priority=priority, queue_id__isnull=True
        ).order_by(
            'provisioned_date', 'added_date'
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='user')
        imp.save()

        # Mark the users as in process, and reset the priority
        super(UserManager, self).get_queryset().filter(
            pk__in=list(pks)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queued(self, queue_id):
        return super(UserManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        kwargs = {'queue_id': None}
        if provisioned_date is not None:
            kwargs['provisioned_date'] = provisioned_date
            kwargs['priority'] = PRIORITY_DEFAULT

        self.queued(queue_id).update(**kwargs)

    def add_all_users(self):
        existing_netids = dict((u, p) for u, p in (
            super(UserManager, self).get_queryset().values_list(
                'net_id', 'priority')))

        for member in get_sis_import_members():
            if (member.name not in existing_netids or
                    existing_netids[member.name] == PRIORITY_NONE):
                try:
                    self.add_user(get_person_by_netid(member.name),
                                  priority=PRIORITY_HIGH)
                    existing_netids[member.name] = PRIORITY_HIGH
                except Exception as err:
                    logger.info('User: SKIP %s, %s' % (member.name, err))

    def add_user(self, person, priority=PRIORITY_DEFAULT):
        if person.uwnetid is None or person.uwregid is None:
            logger.info('User: SKIP uwnetid: %s, uwregid: %s' % (
                person.uwnetid, person.uwregid))
            return

        users = super(UserManager, self).get_queryset().filter(
            models.Q(reg_id=person.uwregid) | models.Q(net_id=person.uwnetid))

        user = None
        if len(users) == 1:
            user = users[0]
        elif len(users) > 1:
            users.delete()

        if user is None:
            user = User()

        if (user.reg_id != person.uwregid or user.net_id != person.uwnetid or
                user.priority < priority):
            user.reg_id = person.uwregid
            user.net_id = person.uwnetid
            if user.priority < priority:
                user.priority = priority
            user.save()

        return user


class User(models.Model):
    """ Represents the provisioned state of a user.
    """
    net_id = models.CharField(max_length=20, unique=True)
    reg_id = models.CharField(max_length=32, unique=True)
    added_date = models.DateTimeField(auto_now_add=True)
    provisioned_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = UserManager()

    def json_data(self):
        return {
            "net_id": self.net_id,
            "reg_id": self.reg_id,
            "added_date": localtime(self.added_date).isoformat(),
            "provisioned_date": localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date is not None) else None,
            "priority": PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }


class GroupManager(models.Manager):
    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        filter_limit = settings.SIS_IMPORT_LIMIT['group']['default']

        course_ids = super(GroupManager, self).get_queryset().filter(
            priority=priority, queue_id__isnull=True
        ).order_by(
            'provisioned_date'
        ).values_list('course_id', flat=True)[:filter_limit]

        if not len(course_ids):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='group')
        imp.save()

        # Mark the groups as in process, and reset the priority
        super(GroupManager, self).get_queryset().filter(
            course_id__in=list(course_ids)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queue_by_modified_date(self, modified_since):
        filter_limit = settings.SIS_IMPORT_LIMIT['group']['default']

        groups = super(GroupManager, self).get_queryset().filter(
            queue_id__isnull=True
        ).exclude(
            priority=PRIORITY_NONE
        ).order_by('-priority', 'provisioned_date')

        group_ids = set()
        course_ids = set()
        for group in groups:
            if group.group_id not in group_ids:
                group_ids.add(group.group_id)

                mod_group_ids = []
                if is_modified_group(group.group_id, modified_since):
                    mod_group_ids.append(group.group_id)
                else:
                    for membergroup in GroupMemberGroup.objects.filter(
                            root_group_id=group.group_id,
                            is_deleted__isnull=True):
                        if is_modified_group(membergroup.group_id,
                                             modified_since):
                            group_ids.add(membergroup.group_id)
                            mod_group_ids.append(membergroup.group_id)
                            mod_group_ids.append(group.group_id)
                            break

                for mod_group_id in mod_group_ids:
                    course_ids.update(set(groups.filter(
                        group_id=mod_group_id
                    ).values_list('course_id', flat=True)))

                if len(course_ids) >= filter_limit:
                    break

        if not len(course_ids):
            raise EmptyQueueException()

        imp = Import(priority=PRIORITY_DEFAULT, csv_type='group')
        imp.save()

        # Mark the groups as in process, and reset the priority
        super(GroupManager, self).get_queryset().filter(
            course_id__in=list(course_ids)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queued(self, queue_id):
        return super(GroupManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        kwargs = {'queue_id': None}
        if provisioned_date is not None:
            kwargs['provisioned_date'] = provisioned_date
            kwargs['priority'] = PRIORITY_DEFAULT

        self.queued(queue_id).update(**kwargs)

    def dequeue_course(self, course_id):
        super(GroupManager, self).get_queryset().filter(
            course_id=course_id
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=None
        )

    def deprioritize_course(self, course_id):
        super(GroupManager, self).get_queryset().filter(
            course_id=course_id
        ).update(
            priority=PRIORITY_NONE, queue_id=None
        )


class Group(models.Model):
    """ Represents the provisioned state of a course group
    """
    course_id = models.CharField(max_length=80)
    group_id = models.CharField(max_length=256)
    role = models.CharField(max_length=80)
    added_by = models.CharField(max_length=20)
    added_date = models.DateTimeField(auto_now_add=True, null=True)
    is_deleted = models.NullBooleanField()
    deleted_by = models.CharField(max_length=20, null=True)
    deleted_date = models.DateTimeField(null=True)
    provisioned_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = GroupManager()

    def json_data(self):
        return {
            "id": self.pk,
            "group_id": self.group_id,
            "course_id": self.course_id,
            "role": self.role,
            "added_by": self.added_by,
            "added_date": localtime(self.added_date).isoformat(),
            "is_deleted": True if self.is_deleted else None,
            "deleted_date": localtime(self.deleted_date).isoformat() if (
                self.deleted_date is not None) else None,
            "provisioned_date": localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date is not None) else None,
            "priority": PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    class Meta:
        unique_together = ('course_id', 'group_id', 'role')


class GroupMemberGroup(models.Model):
    """ Represents member group relationship
    """
    group_id = models.CharField(max_length=256)
    root_group_id = models.CharField(max_length=256)
    is_deleted = models.NullBooleanField()


class CourseMemberManager(models.Manager):
    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        filter_limit = settings.SIS_IMPORT_LIMIT['coursemember']['default']

        pks = super(CourseMemberManager, self).get_queryset().filter(
            priority=priority, queue_id__isnull=True
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='coursemember')
        imp.save()

        # Mark the coursemembers as in process, and reset the priority
        super(CourseMemberManager, self).get_queryset().filter(
            pk__in=list(pks)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queued(self, queue_id):
        return super(CourseMemberManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        if provisioned_date is None:
            self.queued(queue_id).update(queue_id=None)
        else:
            super(CourseMemberManager, self).get_queryset().filter(
                queue_id=queue_id,
                priority=PRIORITY_DEFAULT
            ).update(
                priority=PRIORITY_NONE,
                queue_id=None
            )

            super(CourseMemberManager, self).get_queryset().filter(
                queue_id=queue_id,
                priority=PRIORITY_HIGH
            ).update(
                priority=PRIORITY_DEFAULT,
                queue_id=None
            )


class CourseMember(models.Model):
    UWNETID_TYPE = "uwnetid"
    EPPN_TYPE = "eppn"

    TYPE_CHOICES = (
        (UWNETID_TYPE, "UWNetID"),
        (EPPN_TYPE, "ePPN")
    )

    course_id = models.CharField(max_length=80)
    name = models.CharField(max_length=256)
    member_type = models.SlugField(max_length=16, choices=TYPE_CHOICES)
    role = models.CharField(max_length=80)
    is_deleted = models.NullBooleanField()
    deleted_date = models.DateTimeField(null=True, blank=True)
    priority = models.SmallIntegerField(default=0, choices=PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = CourseMemberManager()

    def is_uwnetid(self):
        return self.member_type.lower() == self.UWNETID_TYPE

    def is_eppn(self):
        return self.member_type.lower() == self.EPPN_TYPE

    def __eq__(self, other):
        return (self.course_id == other.course_id and
                self.name.lower() == other.name.lower() and
                self.member_type.lower() == other.member_type.lower() and
                self.role.lower() == other.role.lower())


class CurriculumManager(models.Manager):
    def queued(self, queue_id):
        return super(CurriculumManager, self).get_queryset()

    def dequeue(self, queue_id, provisioned_date=None):
        pass

    def canvas_account_id(self, section):
        course_id = section.canvas_course_sis_id()
        try:
            curr_abbr = section.curriculum_abbr
            curriculum = Curriculum.objects.get(curriculum_abbr=curr_abbr)
            account_id = curriculum.subaccount_id
        except Curriculum.DoesNotExist:
            account_id = None

        lms_owner_accounts = getattr(settings, 'LMS_OWNERSHIP_SUBACCOUNT', {})
        try:
            account_id = lms_owner_accounts[section.lms_ownership]
        except (AttributeError, KeyError):
            if account_id is None and section.course_campus == 'PCE':
                account_id = lms_owner_accounts['PCE_NONE']

        try:
            override = SubAccountOverride.objects.get(course_id=course_id)
            account_id = override.subaccount_id
        except SubAccountOverride.DoesNotExist:
            pass

        if account_id is None:
            raise CoursePolicyException("No account_id for %s" % course_id)

        return account_id


class Curriculum(models.Model):
    """ Maps curricula to sub-account IDs
    """
    curriculum_abbr = models.SlugField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    subaccount_id = models.CharField(max_length=100, unique=True)

    objects = CurriculumManager()


class Import(models.Model):
    """ Represents a set of files that have been queued for import.
    """
    CSV_TYPE_CHOICES = (
        ('account', 'Curriculum'),
        ('user', 'User'),
        ('course', 'Course'),
        ('unused_course', 'Term'),
        ('coursemember', 'CourseMember'),
        ('enrollment', 'Enrollment'),
        ('group', 'Group')
    )

    csv_type = models.SlugField(max_length=20, choices=CSV_TYPE_CHOICES)
    csv_path = models.CharField(max_length=80, null=True)
    csv_errors = models.TextField(null=True)
    added_date = models.DateTimeField(auto_now_add=True)
    priority = models.SmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    post_status = models.SmallIntegerField(null=True)
    monitor_date = models.DateTimeField(null=True)
    monitor_status = models.SmallIntegerField(null=True)
    canvas_id = models.CharField(max_length=30, null=True)
    canvas_state = models.CharField(max_length=80, null=True)
    canvas_progress = models.SmallIntegerField(default=0)
    canvas_errors = models.TextField(null=True)

    def json_data(self):
        return {
            "queue_id": self.pk,
            "type": self.csv_type,
            "type_name": self.get_csv_type_display(),
            "added_date": localtime(self.added_date).isoformat(),
            "priority": PRIORITY_CHOICES[self.priority][1],
            "csv_errors": self.csv_errors,
            "post_status": self.post_status,
            "canvas_state": self.canvas_state,
            "canvas_progress": self.canvas_progress,
            "canvas_errors": self.canvas_errors,
        }

    def import_csv(self):
        """
        Imports all csv files for the passed import object, as a zipped
        archive.
        """
        if not self.csv_path:
            raise MissingImportPathException()

        try:
            sis_import = sis_import_by_path(self.csv_path)
            self.post_status = 200
            self.canvas_id = sis_import.import_id
            self.canvas_state = sis_import.workflow_state
        except DataFailureException as ex:
            self.post_status = ex.status
            self.canvas_errors = ex
        except Exception as ex:
            self.canvas_errors = ex

        self.save()

    def update_import_status(self):
        """
        Updates import attributes, based on the sis import resource.
        """
        if (self.canvas_id and self.post_status == 200 and
                (self.canvas_errors is None or
                    self.monitor_status in [500, 503, 504])):
            self.monitor_date = datetime.utcnow().replace(tzinfo=utc)
            try:
                sis_import = get_sis_import_status(self.canvas_id)
                self.monitor_status = 200
                self.canvas_errors = None
                self.canvas_state = sis_import.workflow_state
                self.canvas_progress = sis_import.progress

                if len(sis_import.processing_warnings):
                    canvas_errors = json.dumps(sis_import.processing_warnings)
                    self.canvas_errors = canvas_errors

            except DataFailureException as ex:
                self.monitor_status = ex.status
                self.canvas_errors = ex

            if self.is_cleanly_imported():
                self.delete()
            else:
                self.save()
                if self.is_imported():
                    self.dequeue_dependent_models()

    def is_completed(self):
        return (self.post_status == 200 and
                self.canvas_progress == 100)

    def is_cleanly_imported(self):
        return (self.is_completed() and
                self.canvas_state == 'imported')

    def is_imported(self):
        return (self.is_completed() and
                re.match(r'^imported', self.canvas_state) is not None)

    def dependent_model(self):
        return globals()[self.get_csv_type_display()]

    def queued_objects(self):
        return self.dependent_model().objects.queued(self.pk)

    def dequeue_dependent_models(self):
        provisioned_date = self.monitor_date if self.is_imported() else None

        if self.csv_type != 'user' and self.csv_type != 'account':
            User.objects.dequeue(self.pk, provisioned_date)

        self.dependent_model().objects.dequeue(self.pk, provisioned_date)

    def delete(self, *args, **kwargs):
        self.dequeue_dependent_models()
        return super(Import, self).delete(*args, **kwargs)


class SubAccountOverride(models.Model):
    course_id = models.CharField(max_length=80)
    subaccount_id = models.CharField(max_length=100)
    reference_date = models.DateTimeField(auto_now_add=True)


class TermOverride(models.Model):
    course_id = models.CharField(max_length=80)
    term_sis_id = models.CharField(max_length=24)
    term_name = models.CharField(max_length=24)
    reference_date = models.DateTimeField(auto_now_add=True)
