from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.models import Job
import datetime
import sys


class SISProvisionerCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(SISProvisionerCommand, self).__init__(*args, **kwargs)

        if not self.is_active_job(name=sys.argv[1]):
            sys.exit(0)

    def is_active_job(self, name):
        try:
            job = Job.objects.get(name=name)
        except Job.DoesNotExist:
            job = Job(name=name, is_active=False)
            job.save()

        return True if job.is_active else False

    def update_job(self):
        job = Job.objects.get(name=sys.argv[1])
        job.last_run_date = datetime.datetime.utcnow().replace(tzinfo=utc)
        job.save()
