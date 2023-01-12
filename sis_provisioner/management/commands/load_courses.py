# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.dao.term import get_all_active_terms, sws_now
from sis_provisioner.models.course import Course


class Command(SISProvisionerCommand):
    help = "Loads courses for provisioning."

    def handle(self, *args, **options):
        """
        Loads all courses for the current and next terms with default
        priority, and updates all courses from previous term to priority
        none.
        """
        for term in get_all_active_terms():
            if term.bterm_last_day_add is not None:
                curr_last_date = term.bterm_last_day_add
            else:
                curr_last_date = term.last_day_add

            if sws_now().date() <= curr_last_date:
                Course.objects.add_all_courses_for_term(term)
            else:
                Course.objects.deprioritize_all_courses_for_term(term)

        self.update_job()
