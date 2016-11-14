from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.dao.term import get_all_active_terms
from sis_provisioner.models import Course
from datetime import datetime


class Command(SISProvisionerCommand):
    help = "Loads courses for provisioning."

    def handle(self, *args, **options):
        """
        Loads all courses for the current and next terms with default
        priority, and updates all courses from previous term to priority
        none.
        """
        now_dt = datetime.now()
        for term in get_all_active_terms(now_dt):
            if term.bterm_last_day_add is not None:
                curr_last_date = term.bterm_last_day_add
            else:
                curr_last_date = term.last_day_add

            if now_dt.date() <= curr_last_date:
                Course.objects.add_all_courses_for_term(term)
            else:
                Course.objects.deprioritize_all_courses_for_term(term)

        self.update_job()
