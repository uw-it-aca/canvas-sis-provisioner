# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.events.instructor import (
    InstructorAddProcessor, InstructorDropProcessor)
from sis_provisioner.exceptions import EventException
from aws_message.gather import Gather, GatherException


class Command(SISProvisionerCommand):
    help = "Loads instructor events from SQS"

    def health_check(self):
        try:
            InstructorAddProcessor().check_interval(acceptable_silence=24*60)
        except EventException as ex:
            self.squawk('Warning: {}'.format(ex))

    def handle(self, *args, **options):
        try:
            # TODO: split these into separate async jobs
            Gather(processor=InstructorAddProcessor()).gather_events()
            Gather(processor=InstructorDropProcessor()).gather_events()
            self.update_job()
        except GatherException as err:
            raise CommandError(err)
