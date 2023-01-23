# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.events.person import PersonProcessor
from sis_provisioner.exceptions import EventException
from aws_message.gather import Gather, GatherException


class Command(SISProvisionerCommand):
    help = "Loads Person change events from SQS"

    def health_check(self):
        try:
            PersonProcessor().check_interval()
        except EventException as ex:
            self.squawk('Warning: {}'.format(ex))

    def handle(self, *args, **options):
        try:
            Gather(processor=PersonProcessor()).gather_events()
            self.update_job()
        except GatherException as err:
            raise CommandError(err)
