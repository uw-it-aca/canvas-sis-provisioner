# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db import models
from django.db.models import F
from django.conf import settings
from django.utils.timezone import localtime
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.group import is_modified_group
from sis_provisioner.models import Import, ImportResource
from sis_provisioner.models.user import User
from sis_provisioner.exceptions import (
    EmptyQueueException, GroupNotFoundException)
from datetime import datetime, timezone
from logging import getLogger

logger = getLogger(__name__)


class GroupManager(models.Manager):
    def queue_by_priority(self, priority=ImportResource.PRIORITY_DEFAULT):
        if priority > ImportResource.PRIORITY_DEFAULT:
            filter_limit = settings.SIS_IMPORT_LIMIT['group']['high']
        else:
            filter_limit = settings.SIS_IMPORT_LIMIT['group']['default']

        course_ids = super(GroupManager, self).get_queryset().filter(
            priority=priority, queue_id__isnull=True
        ).order_by(
            'provisioned_date'
        ).values_list('course_id', flat=True).distinct()[:filter_limit]

        if not len(course_ids):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='group')
        imp.save()

        # Mark the groups as in process, and reset the priority
        super(GroupManager, self).get_queryset().filter(
            course_id__in=list(course_ids)
        ).update(
            priority=ImportResource.PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def update_priority_by_modified_date(self):
        groups = super(GroupManager, self).get_queryset().filter(
            priority=Group.PRIORITY_DEFAULT, queue_id__isnull=True
        ).exclude(
            is_deleted=True, provisioned_date__gt=F('deleted_date')
        )

        group_ids = set()
        for group in groups:
            if group.group_id not in group_ids:
                group_ids.add(group.group_id)

                try:
                    is_mod = is_modified_group(
                        group.group_id,
                        group.provisioned_date or group.added_date)
                except GroupNotFoundException:
                    is_mod = True
                    self.delete_group_not_found(group.group_id)
                except DataFailureException as err:
                    is_mod = False
                    logger.info('Group: SKIP {}, {}'.format(
                        group.group_id, err))

                if is_mod:
                    group.update_priority(group.PRIORITY_HIGH)
                    continue
                else:
                    for mgroup in GroupMemberGroup.objects.get_active_by_root(
                            group.group_id):
                        if mgroup.group_id not in group_ids:
                            group_ids.add(mgroup.group_id)

                            try:
                                is_mod = is_modified_group(
                                    mgroup.group_id,
                                    group.provisioned_date or group.added_date)
                            except GroupNotFoundException:
                                is_mod = True
                                self.delete_group_not_found(mgroup.group_id)
                            except DataFailureException as err:
                                is_mod = False
                                logger.info('Group: SKIP {}, {}'.format(
                                    group.group_id, err))

                            if is_mod:
                                group.update_priority(group.PRIORITY_HIGH)
                                break

    def find_by_search(self, **kwargs):
        kwargs['is_deleted__isnull'] = True
        return super(GroupManager, self).get_queryset().filter(**kwargs)

    def get_active_by_group(self, group_id):
        return super(GroupManager, self).get_queryset().filter(
            group_id=group_id, priority__gt=Group.PRIORITY_NONE,
            is_deleted__isnull=True)

    def get_active_by_course(self, course_id):
        return super(GroupManager, self).get_queryset().filter(
            course_id=course_id, is_deleted__isnull=True)

    def queued(self, queue_id):
        return super(GroupManager, self).get_queryset().filter(
            queue_id=queue_id).order_by('course_id').values_list(
                'course_id', flat=True).distinct()

    def dequeue(self, sis_import):
        User.objects.dequeue(sis_import)
        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            kwargs['provisioned_date'] = sis_import.monitor_date
            kwargs['priority'] = Group.PRIORITY_DEFAULT

        self.queued(sis_import.pk).update(**kwargs)

    def dequeue_course(self, course_id):
        super(GroupManager, self).get_queryset().filter(
            course_id=course_id
        ).update(
            priority=Group.PRIORITY_DEFAULT, queue_id=None
        )

    def deprioritize_course(self, course_id):
        super(GroupManager, self).get_queryset().filter(
            course_id=course_id
        ).update(
            priority=Group.PRIORITY_NONE, queue_id=None
        )

    def update_group_id(self, old_group_id, new_group_id):
        super(GroupManager, self).get_queryset().filter(
            group_id=old_group_id).update(group_id=new_group_id)

    def delete_group_not_found(self, group_id):
        super(GroupManager, self).get_queryset().filter(
            group_id=group_id, is_deleted__isnull=True
        ).update(
            is_deleted=True, deleted_by='gws',
            deleted_date=datetime.now(timezone.utc)
        )


class Group(ImportResource):
    """ Represents the provisioned state of a course group
    """
    course_id = models.CharField(max_length=80)
    group_id = models.CharField(max_length=256)
    role = models.CharField(max_length=80)
    added_by = models.CharField(max_length=20)
    added_date = models.DateTimeField(auto_now_add=True, null=True)
    is_deleted = models.BooleanField(null=True)
    deleted_by = models.CharField(max_length=20, null=True)
    deleted_date = models.DateTimeField(null=True)
    provisioned_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = GroupManager()

    def update_priority(self, priority):
        for val, txt in self.PRIORITY_CHOICES:
            if val == priority:
                self.priority = val
                self.save()
                return

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
            "priority": self.PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    class Meta:
        unique_together = ('course_id', 'group_id', 'role')


class GroupMemberGroupManager(models.Manager):
    def get_active_by_group(self, group_id):
        return super(GroupMemberGroupManager, self).get_queryset().filter(
            group_id=group_id, is_deleted__isnull=True)

    def get_active_by_root(self, root_group_id):
        return super(GroupMemberGroupManager, self).get_queryset().filter(
            root_group_id=root_group_id, is_deleted__isnull=True)

    def update_group_id(self, old_group_id, new_group_id):
        super(GroupMemberGroupManager, self).get_queryset().filter(
            group_id=old_group_id).update(group_id=new_group_id)

    def update_root_group_id(self, old_group_id, new_group_id):
        super(GroupMemberGroupManager, self).get_queryset().filter(
            root_group_id=old_group_id).update(root_group_id=new_group_id)


class GroupMemberGroup(models.Model):
    """ Represents member group relationship
    """
    group_id = models.CharField(max_length=256)
    root_group_id = models.CharField(max_length=256)
    is_deleted = models.BooleanField(null=True)

    objects = GroupMemberGroupManager()

    def deactivate(self):
        self.is_deleted = True
        self.save()

    def activate(self):
        self.is_deleted = None
        self.save()
