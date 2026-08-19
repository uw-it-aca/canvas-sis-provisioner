# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import re
from datetime import datetime, timedelta

from django.utils.timezone import get_default_timezone, localtime

from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.course import Course


class Command(SISProvisionerCommand):
    help = "Handles provisioning errors in sis imports to Canvas."

    def handle(self, *args, **options):
        courses = Course.objects.filter(provisioned_error__isnull=False,
                                        queue_id__isnull=True,
                                        priority__gte=Course.PRIORITY_DEFAULT)

        retry_now_pattern = re.compile(r"500 (Timeout expired|DFDSRequest)")
        last_check_time = datetime.now(get_default_timezone()) - timedelta(hours=24)

        for course in courses:
            if (course.provisioned_status is None or
                retry_now_pattern.match(course.provisioned_status) or (
                    course.provisioned_date is not None and
                    localtime(course.provisioned_date) < last_check_time) or
                    localtime(course.added_date) < last_check_time):

                course.provisioned_error = None
                course.provisioned_status = None
                course.priority = Course.PRIORITY_HIGH
                course.save()

        self.update_job()
