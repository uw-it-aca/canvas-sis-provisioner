# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Import
from sis_provisioner.builders.accounts import AccountBuilder
import traceback


class Command(SISProvisionerCommand):
    help = "Builds csv files for Canvas accounts."

    def handle(self, *args, **options):
        imp = Import(csv_type="account")
        try:
            imp.csv_path = AccountBuilder().build()
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        if imp.csv_path:
            imp.import_csv()

        self.update_job()
