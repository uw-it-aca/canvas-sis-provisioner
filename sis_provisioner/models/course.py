# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.timezone import localtime
from sis_provisioner.models import Import, ImportResource
from sis_provisioner.models.group import Group
from sis_provisioner.models.user import User
from sis_provisioner.models.term import Term
from sis_provisioner.dao.course import (
    valid_canvas_course_id, valid_course_sis_id, valid_canvas_section,
    get_new_sections_by_term)
from sis_provisioner.dao.canvas import create_course, delete_course
from sis_provisioner.dao.term import get_current_active_term
from sis_provisioner.exceptions import (
    CoursePolicyException, EmptyQueueException)
from restclients_core.exceptions import DataFailureException
from datetime import datetime, timedelta, timezone
from logging import getLogger

logger = getLogger(__name__)


class CourseManager(models.Manager):
    def find_course(self, canvas_course_id, sis_course_id):
        try:
            valid_canvas_course_id(canvas_course_id)
            valid_course_sis_id(sis_course_id)

            courses = super().get_queryset().filter(
                Q(canvas_course_id=canvas_course_id) |
                Q(course_id=sis_course_id))

            if len(courses) == 1:
                return courses[0]
            elif len(courses) > 1:
                raise Course.MultipleObjectsReturned()
            else:
                raise Course.DoesNotExist()
        except CoursePolicyException:
            try:
                valid_canvas_course_id(canvas_course_id)
                return Course.objects.get(canvas_course_id=canvas_course_id)
            except (CoursePolicyException, Course.DoesNotExist):
                try:
                    valid_course_sis_id(sis_course_id)
                    return Course.objects.get(course_id=sis_course_id)
                except CoursePolicyException:
                    pass
            raise Course.DoesNotExist()

    def create_user_course(self, sis_user_id, name, account_id=None,
                           sis_term_id=None):
        if not account_id:
            account_id = getattr(settings, 'ADHOC_COURSE_DEFAULT_ACCOUNT_ID')
        if not sis_term_id:
            term = get_current_active_term()
            sis_term_id = term.canvas_sis_id()

        canvas_course = create_course(
            sis_user_id, account_id, sis_term_id, name)

        course, _ = Course.objects.get_or_create(
            canvas_course_id=canvas_course.course_id, defaults={
                'course_id': canvas_course.sis_course_id,
                'course_type': Course.ADHOC_TYPE,
                'term_id': sis_term_id,
                'created_date': canvas_course.created_at,
                'priority': Course.PRIORITY_NONE,
            })
        return course

    def get_linked_course_ids(self, course_id):
        return super().get_queryset().filter(
            primary_id=course_id).values_list('course_id', flat=True)

    def get_joint_course_ids(self, course_id):
        return super().get_queryset().filter(
            xlist_id=course_id).exclude(course_id=course_id).values_list(
                'course_id', flat=True)

    def queue_by_priority(self, priority, term=None):
        filter_limit = settings.SIS_IMPORT_LIMIT['course']['default']
        kwargs = {
            'priority': priority,
            'course_type': Course.SDB_TYPE,
            'queue_id__isnull': True,
            'provisioned_error__isnull': True,
            'deleted_date__isnull': True
        }
        if term is not None:
            kwargs['term_id'] = term.canvas_sis_id()

        pks = super().get_queryset().filter(**kwargs).order_by(
            'provisioned_date', 'added_date'
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='course')
        imp.save()

        super().get_queryset().filter(pk__in=list(pks)).update(
            queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super().get_queryset().filter(queue_id=queue_id)

    def dequeue(self, sis_import):
        User.objects.dequeue(sis_import)

        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            kwargs['provisioned_date'] = sis_import.monitor_date
            kwargs['priority'] = Course.PRIORITY_DEFAULT

        self.queued(sis_import.pk).update(**kwargs)

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
                course.provisioned_status = 'Primary LMS: {} ({})'.format(
                    section.primary_lms, err)

            if section.is_withdrawn():
                course.priority = Course.PRIORITY_NONE

            course.save()
        except Course.DoesNotExist:
            pass

    def add_all_courses_for_term(self, term):
        term_id = term.canvas_sis_id()
        existing_course_ids = dict((c, p) for c, p in (
            super().get_queryset().filter(
                term_id=term_id, course_type=Course.SDB_TYPE
            ).values_list('course_id', 'priority')))

        last_search_date = datetime.now(timezone.utc)
        try:
            delta = Term.objects.get(term_id=term_id)
        except Term.DoesNotExist:
            delta = Term(term_id=term_id)

        if delta.last_course_search_date is None:
            delta.courses_changed_since_date = datetime.fromtimestamp(
                0, timezone.utc)
        else:
            delta.courses_changed_since_date = (
                delta.last_course_search_date - timedelta(days=1))

        new_courses = []
        for section_data in get_new_sections_by_term(
                localtime(delta.courses_changed_since_date).date(), term,
                existing=existing_course_ids):

            course_id = section_data['course_id']
            if course_id in existing_course_ids:
                if existing_course_ids[course_id] == Course.PRIORITY_NONE:
                    super().get_queryset().filter(course_id=course_id).update(
                        priority=Course.PRIORITY_DEFAULT)
                continue

            new_courses.append(Course(course_id=course_id,
                                      course_type=Course.SDB_TYPE,
                                      term_id=term_id,
                                      primary_id=section_data['primary_id'],
                                      priority=Course.PRIORITY_DEFAULT))

        Course.objects.bulk_create(new_courses)

        delta.last_course_search_date = last_search_date
        delta.save()

    def deprioritize_all_courses_for_term(self, term):
        super().get_queryset().filter(term_id=term.canvas_sis_id()).update(
            priority=Course.PRIORITY_NONE)


class Course(ImportResource):
    """ Represents the provisioned state of a course.
    """
    SDB_TYPE = 'sdb'
    ADHOC_TYPE = 'adhoc'
    TYPE_CHOICES = ((SDB_TYPE, 'SDB'), (ADHOC_TYPE, 'Ad Hoc'))
    RETENTION_EXPIRE_MONTH = 6
    RETENTION_EXPIRE_DAY = 30
    RETENTION_LIFE_SPAN = 5

    # sis_course_id
    course_id = models.CharField(max_length=80, null=True, db_index=True)
    canvas_course_id = models.CharField(max_length=10, null=True,
                                        db_index=True)
    course_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    term_id = models.CharField(max_length=30, db_index=True)
    primary_id = models.CharField(max_length=80, null=True)
    xlist_id = models.CharField(max_length=80, null=True)
    added_date = models.DateTimeField(auto_now_add=True)
    created_date = models.DateTimeField(null=True)
    provisioned_date = models.DateTimeField(null=True)
    provisioned_error = models.BooleanField(null=True)
    provisioned_status = models.CharField(max_length=512, null=True)
    expiration_date = models.DateTimeField(null=True)
    expiration_exc_granted_date = models.DateTimeField(null=True)
    expiration_exc_granted_by = models.ForeignKey(User, null=True,
                                                  on_delete=models.SET_NULL)
    expiration_exc_desc = models.CharField(max_length=200, null=True)
    deleted_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
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
            sws_url = (
                "/restclients/view/sws/student/v5/course/{year},{quarter},"
                "{curr_abbr},{course_num}/{section_id}.json").format(
                    year=year, quarter=quarter, curr_abbr=curr_abbr,
                    course_num=course_num, section_id=section_id)
        except ValueError:
            sws_url = None

        return sws_url

    def update_priority(self, priority):
        for key, val in self.PRIORITY_CHOICES:
            if val == priority:
                self.priority = key
                self.save()
                return

        raise CoursePolicyException("Invalid priority: '{}'".format(priority))

    @property
    def default_expiration_date(self):
        now = datetime.now(timezone.utc)
        expiration = datetime(
            now.year + self.RETENTION_LIFE_SPAN, self.RETENTION_EXPIRE_MONTH,
            self.RETENTION_EXPIRE_DAY, 12, 0, 0, tzinfo=timezone.utc)
        try:
            (year, quarter, c, n, s) = self.course_id.split('-')
            year = int(year) + self.RETENTION_LIFE_SPAN + (1 if (
                quarter.lower() in ['summer', 'autumn']) else 0)
            expiration = expiration.replace(year=year)
        except (AttributeError, ValueError):
            expiration = expiration.replace(
                year=self.created_date.year + self.RETENTION_LIFE_SPAN) if (
                    self.created_date) else expiration

        if expiration.year < now.year:
            expiration = expiration.replace(year=now.year)

        return expiration

    def is_expired(self):
        if self.expiration_date is not None:
            return self.expiration_date < datetime.now(timezone.utc)
        return False

    def json_data(self, include_sws_url=False):
        try:
            group_models = Group.objects.filter(course_id=self.course_id,
                                                is_deleted__isnull=True)
            groups = list(group_models.values_list("group_id", flat=True))
        except Group.DoesNotExist:
            groups = []

        return {
            "course_id": self.course_id,
            "canvas_course_id": self.canvas_course_id,
            "term_id": self.term_id,
            "primary_id": self.primary_id,
            "xlist_id": self.xlist_id,
            "is_sdb_type": self.is_sdb(),
            "added_date": localtime(self.added_date).isoformat() if (
                self.added_date is not None) else None,
            "provisioned_date": localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date is not None) else None,
            "created_date": localtime(self.created_date).isoformat() if (
                self.created_date is not None) else None,
            "deleted_date": localtime(self.deleted_date).isoformat() if (
                self.deleted_date is not None) else None,
            "is_expired": self.is_expired(),
            "expiration_date": localtime(self.expiration_date).isoformat() if (
                self.expiration_date is not None) else None,
            "expiration_exc_granted_date": localtime(
                self.expiration_exc_granted_date).isoformat() if (
                    self.expiration_exc_granted_date is not None) else None,
            "expiration_exc_granted_by": (
                self.expiration_exc_granted_by.net_id if (
                    self.expiration_exc_granted_by is not None) else None),
            "expiration_exc_desc": self.expiration_exc_desc,
            "priority": self.PRIORITY_CHOICES[self.priority][1],
            "provisioned_error": self.provisioned_error,
            "provisioned_status": self.provisioned_status,
            "queue_id": self.queue_id,
            "groups": groups,
            "sws_url": self.sws_url() if (
                include_sws_url and self.is_sdb()) else None,
        }


class UnusedCourseManager(models.Manager):
    def queue_unused_courses(self, term_id):
        try:
            term = Term.objects.get(term_id=term_id)
            if (term.deleted_unused_courses_date is not None or
                    term.queue_id is not None):
                raise EmptyQueueException()
        except Term.DoesNotExist:
            term = Term(term_id=term_id)
            term.save()

        imp = Import(priority=Course.PRIORITY_DEFAULT,
                     csv_type='unused_course')
        imp.save()

        term.queue_id = imp.pk
        term.save()

        return imp

    def queued(self, queue_id):
        return Course.objects.queued(queue_id)

    def dequeue(self, sis_import):
        Term.objects.dequeue(sis_import)

        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            kwargs['deleted_date'] = sis_import.monitor_date
            kwargs['priority'] = Course.PRIORITY_NONE

        self.queued(sis_import.pk).update(**kwargs)


class UnusedCourse(ImportResource):
    objects = UnusedCourseManager()

    class Meta:
        managed = False


class ExpiredCourseManager(models.Manager):
    def queued(self, queue_id):
        return Course.objects.queued(queue_id)

    def queued_sdb_courses(self, queue_id):
        return Course.objects.filter(
            queue_id=queue_id, course_type=Course.SDB_TYPE)

    def queued_adhoc_courses(self, queue_id):
        return Course.objects.filter(
            queue_id=queue_id, course_type=Course.ADHOC_TYPE)

    def dequeue(self, sis_import):
        if sis_import.is_imported():
            # Dequeue the sdb courses
            self.queued_sdb_courses(sis_import.pk).update(
                queue_id=None, priority=Course.PRIORITY_NONE,
                deleted_date=datetime.now(timezone.utc))

        # Delete the adhoc courses via the Canvas api
        for course in self.queued_adhoc_courses(sis_import.pk):
            try:
                delete_course(course.canvas_course_id)
                course.deleted_date = datetime.now(timezone.utc)
                logger.info(f"DELETE adhoc course '{course.canvas_course_id}'")
            except DataFailureException as err:
                course.provisioned_error = True
                course.provisioned_status = str(err)
                logger.info(f"DELETE adhoc course '{course.canvas_course_id}' "
                            f"error: {err}")

            course.queue_id = None
            course.priority = Course.PRIORITY_NONE
            course.save()


class ExpiredCourse(ImportResource):
    objects = ExpiredCourseManager()

    class Meta:
        managed = False
