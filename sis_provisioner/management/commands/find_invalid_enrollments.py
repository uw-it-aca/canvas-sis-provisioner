# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.management.commands import SISProvisionerCommand


class Command(SISProvisionerCommand):
    help = "Find enrollments that are invalid."

    def handle(self, *args, **options):
        # Get enrollments report for _ term
        #
        # Parse report for users who have both student and non-student roles
        #
        # For these users, check uw groups (affiliate and sponsored) to verify
        # membership
        #
        # If no membership in either, check for user in
        # sis_provisioner.models.User (insert if needed).  If existing and
        # invalid_enrollments_found_date is NULL, update record with
        # invalid_enrollments_found_date set to current dt
