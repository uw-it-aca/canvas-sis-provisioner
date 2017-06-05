from django.core.management.base import CommandError
from django.conf import settings
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.pidfile import Pidfile, ProcessRunningException
from sis_provisioner.events.group import Group
from sis_provisioner.models.events import GroupLog
from sis_provisioner.exceptions import GroupEventException
from aws_message.gather import Gather, GatherException
from time import time
from math import floor


class GroupsProvisionerCommand(SISProvisionerCommand):
    def health_check(self):
        # squawk if no new events in the last 12 hours
        acceptable_silence = (24 * 60)
        recent = GroupLog.objects.all().order_by('-minute')[:1]
        if len(recent):
            delta = int(floor(time() / 60)) - recent[0].minute
            if (delta > acceptable_silence):
                self.squawk(
                    "No group events in the last %s hours, %s minutes" % (
                        int(floor((delta/60))), (delta % 60)))


class Command(GroupsProvisionerCommand):
    help = "Loads group events from SQS"

    def handle(self, *args, **options):
        try:
            with Pidfile():
                Gather(settings.AWS_SQS.get('GROUP'),
                       Group, GroupEventException).gather_events()
                self.update_job()
        except ProcessRunningException as err:
            pass
        except GatherException as err:
            raise CommandError(err)
        except Exception as err:
            raise CommandError('FAIL: %s' % (err))
