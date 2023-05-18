# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.dao.term import get_all_active_terms
from sis_provisioner.models.course import Course


class Command(SISProvisionerCommand):
    help = "Re-queue active courses for the current term."

    def handle(self, *args, **options):
        priority_expires_week = getattr(settings, 'PRIORITY_EXPIRES_WEEK', 5)
        for term in get_all_active_terms():
            if term.get_week_of_term() > priority_expires_week:
                continue
            Course.objects.prioritize_active_courses_for_term(term)

        self.update_job()
