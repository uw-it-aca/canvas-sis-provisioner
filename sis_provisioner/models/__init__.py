# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models, IntegrityError
from django.db.models import F, Q
from django.conf import settings
from django.utils.timezone import utc, localtime
from sis_provisioner.dao.account import (
    valid_academic_account_sis_id, adhoc_account_sis_id)
from sis_provisioner.dao.astra import ASTRA
from sis_provisioner.dao.group import get_sis_import_members, is_modified_group
from sis_provisioner.dao.term import (
    get_term_by_year_and_quarter, term_date_overrides)
from sis_provisioner.dao.canvas import (
    sis_import_by_path, get_sis_import_status,
    get_account_by_id, get_all_sub_accounts, update_account_sis_id,
    update_term_overrides, get_account_role_data)
from sis_provisioner.exceptions import (
    AccountPolicyException, EmptyQueueException, MissingImportPathException,
    GroupNotFoundException)
from restclients_core.exceptions import DataFailureException
from datetime import datetime, timedelta
from logging import getLogger
import json
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
    def update_override_dates(self):
        for term in super(TermManager, self).get_queryset().filter(
                updated_overrides_date__isnull=True):

            (year, quarter) = term.term_id.split('-')
            try:
                sws_term = get_term_by_year_and_quarter(year, quarter)
                update_term_overrides(term.term_id,
                                      term_date_overrides(sws_term))
                term.updated_overrides_date = datetime.utcnow().replace(
                    tzinfo=utc)
                term.save()

            except DataFailureException as ex:
                logger.info('Unable to set term overrides: {}'.format(ex))

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

    def dequeue(self, sis_import):
        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            # Currently only handles the 'unused_course' type
            kwargs['deleted_unused_courses_date'] = sis_import.monitor_date

        self.queued(sis_import.pk).update(**kwargs)


class Term(models.Model):
    """ Represents the provisioned state of courses for a term.
    """
    term_id = models.CharField(max_length=20, unique=True)
    added_date = models.DateTimeField(auto_now_add=True)
    last_course_search_date = models.DateTimeField(null=True)
    courses_changed_since_date = models.DateTimeField(null=True)
    deleted_unused_courses_date = models.DateTimeField(null=True)
    updated_overrides_date = models.DateTimeField(null=True)
    queue_id = models.CharField(max_length=30, null=True)

    objects = TermManager()


class GroupManager(models.Manager):
    def queue_by_priority(self, priority=PRIORITY_DEFAULT):
        if priority > PRIORITY_DEFAULT:
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
            priority=PRIORITY_DEFAULT, queue_id=imp.pk
        )

        return imp

    def update_priority_by_modified_date(self):
        groups = super(GroupManager, self).get_queryset().filter(
            priority=PRIORITY_DEFAULT, queue_id__isnull=True
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

                if is_mod:
                    group.update_priority(PRIORITY_HIGH)
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

                            if is_mod:
                                group.update_priority(PRIORITY_HIGH)
                                break

    def find_by_search(self, **kwargs):
        kwargs['is_deleted__isnull'] = True
        return super(GroupManager, self).get_queryset().filter(**kwargs)

    def get_active_by_group(self, group_id):
        return super(GroupManager, self).get_queryset().filter(
            group_id=group_id, priority__gt=PRIORITY_NONE,
            is_deleted__isnull=True)

    def get_active_by_course(self, course_id):
        return super(GroupManager, self).get_queryset().filter(
            course_id=course_id, is_deleted__isnull=True)

    def queued(self, queue_id):
        return super(GroupManager, self).get_queryset().filter(
            queue_id=queue_id).order_by('course_id').values_list(
                'course_id', flat=True).distinct()

    def dequeue(self, sis_import):
        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            kwargs['provisioned_date'] = sis_import.monitor_date
            kwargs['priority'] = PRIORITY_DEFAULT

        self.queued(sis_import.pk).update(**kwargs)

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

    def update_group_id(self, old_group_id, new_group_id):
        super(GroupManager, self).get_queryset().filter(
            group_id=old_group_id).update(group_id=new_group_id)

    def delete_group_not_found(self, group_id):
        super(GroupManager, self).get_queryset().filter(
            group_id=group_id, is_deleted__isnull=True
        ).update(
            is_deleted=True, deleted_by='gws',
            deleted_date=datetime.utcnow().replace(tzinfo=utc)
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

    def update_priority(self, priority):
        for val, txt in PRIORITY_CHOICES:
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
            "priority": PRIORITY_CHOICES[self.priority][1],
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
    is_deleted = models.NullBooleanField()

    objects = GroupMemberGroupManager()

    def deactivate(self):
        self.is_deleted = True
        self.save()

    def activate(self):
        self.is_deleted = None
        self.save()


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

        super(CourseMemberManager, self).get_queryset().filter(
            pk__in=list(pks)).update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(CourseMemberManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        if sis_import.is_imported():
            # Decrement the priority
            super(CourseMemberManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)

    def get_by_course(self, course_id):
        return super(CourseMemberManager, self).get_queryset().filter(
            course_id=course_id)


class CourseMember(models.Model):
    UWNETID_TYPE = "uwnetid"
    EPPN_TYPE = "eppn"

    TYPE_CHOICES = (
        (UWNETID_TYPE, "UWNetID"),
        (EPPN_TYPE, "ePPN")
    )

    course_id = models.CharField(max_length=80)
    name = models.CharField(max_length=256)
    type = models.SlugField(max_length=16, choices=TYPE_CHOICES)
    role = models.CharField(max_length=80)
    is_deleted = models.NullBooleanField()
    deleted_date = models.DateTimeField(null=True, blank=True)
    priority = models.SmallIntegerField(default=0, choices=PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = CourseMemberManager()

    def is_uwnetid(self):
        return self.type.lower() == self.UWNETID_TYPE

    def is_eppn(self):
        return self.type.lower() == self.EPPN_TYPE

    def deactivate(self):
        self.is_deleted = True
        self.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        self.save()

    def activate(self):
        self.is_deleted = None
        self.deleted_date = None
        self.save()

    def __eq__(self, other):
        return (self.course_id == other.course_id and
                self.name.lower() == other.name.lower() and
                self.type.lower() == other.type.lower() and
                self.role.lower() == other.role.lower())


class CurriculumManager(models.Manager):
    def queued(self, queue_id):
        return super(CurriculumManager, self).get_queryset()

    def dequeue(self, sis_import):
        pass

    def accounts_by_curricula(self):
        return dict((curr, account) for curr, account in (
            super(CurriculumManager, self).get_queryset().values_list(
                'curriculum_abbr', 'subaccount_id')))


class Curriculum(models.Model):
    """ Maps curricula to sub-account IDs
    """
    curriculum_abbr = models.SlugField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    subaccount_id = models.CharField(max_length=100, unique=True)

    objects = CurriculumManager()


class AccountManager(models.Manager):
    def find_by_type(self, account_type=None, is_deleted=False):
        kwargs = {}
        if account_type:
            kwargs['account_type'] = account_type
        if is_deleted:
            kwargs['is_deleted'] = True

        return super(AccountManager, self).get_queryset().filter(**kwargs)

    def find_by_soc(self, account_type=''):
        t = account_type.lower()
        if t == 'academic':
            q = Q(account_type=Account.SDB_TYPE)
        elif t == 'non-academic':
            q = Q(account_type=Account.ADHOC_TYPE)
        elif t == 'test-account':
            q = Q(account_type=Account.TEST_TYPE)
        elif t == 'all':
            q = (Q(account_type=Account.ROOT_TYPE) |
                 Q(account_type=Account.SDB_TYPE) |
                 Q(account_type=Account.ADHOC_TYPE) |
                 Q(account_type=Account.TEST_TYPE))
        else:
            q = (Q(account_type=Account.ADHOC_TYPE) |
                 Q(account_type=Account.TEST_TYPE))

        return super(AccountManager, self).get_queryset().filter(q)

    def add_all_accounts(self):
        account = get_account_by_id(settings.RESTCLIENTS_CANVAS_ACCOUNT_ID)
        accounts = get_all_sub_accounts(account.account_id)
        accounts.append(account)

        super(AccountManager, self).get_queryset().update(is_deleted=True)

        for account in accounts:
            self.add_account(account)

    def add_account(self, account):
        account_type = Account.ADHOC_TYPE
        if account.account_id == int(settings.RESTCLIENTS_CANVAS_ACCOUNT_ID):
            account_type = Account.ROOT_TYPE
        elif account.sis_account_id is not None:
            try:
                valid_academic_account_sis_id(account.sis_account_id)
                account_type = Account.SDB_TYPE
            except AccountPolicyException as ex:
                pass
        else:
            account = update_account_sis_id(
                account.account_id, adhoc_account_sis_id(account.account_id))

        try:
            a = Account.objects.get(canvas_id=account.account_id)
            a.sis_id = account.sis_account_id
            a.account_name = account.name
            a.account_type = account_type
            a.is_deleted = None
        except Account.DoesNotExist:
            a = Account(canvas_id=account.account_id,
                        sis_id=account.sis_account_id,
                        account_name=account.name,
                        account_type=account_type)

        try:
            a.save()
        except IntegrityError as err:
            logger.error(
                'ADD ACCOUNT FAIL: canvas_id: {}, sis_id: {}, {}'.format(
                    account.account_id, account.sis_account_id, err))

        return a


class Account(models.Model):
    """ Represents Canvas Accounts
    """
    ROOT_TYPE = 'root'
    SDB_TYPE = 'sdb'
    ADHOC_TYPE = 'adhoc'
    TEST_TYPE = 'test'

    TYPE_CHOICES = (
        (SDB_TYPE, 'SDB'),
        (ADHOC_TYPE, 'Ad Hoc'),
        (ROOT_TYPE, 'Root'),
        (TEST_TYPE, 'Test')
    )

    canvas_id = models.IntegerField(unique=True)
    sis_id = models.CharField(max_length=128, unique=True, blank=True,
                              null=True)
    account_name = models.CharField(max_length=256)
    account_short_name = models.CharField(max_length=128)
    account_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    added_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.NullBooleanField()
    is_blessed_for_course_request = models.NullBooleanField()
    queue_id = models.CharField(max_length=30, null=True)

    objects = AccountManager()

    class Meta:
        db_table = 'astra_account'

    def is_root(self):
        return self.account_type == self.ROOT_TYPE

    def is_sdb(self):
        return self.account_type == self.SDB_TYPE

    def is_adhoc(self):
        return self.account_type == self.ADHOC_TYPE

    def is_test(self):
        return self.account_type == self.TEST_TYPE

    def json_data(self):
        return {
            'canvas_id': self.canvas_id,
            'sis_id': self.sis_id,
            'name': self.account_name,
            'short_name': self.account_short_name,
            'account_type': self.account_type,
            'canvas_url': '{host}/accounts/{account_id}'.format(
                host=settings.RESTCLIENTS_CANVAS_HOST,
                account_id=self.canvas_id),
            'added_date': self.added_date.isoformat() if (
                self.added_date is not None) else '',
            'is_deleted': True if self.is_deleted else False
        }

    def soc_json_data(self):
        type_name = 'Unknown'
        if self.is_root():
            type_name = 'Root'
        elif self.is_sdb():
            type_name = 'SDB'
        elif self.is_adhoc():
            type_name = 'Non-Academic'
        elif self.is_test():
            type_name = 'Test-Account'

        return {
            'id': 'canvas_{}'.format(self.canvas_id),
            'type': type_name,
            'description': self.account_name,
            'short_description': self.account_short_name
        }


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

        imp = Import(priority=PRIORITY_DEFAULT, csv_type='admin')
        imp.save()

        super(AdminManager, self).get_queryset().update(queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(AdminManager, self).get_queryset().filter(
            queue_id=queue_id).order_by('-is_deleted')

    def dequeue(self, sis_import):
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


class Admin(models.Model):
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
    is_deleted = models.NullBooleanField()
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


class ImportResource(models.Model):
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

    class Meta:
        abstract = True


class ImportManager(models.Manager):
    def find_by_requires_update(self):
        return super(ImportManager, self).get_queryset().filter(
            (Q(canvas_warnings__isnull=True) &
                Q(canvas_errors__isnull=True)) | Q(monitor_status__gte=500),
            canvas_id__isnull=False,
            post_status=200)


class Import(models.Model):
    """ Represents a set of files that have been queued for import.
    """
    CSV_TYPE_CHOICES = (
        ('account', 'Curriculum'),
        ('admin', 'Admin'),
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
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    override_sis_stickiness = models.NullBooleanField()
    post_status = models.SmallIntegerField(null=True)
    monitor_date = models.DateTimeField(null=True)
    monitor_status = models.SmallIntegerField(null=True)
    canvas_id = models.CharField(max_length=30, null=True)
    canvas_state = models.CharField(max_length=80, null=True)
    canvas_progress = models.SmallIntegerField(default=0)
    canvas_warnings = models.TextField(null=True)
    canvas_errors = models.TextField(null=True)

    objects = ImportManager()

    def json_data(self):
        return {
            "queue_id": self.pk,
            "type": self.csv_type,
            "csv_path": self.csv_path,
            "type_name": self.get_csv_type_display(),
            "added_date": localtime(self.added_date).isoformat(),
            "priority": ImportResource.PRIORITY_CHOICES[self.priority][1],
            "override_sis_stickiness": self.override_sis_stickiness,
            "csv_errors": self.csv_errors,
            "post_status": self.post_status,
            "canvas_state": self.canvas_state,
            "canvas_progress": self.canvas_progress,
            "canvas_warnings": self.canvas_warnings,
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
            sis_import = sis_import_by_path(self.csv_path,
                                            self.override_sis_stickiness)
            self.post_status = 200
            self.canvas_id = sis_import.import_id
            self.canvas_state = sis_import.workflow_state
        except DataFailureException as ex:
            self.post_status = ex.status
            self.canvas_errors = ex

        self.save()

    def update_import_status(self):
        """
        Updates import attributes, based on the sis import resource.
        """
        try:
            sis_import = get_sis_import_status(self.canvas_id)
            self.monitor_status = 200
            self.monitor_date = datetime.utcnow().replace(tzinfo=utc)
            self.canvas_state = sis_import.workflow_state
            self.canvas_progress = sis_import.progress
            self.canvas_warnings = None
            self.canvas_errors = None

            warnings = self._process_warnings(sis_import.processing_warnings)
            if len(warnings):
                self.canvas_warnings = json.dumps(warnings)

            if len(sis_import.processing_errors):
                self.canvas_errors = json.dumps(sis_import.processing_errors)

        except (DataFailureException, KeyError) as ex:
            logger.info('Monitor error: {}'.format(ex))
            return

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
        return (self.is_imported() and
                self.canvas_warnings is None and
                self.canvas_errors is None)

    def is_imported(self):
        return (self.is_completed() and
                self.canvas_state is not None and
                re.match(r'^imported', self.canvas_state) is not None)

    def dependent_model(self):
        if self.get_csv_type_display():
            for subclass in ImportResource.__subclasses__():
                if subclass.__name__.endswith(self.get_csv_type_display()):
                    return subclass
        return globals()[self.get_csv_type_display()]

    def queued_objects(self):
        return self.dependent_model().objects.queued(self.pk)

    def dequeue_dependent_models(self):
        # XXX move this to dequeue() methods
        # if self.csv_type != 'user' and self.csv_type != 'account':
        #    User.objects.dequeue(self)

        self.dependent_model().objects.dequeue(self)

    def delete(self, *args, **kwargs):
        self.dequeue_dependent_models()
        return super(Import, self).delete(*args, **kwargs)

    def _process_warnings(self, warnings):
        return [w for w in warnings if ('-MSIS-550-' not in w[-1])]


class SubAccountOverrideManager(models.Manager):
    def overrides_by_course(self):
        return dict((course_id, account) for course_id, account in (
            super(SubAccountOverrideManager, self).get_queryset().values_list(
                'course_id', 'subaccount_id')))


class SubAccountOverride(models.Model):
    course_id = models.CharField(max_length=80)
    subaccount_id = models.CharField(max_length=100)
    reference_date = models.DateTimeField(auto_now_add=True)

    objects = SubAccountOverrideManager()


class TermOverride(models.Model):
    course_id = models.CharField(max_length=80)
    term_sis_id = models.CharField(max_length=24)
    term_name = models.CharField(max_length=24)
    reference_date = models.DateTimeField(auto_now_add=True)


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
