# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.conf import settings
from django.utils.timezone import utc, localtime
from sis_provisioner.dao.astra import ASTRA
from sis_provisioner.dao.canvas import get_account_role_data
from sis_provisioner.models import Import, ImportResource
from sis_provisioner.models.account import Account
from sis_provisioner.models.user import User
from sis_provisioner.exceptions import (
    AccountPolicyException, EmptyQueueException)
from datetime import datetime, timedelta


class AdminManager(models.Manager):
    def find_by_account(self, account=None, is_deleted=False):
        kwargs = {}
        if account is None:
            kwargs['account__is_deleted__isnull'] = True
        else:
            kwargs['account'] = account

        if is_deleted:
            kwargs['is_deleted'] = True

        return super(AdminManager, self).get_queryset().filter(**kwargs)

    def queue_all(self):
        pks = super(AdminManager, self).get_queryset().filter(
            queue_id__isnull=True,
            account__is_deleted__isnull=True).values_list('pk', flat=True)

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=Admin.PRIORITY_DEFAULT, csv_type='admin')
        imp.save()

        super(AdminManager, self).get_queryset().update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(AdminManager, self).get_queryset().filter(
            queue_id=queue_id).order_by('-is_deleted')

    def dequeue(self, sis_import):
        User.objects.dequeue(sis_import)
        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            kwargs['provisioned_date'] = sis_import.monitor_date

        self.queued(sis_import.pk).update(**kwargs)

    def start_reconcile(self, queue_id):
        """
        Mark all records deleted to catch ASTRA fallen
        """
        super(AdminManager, self).get_queryset().filter(
            queue_id=queue_id).update(is_deleted=True)

    def finish_reconcile(self, queue_id):
        retention = getattr(settings, 'REMOVED_ADMIN_RETENTION_DAYS', 90)
        now_dt = datetime.utcnow().replace(tzinfo=utc)
        retention_dt = now_dt - timedelta(days=retention)

        # Set deleted date for admins who were just deleted
        super(AdminManager, self).get_queryset().filter(
            queue_id=queue_id, is_deleted__isnull=False,
            deleted_date=None).update(deleted_date=now_dt)

        # Purge expired removed admins
        super(AdminManager, self).get_queryset().filter(
            queue_id=queue_id, is_deleted__isnull=False,
            deleted_date__lt=retention_dt).delete()

    def load_all_admins(self, queue_id):
        admins = ASTRA().get_canvas_admins()

        self.start_reconcile(queue_id)

        for admin_data in admins:
            admin_data['queue_id'] = queue_id
            self.add_admin(**admin_data)

        self.finish_reconcile(queue_id)

    def add_admin(self, **kwargs):
        try:
            if kwargs['canvas_id'] is not None:
                account = Account.objects.get(canvas_id=kwargs['canvas_id'])
            elif kwargs['account_sis_id'] is not None:
                account = Account.objects.get(sis_id=kwargs['account_sis_id'])
            else:
                raise AccountPolicyException('Missing account for admin')
        except Account.DoesNotExist:
            raise AccountPolicyException('Unknown account: "{}" ({})'.format(
                kwargs.get('account_sis_id'), kwargs.get('canvas_id')))

        admin, created = Admin.objects.get_or_create(
            net_id=kwargs['net_id'],
            reg_id=kwargs['reg_id'],
            role=kwargs['role'],
            account=account)

        if kwargs.get('queue_id'):
            admin.queue_id = kwargs['queue_id']

        admin.is_deleted = None
        admin.deleted_date = None
        admin.save()
        return admin

    def is_account_admin(self, net_id):
        return self.has_role_in_account(
            net_id, settings.RESTCLIENTS_CANVAS_ACCOUNT_ID, 'accountadmin')

    def has_role_in_account(self, net_id, canvas_id, role):
        try:
            admin = Admin.objects.get(
                net_id=net_id, account__canvas_id=canvas_id, role=role,
                deleted_date__isnull=True)
            return True
        except Admin.DoesNotExist:
            return False

    def has_role(self, net_id, role):
        try:
            admin = Admin.objects.get(
                net_id=net_id, role=role, deleted_date__isnull=True,
                account__is_deleted__isnull=True)
            return True
        except Admin.MultipleObjectsReturned:
            return True
        except Admin.DoesNotExist:
            return False

    def verify_canvas_admin(self, admin, canvas_account_id):
        # Create a reverse lookup for ASTRA role, based on the role in Canvas
        roles = {v: k for k, v in settings.ASTRA_ROLE_MAPPING.items()}

        # Verify whether this role is ASTRA-defined
        astra_role = roles.get(admin.role)
        if (astra_role is not None and self.has_role_in_account(
                admin.user.login_id, canvas_account_id, astra_role)):
            return True

        # Otherwise, verify whether this is a valid ancillary role
        for parent_role, data in settings.ANCILLARY_CANVAS_ROLES.items():
            if 'root' == data['account']:
                ancillary_account_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
            else:
                ancillary_account_id = canvas_account_id

            if (str(ancillary_account_id) == str(canvas_account_id) and
                    data['canvas_role'] == admin.role):
                if self.has_role(admin.user.login_id, parent_role):
                    return True

        # Check for allowed admins not in ASTRA, or admins with a
        # non-standard ancillary role
        if (admin.user.login_id in getattr(
                settings, 'ASTRA_ADMIN_EXCEPTIONS', [])):
            return True

        return False


class Admin(ImportResource):
    """ Represents the provisioned state of an administrative user.
    """
    net_id = models.CharField(max_length=20)
    reg_id = models.CharField(max_length=32)
    role = models.CharField(max_length=32)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    canvas_id = models.IntegerField(null=True)
    added_date = models.DateTimeField(auto_now_add=True)
    provisioned_date = models.DateTimeField(null=True)
    deleted_date = models.DateTimeField(null=True)
    is_deleted = models.BooleanField(null=True)
    queue_id = models.CharField(max_length=30, null=True)

    objects = AdminManager()

    class Meta:
        db_table = 'astra_admin'

    def json_data(self):
        date_fmt = '%m/%d/%Y %l:%M %p'
        return {
            'net_id': self.net_id,
            'reg_id': self.reg_id,
            'role': self.role,
            'account': self.account.json_data(),
            'added_date': localtime(self.added_date).strftime(date_fmt) if (
                self.added_date is not None) else '',
            'provisioned_date': localtime(self.provisioned_date).strftime(
                date_fmt) if (self.provisioned_date is not None) else '',
            'is_deleted': True if self.is_deleted else False,
            'deleted_date': localtime(self.deleted_date).strftime(
                date_fmt) if (self.deleted_date is not None) else '',
            'queue_id': self.queue_id
        }


class RoleCacheManager(models.Manager):
    def check_roles_for_account(self, account_id):
        try:
            account = Account.objects.get(canvas_id=account_id)
        except Account.DoesNotExist:
            raise AccountPolicyException(
                'Unknown account: {}'.format(account_id))

        serialized = get_account_role_data(account_id)
        new_cache = RoleCache(account=account, role_data=serialized)

        try:
            last_cache = RoleCache.objects.filter(account=account).latest()
        except RoleCache.DoesNotExist:
            new_cache.save()
            return False

        if new_cache.role_data != last_cache.role_data:
            new_cache.save()
            return True
        return False


class RoleCache(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    role_data = models.TextField()
    time_saved = models.DateTimeField(auto_now_add=True)

    objects = RoleCacheManager()

    class Meta:
        get_latest_by = 'time_saved'
