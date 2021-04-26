# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models, IntegrityError
from django.db.models import F
from django.conf import settings
from django.utils.timezone import utc, localtime
from sis_provisioner.models import Import, ImportResource
from sis_provisioner.models.course import Course
from sis_provisioner.models.user import User
from sis_provisioner.dao.term import is_active_term
from sis_provisioner.dao.canvas import ENROLLMENT_ACTIVE, INSTRUCTOR_ENROLLMENT
from sis_provisioner.exceptions import EmptyQueueException
from datetime import datetime, timedelta
from logging import getLogger

logger = getLogger(__name__)
enrollment_log_prefix = 'ENROLLMENT:'


class EnrollmentManager(models.Manager):
    def queue_by_priority(self, priority=ImportResource.PRIORITY_DEFAULT):
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

        super(EnrollmentManager, self).get_queryset().filter(
            pk__in=list(pks)).update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(EnrollmentManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        Course.objects.dequeue(sis_import)
        if sis_import.is_imported():
            # Decrement the priority
            super(EnrollmentManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=Enrollment.PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)

        self.purge_expired()

    def purge_expired(self):
        retention_dt = datetime.utcnow().replace(tzinfo=utc) - timedelta(
            days=getattr(settings, 'ENROLLMENT_EVENT_RETENTION_DAYS', 180))
        return super(EnrollmentManager, self).get_queryset().filter(
            priority=Enrollment.PRIORITY_NONE,
            last_modified__lt=retention_dt).delete()

    def add_enrollment(self, enrollment_data):
        section = enrollment_data.get('Section')
        reg_id = enrollment_data.get('UWRegID')
        role = enrollment_data.get('Role')
        status = enrollment_data.get('Status').lower()
        last_modified = enrollment_data.get('LastModified').replace(tzinfo=utc)
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
                        status == ENROLLMENT_ACTIVE)):
                    enrollment.status = status
                    enrollment.last_modified = last_modified
                    enrollment.request_date = request_date
                    enrollment.primary_course_id = primary_course_id
                    enrollment.instructor_reg_id = instructor_reg_id

                    if enrollment.queue_id is None:
                        enrollment.priority = enrollment.PRIORITY_DEFAULT
                    else:
                        enrollment.priority = enrollment.PRIORITY_HIGH
                        logger.info('{} IN QUEUE {}, {}, {}, {}'.format(
                            enrollment_log_prefix, full_course_id, reg_id,
                            role, enrollment.queue_id))

                    enrollment.save()
                    logger.info('{} UPDATE {}, {}, {}, {}, {}'.format(
                        enrollment_log_prefix, full_course_id, reg_id, role,
                        status, last_modified))
                else:
                    logger.info('{} IGNORE {}, {}, {} before {}'.format(
                        enrollment_log_prefix, full_course_id, reg_id,
                        last_modified, enrollment.last_modified))

            else:
                logger.info('{} IGNORE Unprovisioned course {}, {}, {}'.format(
                    enrollment_log_prefix, full_course_id, reg_id, role))
                course.priority = course.PRIORITY_HIGH
                course.save()

        except Enrollment.DoesNotExist:
            enrollment = Enrollment(course_id=course_id, reg_id=reg_id,
                                    role=role, status=status,
                                    last_modified=last_modified,
                                    primary_course_id=primary_course_id,
                                    instructor_reg_id=instructor_reg_id)
            try:
                enrollment.save()
                logger.info('{} ADD {}, {}, {}, {}, {}'.format(
                    enrollment_log_prefix, full_course_id, reg_id, role,
                    status, last_modified))
            except IntegrityError:
                self.add_enrollment(enrollment_data)  # Try again
        except Course.DoesNotExist:
            if is_active_term(section.term):
                # Initial course provisioning effectively picks up event
                course = Course(course_id=full_course_id,
                                course_type=Course.SDB_TYPE,
                                term_id=section.term.canvas_sis_id(),
                                primary_id=primary_course_id,
                                priority=Course.PRIORITY_HIGH)
                try:
                    course.save()
                    logger.info(
                        '{} IGNORE Unprovisioned course {}, {}, {}'.format(
                            enrollment_log_prefix, full_course_id, reg_id,
                            role))
                except IntegrityError:
                    self.add_enrollment(enrollment_data)  # Try again
            else:
                logger.info('{} IGNORE Inactive section {}, {}, {}'.format(
                    enrollment_log_prefix, full_course_id, reg_id, role))


class Enrollment(ImportResource):
    """ Represents the provisioned state of an enrollment.
    """
    reg_id = models.CharField(max_length=32)
    status = models.CharField(max_length=16)
    role = models.CharField(max_length=32)
    course_id = models.CharField(max_length=80)
    last_modified = models.DateTimeField()
    request_date = models.DateTimeField(null=True)
    primary_course_id = models.CharField(max_length=80, null=True)
    instructor_reg_id = models.CharField(max_length=32, null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = EnrollmentManager()

    def is_active(self):
        return self.status.lower() == ENROLLMENT_ACTIVE.lower()

    def is_instructor(self):
        return self.role.lower() == INSTRUCTOR_ENROLLMENT.lower()

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
            "priority": self.PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    class Meta:
        unique_together = ("course_id", "reg_id", "role")


class InvalidEnrollmentManager(models.Manager):
    def queue_by_priority(self, priority=ImportResource.PRIORITY_DEFAULT):
        filter_limit = settings.SIS_IMPORT_LIMIT['enrollment']['default']

        grace_period_dt = datetime.utcnow().replace(tzinfo=utc) - timedelta(
            days=getattr(settings, 'INVALID_ENROLLMENT_GRACE_DAYS', 90))

        pks = super(InvalidEnrollmentManager, self).get_queryset().filter(
            priority=priority, queue_id__isnull=True,
            found_date__lt=grace_period_dt
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='invalid_enrollment')
        imp.save()

        super(InvalidEnrollmentManager, self).get_queryset().filter(
            pk__in=list(pks)).update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(InvalidEnrollmentManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        if sis_import.is_imported():
            kwargs['queue_id'] = None
            kwargs['deleted_date'] = sis_import.monitor_date
            kwargs['priority'] = InvalidEnrollment.PRIORITY_NONE
            self.queued(sis_import.pk).update(**kwargs)

    def add_enrollments(self):
        check_roles = getattr(settings, 'ENROLLMENT_TYPES_INVALID_CHECK')
        for user in User.objects.get_invalid_enrollment_check_users():
            # Verify that the check conditions still exist
            if user.has_student_affiliation_only():
                for enr in user.get_active_sis_enrollments(roles=check_roles):
                    inv, created = InvalidEnrollment.objects.get_or_create(
                        user=user, role=enr.role, section_id=enr.sis_section_id
                    )
                    if inv.priority == InvalidEnrollment.PRIORITY_NONE:
                        inv.priority = InvalidEnrollment.PRIORITY_DEFAULT
                        # reset found_date?
                        inv.save()

            # Clear check flag
            user.invalid_enrollment_check_required = False
            user.save()


class InvalidEnrollment(ImportResource):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=32)
    section_id = models.CharField(max_length=80)
    found_date = models.DateTimeField(auto_now_add=True)
    deleted_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'role', 'section_id'],
                                    name='unique_enrollment')
        ]

    objects = InvalidEnrollmentManager()
