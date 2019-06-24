from django.conf import settings
from django.db import models
from django.utils.timezone import utc, localtime
from sis_provisioner.models import Account
from sis_provisioner.dao.canvas import (
    get_account_by_id, get_sub_accounts, get_external_tools,
    create_external_tool, update_external_tool, delete_external_tool)
from blti.models import BLTIKeyStore
from datetime import datetime
import string
import random
import json


class ExternalToolManager(models.Manager):
    def get_by_hostname(self, hostname):
        return super(ExternalToolManager, self).get_queryset().filter(
            config__contains=hostname)

    def import_all(self, changed_by='auto'):
        account_id = getattr(settings, 'RESTCLIENTS_CANVAS_ACCOUNT_ID')
        self.import_tools_in_account(account_id, changed_by)

    def import_tools_in_account(self, account_id, changed_by):
        for config in get_external_tools(account_id):
            try:
                tool = ExternalTool.objects.get(canvas_id=config.get('id'))
            except ExternalTool.DoesNotExist:
                tool = ExternalTool(canvas_id=config.get('id'))
                tool.account = Account.objects.get(canvas_id=account_id)

            tool.config = json.dumps(config)
            tool.changed_by = changed_by
            tool.changed_date = datetime.utcnow().replace(tzinfo=utc)
            tool.save()

        for subaccount in get_sub_accounts(account_id):
            self.import_tools_in_account(subaccount.account_id, changed_by)

    def create_tool(self, account_id, config, created_by):
        account = Account.objects.get(canvas_id=account_id)
        tool = ExternalTool(
            account=account,
            changed_by=created_by,
            changed_date=datetime.utcnow().replace(tzinfo=utc))

        try:
            keystore = BLTIKeyStore.objects.get(
                consumer_key=config.get('consumer_key'))
            # Re-using an existing key/secret (clone?)
            config['shared_secret'] = keystore.shared_secret

        except BLTIKeyStore.DoesNotExist:
            keystore = BLTIKeyStore(consumer_key=config.get('consumer_key'))
            shared_secret = config.get('shared_secret')
            if shared_secret is None or not len(shared_secret):
                keystore.shared_secret = tool.generate_shared_secret()
                config['shared_secret'] = keystore.shared_secret
            keystore.save()

        new_config = create_external_tool(account_id, config)

        tool.canvas_id = new_config.get('id')
        tool.config = json.dumps(new_config)
        tool.provisioned_date = datetime.utcnow().replace(tzinfo=utc)
        tool.save()
        return tool

    def update_tool(self, canvas_id, config, updated_by):
        tool = ExternalTool.objects.get(canvas_id=canvas_id)

        try:
            keystore = BLTIKeyStore.objects.get(
                consumer_key=config.get('consumer_key'))
        except BLTIKeyStore.DoesNotExist:
            keystore = BLTIKeyStore(consumer_key=config.get('consumer_key'))

        if 'shared_secret' in config:
            shared_secret = config['shared_secret']
            if shared_secret is None or not len(shared_secret):
                del config['shared_secret']
            else:
                keystore.shared_secret = shared_secret
                keystore.save()

        new_config = update_external_tool(
            tool.account.canvas_id, canvas_id, config)

        tool.config = json.dumps(new_config)
        tool.changed_by = updated_by
        tool.changed_date = datetime.utcnow().replace(tzinfo=utc)
        tool.provisioned_date = datetime.utcnow().replace(tzinfo=utc)
        tool.save()
        return tool

    def delete_tool(self, canvas_id):
        tool = ExternalTool.objects.get(canvas_id=canvas_id)
        tool.delete()
        return delete_external_tool(tool.account.canvas_id, tool.canvas_id)


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

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    canvas_id = models.CharField(max_length=20, unique=True)
    config = models.TextField()
    changed_by = models.CharField(max_length=32)
    changed_date = models.DateTimeField()
    provisioned_date = models.DateTimeField(null=True)

    class Meta:
        db_table = 'lti_manager_externaltool'

    objects = ExternalToolManager()

    def get_shared_secret(self):
        try:
            config = json.loads(self.config)
            if config.get('consumer_key'):
                keystore = BLTIKeyStore.objects.get(
                    consumer_key=config['consumer_key'])
                return keystore.shared_secret
        except Exception:
            pass

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
            'account': self.account.json_data(),
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
