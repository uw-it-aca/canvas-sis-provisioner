from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.dao.term import get_current_active_term
from sis_provisioner.models import Course
from datetime import datetime


class Command(SISProvisionerCommand):
    help = "Re-queue active courses for the current term."

    def handle(self, *args, **options):
        term = get_current_active_term(datetime.now())
        Course.objects.prioritize_active_courses_for_term(term)
        self.update_job()
