from django.core.management.base import BaseCommand
from uw_pws import PWS
import csv


class Command(BaseCommand):
    def handle(self, *args, **options):

        input_filename = '/app/userList-699.csv'
        output_filename = '/app/userList-699-with-active.csv'
        with (open(input_filename, 'r', newline='', encoding='utf-8') as infile,
              open(output_filename, 'w', newline='', encoding='utf-8') as outfile):

            csv.register_dialect('unix_newline', lineterminator='\n')

            reader = csv.reader(infile, dialect='unix_newline')
            writer = csv.writer(outfile, dialect='unix_newline')

            pws = PWS()

            header = next(reader)
            header.append('active')
            writer.writerow(header)

            email_idx = header.index('EmailAddress')

            for i, row in enumerate(reader):
                email = row[email_idx]

                try:
                    netid = email.replace('@uw.edu', '')
                    person = pws.get_person_by_netid(netid)

                    active = 'No'
                    if (person.is_emp_state_current() or
                            person.is_stud_state_current()):
                        active = 'Yes'

                except Exception as err:
                    print(err)
                    active = 'Unknown or Non-personal Netid'

                row.append(active)
                writer.writerow(row)
