from django.db import models
from django.utils.timezone import utc, localtime
import datetime
import string
import random
import json


class ExternalToolAccount(models.Model):
    account_id = models.CharField(max_length=100, unique=True)
    sis_account_id = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=250, null=True)

    class Meta:
        db_table = 'lti_manager_externaltoolaccount'


class ExternalToolManager(models.Manager):
    def get_by_hostname(self, hostname):
        return super(ExternalToolManager, self).get_queryset().filter(
            config__contains=hostname)


class ExternalTool(models.Model):
    PRIVACY_ANONYMOUS = 'anonymous'
    PRIVACY_NAMEONLY = 'name_only'
    PRIVACY_PUBLIC = 'public'
    PRIVACY_CHOICES = (
        (PRIVACY_ANONYMOUS, 'Anonymous'),
        (PRIVACY_NAMEONLY, 'Name Only'),
        (PRIVACY_PUBLIC, 'Public')
    )

    VISIBILITY_CHOICES = (
        ('admins', 'Admins'), ('members', 'Members')
    )

    account = models.ForeignKey(ExternalToolAccount)
    canvas_id = models.CharField(max_length=20, unique=True)
    config = models.TextField()
    changed_by = models.CharField(max_length=32)
    changed_date = models.DateTimeField()
    provisioned_date = models.DateTimeField(null=True)

    class Meta:
        db_table = 'lti_manager_externaltool'

    objects = ExternalToolManager()

    def generate_shared_secret(self):
        return ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits) for _ in range(32))

    def json_data(self):
        try:
            config = json.loads(self.config)
        except Exception as err:
            config = {'name': 'Error', 'error': str(err)}

        return {
            'id': self.pk,
            'account_id': self.account.account_id,
            'sis_account_id': self.account.sis_account_id,
            'account_name': self.account.name,
            'canvas_id': self.canvas_id,
            'name': config.get('name'),
            'consumer_key': config.get('consumer_key'),
            'config': config,
            'changed_by': self.changed_by,
            'changed_date': localtime(self.changed_date).isoformat() if (
                self.changed_date is not None) else None,
            'provisioned_date': localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date is not None) else None,
        }
