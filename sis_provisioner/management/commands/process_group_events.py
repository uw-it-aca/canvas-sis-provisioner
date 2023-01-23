# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.pidfile import Pidfile, ProcessRunningException
from sis_provisioner.events.group import GroupProcessor
from sis_provisioner.exceptions import EventException
from aws_message.gather import Gather, GatherException


class Command(SISProvisionerCommand):
    help = "Loads group events from SQS"

    def health_check(self):
        try:
            GroupProcessor().check_interval(acceptable_silence=24*60)
        except EventException as ex:
            self.squawk('Warning: {}'.format(ex))

    def handle(self, *args, **options):
        try:
            with Pidfile():
                Gather(processor=GroupProcessor()).gather_events()
                self.update_job()
        except ProcessRunningException as err:
            pass
        except GatherException as err:
            raise CommandError(err)
