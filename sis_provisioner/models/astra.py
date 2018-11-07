from django.db import models, IntegrityError
from django.db.models import Q
from django.conf import settings
from django.utils.timezone import localtime
from logging import getLogger
from sis_provisioner.dao.account import valid_academic_account_sis_id
from sis_provisioner.dao.canvas import get_account_by_id, get_all_sub_accounts
from sis_provisioner.exceptions import AccountPolicyException


logger = getLogger(__name__)


class AdminManager(models.Manager):
    def queue_all(self, queue_id):
        return super(AdminManager, self).get_queryset().update(
            queue_id=queue_id, is_deleted=True)

    def queued(self, queue_id=None):
        if queue_id is not None:
            return super(AdminManager, self).get_queryset().filter(
                queue_id=queue_id)
        else:
            return super(AdminManager, self).get_queryset().filter(
                queue_id__isnull=False)

    def dequeue(self, queue_id=None):
        if queue_id is not None:
            super(AdminManager, self).get_queryset().filter(
                queue_id=queue_id).update(queue_id=None)
        else:
            super(AdminManager, self).get_queryset().filter(
                queue_id__isnull=False).update(queue_id=None)

    def get_deleted(self):
        return super(AdminManager, self).get_queryset().filter(
            is_deleted__isnull=False)

    def is_account_admin(self, net_id):
        try:
            admin = Admin.objects.get(
                net_id=net_id, role='accountadmin', deleted_date__isnull=True)
            return True
        except Admin.DoesNotExist:
            return False


class Admin(models.Model):
    """ Represents the provisioned state of an administrative user.
    """
    net_id = models.CharField(max_length=20)
    reg_id = models.CharField(max_length=32)
    role = models.CharField(max_length=32)
    account_id = models.CharField(max_length=128)
    canvas_id = models.IntegerField()
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
            'account_id': self.account_id,
            'canvas_id': self.canvas_id,
            'account_link': '{host}/accounts/{account_id}'.format(
                host=settings.RESTCLIENTS_CANVAS_HOST,
                account_id=self.canvas_id),
            'added_date': localtime(self.added_date).strftime(date_fmt) if (
                self.added_date is not None) else '',
            'provisioned_date': localtime(self.provisioned_date).strftime(
                date_fmt) if (self.provisioned_date is not None) else '',
            'is_deleted': True if self.is_deleted else False,
            'deleted_date': localtime(self.deleted_date).strftime(
                date_fmt) if (self.deleted_date is not None) else '',
            'queue_id': self.queue_id
        }


class AccountManager(models.Manager):
    def find_by_type(self, account_type=None, deleted=False):
        filter = {}
        if account_type:
            filter['account_type'] = account_type
        if deleted:
            filter['is_deleted'] = 1

        return super(AccountManager, self).get_queryset().filter(**filter)

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
        root_id = getattr(settings, 'RESTCLIENTS_CANVAS_ACCOUNT_ID')
        accounts = [get_account_by_id(root_id)]
        accounts.extend(get_all_sub_accounts(root_id))

        super(AccountManager, self).get_queryset().update(is_deleted=True)

        for account in accounts:
            self.add_account(account)

    def add_account(self, account):
        account_type = Account.ADHOC_TYPE
        if account.account_id == int(getattr(settings,
                                             'RESTCLIENTS_CANVAS_ACCOUNT_ID')):
            account_type = Account.ROOT_TYPE
        elif account.sis_account_id is not None:
            try:
                valid_academic_account_sis_id(account.sis_account_id)
                account_type = Account.SDB_TYPE
            except AccountPolicyException:
                pass

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
                'ACCOUNT LOAD FAIL: canvas_id: {}, sis_id: {}, {}'.format(
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
            'account_name': self.account_name,
            'account_short_name': self.account_short_name,
            'account_type': self.account_type,
            'added_date': self.added_date.isoformat() if (
                self.added_date is not None) else '',
            'is_deleted': self.is_deleted,
            'is_blessed_for_course_request': (
                self.is_blessed_for_course_request)}

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
