from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.models import Job
import sys


class SISProvisionerCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(SISProvisionerCommand, self).__init__(*args, **kwargs)

        if not self.is_active_job(name=sys.argv[1]):
            sys.exit(0)

    def is_active_job(self, name):
        try:
            job = Job.objects.get(name=name)
            return True if job.is_active else False
        except Job.DoesNotExist:
            return False
