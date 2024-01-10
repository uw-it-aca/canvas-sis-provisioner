# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from sis_provisioner.dao.user import get_person_by_regid
from sis_provisioner.dao.canvas import merge_all_users_for_person


class Command(BaseCommand):
    help = "Merge related users for the passed uwnetid"

    def add_arguments(self, parser):
        parser.add_argument('uwregid', help='uwregid of a user to migrate')

    def handle(self, *args, **options):
        person = get_person_by_regid(options.get('uwregid'))
        merge_all_users_for_person(person)
