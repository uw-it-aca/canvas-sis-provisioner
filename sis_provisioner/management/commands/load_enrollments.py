from django.core.management.base import CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.events.enrollment import EnrollmentProcessor
from sis_provisioner.exceptions import EventException
from aws_message.gather import Gather, GatherException


class Command(SISProvisionerCommand):
    help = "Loads enrollment events from SQS"

    def health_check(self):
        try:
            EnrollmentProcessor().check_interval()
        except EventException as ex:
            self.squawk(ex)

    def handle(self, *args, **options):
        try:
            Gather(processor=EnrollmentProcessor()).gather_events()
            self.update_job()
        except GatherException as err:
            raise CommandError(err)
        except Exception as err:
            raise CommandError('FAIL: {}'.format(err))
