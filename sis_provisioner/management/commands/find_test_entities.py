# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from uw_pws import PWS
import csv


class Command(BaseCommand):
    def handle(self, *args, **options):
        outfile = open('test-entities.csv', 'w')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')
        writer.writerow(['uwnetid', 'uwregid'])

        pws = PWS()
        for entity in pws.entity_search(is_test_entity=True):
            print(entity.json_data())
            writer.writerow([entity.uwnetid, entity.uwregid])

        outfile.close()
