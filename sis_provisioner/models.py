from django.db import models
from django.conf import settings
from django.utils.timezone import utc, localtime
from restclients.canvas.sis_import import SISImport
from restclients.models.canvas import SISImport as SISImportModel
from restclients.gws import GWS
from restclients.exceptions import DataFailureException
from eos.models import EOSCourseDelta
import datetime
import json
import re


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


class EmptyQueueException(Exception):
    pass


class MissingImportPathException(Exception):
    pass


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
            'last_status_date': localtime(self.last_status_date).isoformat() if (
                self.last_status_date is not None) else None,
        }


class CourseManager(models.Manager):
    def get_linked_course_ids(self, course_id):
        return super(CourseManager, self).get_query_set().filter(
            primary_id=course_id).values_list('course_id', flat=True)

    def get_joint_course_ids(self, course_id):
        return super(CourseManager, self).get_query_set().filter(
            xlist_id=course_id).exclude(course_id=course_id).values_list(
                'course_id', flat=True)

    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        if priority > PRIORITY_DEFAULT:
            filter_limit = settings.SIS_IMPORT_LIMIT['course']['high']
        else:
            filter_limit = settings.SIS_IMPORT_LIMIT['course']['default']

        pks = super(CourseManager, self).get_query_set().filter(
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
        super(CourseManager, self).get_query_set().filter(
            pk__in=list(pks)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queued(self, queue_id):
        return super(CourseManager, self).get_query_set().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        kwargs = {'queue_id': None}
        if provisioned_date is not None:
            kwargs['provisioned_date'] = provisioned_date
            kwargs['priority'] = PRIORITY_DEFAULT

        self.queued(queue_id).update(**kwargs)


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


class Instructor(models.Model):
    """ Represents the provisioned state of a course instructor.
    """
    section_id = models.CharField(max_length=80)
    reg_id = models.CharField(max_length=32)

    class Meta:
        unique_together = ('section_id', 'reg_id')

    def __eq__(self, other):
        return (self.section_id == other.section_id and
                self.reg_id == other.reg_id)


class EnrollmentManager(models.Manager):
    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        filter_limit = settings.SIS_IMPORT_LIMIT['enrollment']['default']

        pks = super(EnrollmentManager, self).get_query_set().filter(
            priority=priority, queue_id__isnull=True
        ).order_by(
            'last_modified'
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='enrollment')
        imp.save()

        # Mark the enrollments as in process
        super(EnrollmentManager, self).get_query_set().filter(
            pk__in=list(pks)
        ).update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(EnrollmentManager, self).get_query_set().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        if provisioned_date is None:
            self.queued(queue_id).update(queue_id=None)
        else:
            super(EnrollmentManager, self).get_query_set().filter(
                queue_id=queue_id,
                priority=PRIORITY_DEFAULT
            ).update(
                priority=PRIORITY_NONE,
                queue_id=None
            )

            super(EnrollmentManager, self).get_query_set().filter(
                queue_id=queue_id,
                priority=PRIORITY_HIGH
            ).update(
                priority=PRIORITY_DEFAULT,
                queue_id=None
            )


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

    reg_id = models.CharField(max_length=32, null=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    course_id = models.CharField(max_length=80)
    last_modified = models.DateTimeField()
    primary_course_id = models.CharField(max_length=80, null=True)
    instructor_reg_id = models.CharField(max_length=32, null=True)
    priority = models.SmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = EnrollmentManager()

    def is_active(self):
        return self.status == self.ACTIVE_STATUS

    def json_data(self):
        return {
            "reg_id": self.reg_id,
            "status": self.status,
            "course_id": self.course_id,
            "last_modified": localtime(self.last_modified).isoformat() if (
                self.last_modified is not None) else None,
            "primary_course_id": self.primary_course_id,
            "instructor_reg_id": self.instructor_reg_id,
            "priority": PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    class Meta:
        unique_together = ("course_id", "reg_id")


class UserManager(models.Manager):
    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        if priority > PRIORITY_DEFAULT:
            filter_limit = settings.SIS_IMPORT_LIMIT['user']['high']
        else:
            filter_limit = settings.SIS_IMPORT_LIMIT['user']['default']

        pks = super(UserManager, self).get_query_set().filter(
            priority=priority, queue_id__isnull=True
        ).order_by(
            'provisioned_date', 'added_date'
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='user')
        imp.save()

        # Mark the users as in process, and reset the priority
        super(UserManager, self).get_query_set().filter(
            pk__in=list(pks)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queued(self, queue_id):
        return super(UserManager, self).get_query_set().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        kwargs = {'queue_id': None}
        if provisioned_date is not None:
            kwargs['provisioned_date'] = provisioned_date
            kwargs['priority'] = PRIORITY_DEFAULT

        self.queued(queue_id).update(**kwargs)


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

        course_ids = super(GroupManager, self).get_query_set().filter(
            priority=priority, queue_id__isnull=True
        ).order_by(
            'provisioned_date'
        ).values_list('course_id', flat=True)[:filter_limit]

        if not len(course_ids):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='group')
        imp.save()

        # Mark the groups as in process, and reset the priority
        super(GroupManager, self).get_query_set().filter(
            course_id__in=list(course_ids)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queue_by_modified_date(self, modified_since):
        filter_limit = settings.SIS_IMPORT_LIMIT['group']['default']

        groups = super(GroupManager, self).get_query_set().filter(
            queue_id__isnull=True
        ).order_by('-priority', 'provisioned_date')

        group_ids = set()
        course_ids = set()
        self._gws = GWS()
        for group in groups:
            if group.group_id not in group_ids:
                group_ids.add(group.group_id)

                mod_group_ids = []
                if self._is_modified_group(group.group_id, modified_since):
                    mod_group_ids.append(group.group_id)
                else:
                    for membergroup in GroupMemberGroup.objects.filter(
                            root_group_id=group.group_id,
                            is_deleted__isnull=True):
                        if self._is_modified_group(membergroup.group_id,
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
        super(GroupManager, self).get_query_set().filter(
            course_id__in=list(course_ids)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def _is_modified_group(self, group_id, mtime):
        try:
            group = self._gws.get_group_by_id(group_id)
            return (group.membership_modified > mtime)
        except DataFailureException as err:
            if err.status == 404:   # deleted group?
                return True
            else:
                raise

    def queued(self, queue_id):
        return super(GroupManager, self).get_query_set().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        kwargs = {'queue_id': None}
        if provisioned_date is not None:
            kwargs['provisioned_date'] = provisioned_date
            kwargs['priority'] = PRIORITY_DEFAULT

        self.queued(queue_id).update(**kwargs)


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

        pks = super(CourseMemberManager, self).get_query_set().filter(
            priority=priority, queue_id__isnull=True
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='coursemember')
        imp.save()

        # Mark the coursemembers as in process, and reset the priority
        super(CourseMemberManager, self).get_query_set().filter(
            pk__in=list(pks)
        ).update(
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def queued(self, queue_id):
        return super(CourseMemberManager, self).get_query_set().filter(
            queue_id=queue_id)

    def dequeue(self, queue_id, provisioned_date=None):
        if provisioned_date is None:
            self.queued(queue_id).update(queue_id=None)
        else:
            super(CourseMemberManager, self).get_query_set().filter(
                queue_id=queue_id,
                priority=PRIORITY_DEFAULT
            ).update(
                priority=PRIORITY_NONE,
                queue_id=None
            )

            super(CourseMemberManager, self).get_query_set().filter(
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
        return super(CurriculumManager, self).get_query_set()

    def dequeue(self, queue_id, provisioned_date=None):
        pass


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
        ('coursemember', 'CourseMember'),
        ('enrollment', 'Enrollment'),
        ('group', 'Group'),
        ('eoscourse', 'EOSCourseDelta')
    )

    csv_type = models.SlugField(max_length=20, choices=CSV_TYPE_CHOICES)
    csv_path = models.CharField(max_length=80, null=True)
    csv_errors = models.TextField(null=True)
    added_date = models.DateTimeField(auto_now_add=True)
    priority = models.SmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    post_status = models.SmallIntegerField(max_length=3, null=True)
    monitor_date = models.DateTimeField(null=True)
    monitor_status = models.SmallIntegerField(max_length=3, null=True)
    canvas_id = models.CharField(max_length=30, null=True)
    canvas_state = models.CharField(max_length=80, null=True)
    canvas_progress = models.SmallIntegerField(max_length=3, default=0)
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
            sis_import = SISImport().import_dir(self.csv_path)
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
            self.monitor_date = datetime.datetime.utcnow().replace(tzinfo=utc)
            try:
                sis_import = SISImport().get_import_status(
                    SISImportModel(import_id=str(self.canvas_id)))
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
