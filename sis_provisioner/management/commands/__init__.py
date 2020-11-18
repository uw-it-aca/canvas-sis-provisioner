from django.core.management.base import BaseCommand
from django.core.mail import mail_admins
from django.utils.timezone import utc
from sis_provisioner.models import Job
from logging import getLogger
import datetime
import sys


class SISProvisionerCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(SISProvisionerCommand, self).__init__(*args, **kwargs)

        if not self.is_active_job():
            sys.exit(0)

        self.log = getLogger(__name__)
        self.health_check()

    def is_active_job(self):
        name = self.name_from_argv()
        try:
            job = Job.objects.get(name=name)
        except Job.DoesNotExist:
            job = Job(name=name,
                      title=self.title_from_name(name),
                      is_active=False)
            job.changed_date = datetime.datetime.utcnow().replace(tzinfo=utc)
            job.save()

        return True if job.is_active else False

    def update_job(self):
        job = Job.objects.get(name=self.name_from_argv())
        job.last_run_date = datetime.datetime.utcnow().replace(tzinfo=utc)
        job.save()

    def health_check(self):
        """Override to sanity check specific job environment"""
        pass

    def squawk(self, message="Problem with Provisioning Job"):
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        job = Job.objects.get(name=self.name_from_argv())
        job.health_status = message
        if (not job.last_status_date or
                (now - job.last_status_date) > datetime.timedelta(hours=1)):
            try:
                mail_admins(
                    'Provisioning job "{}" may be having issues'.format(
                        job.title), message, fail_silently=True)
                job.last_status_date = now
            except Exception as err:
                self.log.error(
                    'Cannot email admins "{}", Error Message: "{}"'.format(
                        err, message))

        job.save()

    def name_from_argv(self):
        name = sys.argv[1]
        args = sys.argv[2:]
        if name == '--delay':
            name = sys.argv[3]
            args = sys.argv[4:]
        if len(args):
            name += ':' + ':'.join(args).replace('--', '')
        return name

    def title_from_name(self, name):
        parts = name.split(':')
        title = ' '.join(w.capitalize() for w in parts[0].split('_'))
        args = parts[1:]
        if len(args):
            title += ' (' + ', '.join(args) + ')'
        return title
