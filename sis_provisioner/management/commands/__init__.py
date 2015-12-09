from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.models import Trigger
import sys


class SISProvisionerCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(SISProvisionerCommand, self).__init__(*args, **kwargs)

        if not self.check_trigger(name=sys.argv[1]):
            sys.exit(0)

    def check_trigger(self, name):
        try:
            trigger = Trigger.objects.get(name=name)
            return True if trigger.is_active else False
        except Trigger.DoesNotExist:
            return False
