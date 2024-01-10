# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from django.utils.timezone import make_aware, localtime, get_default_timezone
from sis_provisioner.models.course import Course
from datetime import datetime, timedelta
import re


class Command(SISProvisionerCommand):
    help = "Handles provisioning errors in sis imports to Canvas."

    def handle(self, *args, **options):
        courses = Course.objects.filter(provisioned_error__isnull=False,
                                        queue_id__isnull=True,
                                        priority__gte=Course.PRIORITY_DEFAULT)

        retry_now_pattern = re.compile(r"500 (Timeout expired|DFDSRequest)")
        last_check_time = make_aware(datetime.now() - timedelta(hours=24),
                                     get_default_timezone())

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
