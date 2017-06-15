from django.db import models
from django.conf import settings
from logging import getLogger
from sis_provisioner.models import Curriculum
from sis_provisioner.dao.canvas import get_account_by_id, get_all_sub_accounts

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
            admin = Admin.objects.get(net_id=net_id,
                                      role='accountadmin',
                                      deleted_date__isnull=True)
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


class AccountManager(models.Manager):
    def add_all_accounts(self):
        root_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
        accounts = [get_account_by_id(root_id)]
        accounts.extend(get_all_sub_accounts(root_id))

        super(AccountManager, self).get_queryset().update(is_deleted=True)

        for account in accounts:
            self.add_account(account)

    def add_account(self, account):
        sis_id = None
        account_type = Account.ADHOC_TYPE
        if account.account_id == int(settings.RESTCLIENTS_CANVAS_ACCOUNT_ID):
            account_type = Account.ROOT_TYPE
        elif account.sis_account_id is not None:
            sis_id = account.sis_account_id
            try:
                curriculum = Curriculum.objects.get(
                    subaccount_id=account.sis_account_id)
                account_type = Account.SDB_TYPE
            except Curriculum.DoesNotExist:
                pass

        try:
            a = Account.objects.get(canvas_id=account.account_id)
            a.sis_id = sis_id
            a.account_name = account.name
            a.account_type = account_type
            a.is_deleted = None
        except Account.DoesNotExist:
            a = Account(canvas_id=account.account_id,
                        sis_id=sis_id,
                        account_name=account.name,
                        account_type=account_type)

        try:
            a.save()
        except IntegrityError as err:
            logger.error('ACCOUNT LOAD FAIL: canvas_id: %s, sis_id: %s, %s' % (
                    account.account_id, sis_id, err))
            raise

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
            'id': 'canvas_%s' % self.canvas_id,
            'type': type_name,
            'description': self.account_name,
            'short_description': self.account_short_name
        }
