from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import utc
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
            title = ' '.join(w.capitalize() for w in name.split('_'))
            job = Job(name=name, title=title, is_active=False)
            job.save()

        return True if job.is_active else False

    def update_job(self):
        job = Job.objects.get(name=sys.argv[1])
        job.last_run_date = datetime.datetime.utcnow().replace(tzinfo=utc)
        job.save()
