# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db import models
from django.db.models import F, Q
from django.conf import settings
from django.utils.timezone import localtime
from sis_provisioner.dao.user import get_person_by_netid, is_group_member
from sis_provisioner.dao.group import get_sis_import_members
from sis_provisioner.dao.canvas import get_active_sis_enrollments_for_user
from sis_provisioner.models import Import, ImportResource
from sis_provisioner.exceptions import (
    MissingLoginIdException, EmptyQueueException)
from logging import getLogger

logger = getLogger(__name__)


class UserManager(models.Manager):
    def queue_by_priority(self, priority=ImportResource.PRIORITY_DEFAULT):
        filter_limit = settings.SIS_IMPORT_LIMIT['user']['default']
        kwargs = {'queue_id__isnull': True}

        if priority == ImportResource.PRIORITY_IMMEDIATE:
            kwargs['priority'] = priority
        else:
            kwargs['priority__in'] = [
                ImportResource.PRIORITY_DEFAULT, ImportResource.PRIORITY_HIGH]

        pks = super().get_queryset().filter(**kwargs).order_by(
            F('priority').desc(),
            F('provisioned_date').asc(nulls_first=True)
        ).values_list('pk', flat=True)[:filter_limit]

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(csv_type='user', priority=priority)
        imp.override_sis_stickiness = True
        imp.save()

        super().get_queryset().filter(
            pk__in=list(pks)).update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super().get_queryset().filter(queue_id=queue_id)

    def dequeue(self, sis_import):
        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            kwargs['provisioned_date'] = sis_import.monitor_date
            kwargs['priority'] = User.PRIORITY_DEFAULT

        self.queued(sis_import.pk).update(**kwargs)

    def add_all_users(self):
        existing_netids = dict((u, p) for u, p in (
            super().get_queryset().values_list('net_id', 'priority')))

        for member in get_sis_import_members():
            if (member.name not in existing_netids or
                    existing_netids[member.name] == User.PRIORITY_NONE):
                try:
                    user = self.add_user_by_netid(member.name)
                    existing_netids[member.name] = user.priority
                except Exception as err:
                    logger.info('User: SKIP {}, {}'.format(member.name, err))

    def _find_existing(self, net_id, reg_id):
        if net_id is None:
            raise MissingLoginIdException()

        users = super().get_queryset().filter(
            models.Q(reg_id=reg_id) | models.Q(net_id=net_id))

        user = None
        if len(users) == 1:
            user = users[0]
        elif len(users) > 1:
            users.delete()
            user = User(net_id=net_id,
                        reg_id=reg_id,
                        priority=User.PRIORITY_HIGH)
            user.save()

        return user

    def update_priority(self, person, priority):
        user = self._find_existing(person.uwnetid, person.uwregid)

        if (user is not None and user.priority != priority):
            user.priority = priority
            user.save()

        return user

    def get_user(self, person):
        user = self._find_existing(person.uwnetid, person.uwregid)

        if user is None:
            user = self.add_user(person)

        return user

    def add_user(self, person, priority=ImportResource.PRIORITY_HIGH):
        user = self._find_existing(person.uwnetid, person.uwregid)

        if user is None:
            user = User()

        if (user.reg_id != person.uwregid or user.net_id != person.uwnetid or
                user.priority != priority):
            user.reg_id = person.uwregid
            user.net_id = person.uwnetid
            user.priority = priority
            user.save()

        return user

    def add_user_by_netid(self, net_id, priority=ImportResource.PRIORITY_HIGH):
        return self.add_user(get_person_by_netid(net_id), priority=priority)

    def get_invalid_enrollment_check_users(self):
        filter_limit = settings.SIS_IMPORT_LIMIT['user']['default']
        return super().get_queryset().filter(
            invalid_enrollment_check_required=True,
            provisioned_date__isnull=False)[:filter_limit]


class User(ImportResource):
    """ Represents the provisioned state of a user.
    """
    net_id = models.CharField(max_length=80, unique=True)
    reg_id = models.CharField(max_length=32, unique=True)
    added_date = models.DateTimeField(auto_now_add=True)
    provisioned_date = models.DateTimeField(null=True)
    invalid_enrollment_check_required = models.BooleanField(default=False)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = UserManager()

    def json_data(self):
        return {
            "net_id": self.net_id,
            "reg_id": self.reg_id,
            "added_date": localtime(self.added_date).isoformat(),
            "provisioned_date": localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date) else None,
            "priority": self.PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    def get_active_sis_enrollments(self, roles=[]):
        return get_active_sis_enrollments_for_user(self.reg_id, roles=roles)

    def is_student_user(self):
        return is_group_member(
            getattr(settings, 'ALLOWED_CANVAS_STUDENT_USERS'), self.net_id)

    def is_affiliate_user(self):
        return is_group_member(
            getattr(settings, 'ALLOWED_CANVAS_AFFILIATE_USERS'), self.net_id)

    def is_sponsored_user(self):
        return is_group_member(
            getattr(settings, 'ALLOWED_CANVAS_SPONSORED_USERS'), self.net_id)
