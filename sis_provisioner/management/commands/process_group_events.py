# Copyright 2026 UWIT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from aws_message.gather import Gather, GatherException
from django.core.management.base import CommandError

from sis_provisioner.events.group import GroupProcessor
from sis_provisioner.exceptions import EventException
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.pidfile import Pidfile, ProcessRunningException


class Command(SISProvisionerCommand):
    help = "Loads group events from SQS"

    def health_check(self):
        try:
            GroupProcessor().check_interval(acceptable_silence=24*60)
        except EventException as ex:
            self.squawk(f'Warning: {ex}')

    def handle(self, *args, **options):
        try:
            with Pidfile():
                Gather(processor=GroupProcessor()).gather_events()
                self.update_job()
        except ProcessRunningException:
            pass
        except GatherException as err:
            raise CommandError(err)
