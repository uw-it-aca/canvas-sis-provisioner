# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from aws_message.gather import Gather, GatherException
from django.core.management.base import CommandError

from sis_provisioner.events.person import PersonProcessor
from sis_provisioner.exceptions import EventException
from sis_provisioner.management.commands import SISProvisionerCommand


class Command(SISProvisionerCommand):
    help = "Loads Person change events from SQS"

    def health_check(self):
        try:
            PersonProcessor().check_interval()
        except EventException as ex:
            self.squawk(f'Warning: {ex}')

    def handle(self, *args, **options):
        try:
            Gather(processor=PersonProcessor()).gather_events()
            self.update_job()
        except GatherException as err:
            raise CommandError(err)
