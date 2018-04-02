from django.core.management.base import BaseCommand
import csv
import sys
import re


class Command(BaseCommand):
    help = ("Builds a csv file containing current UW employees, based on "
            "the input of the URL "
            "https://staff.washington.edu/krl/stats/byemail/more.csv")

    def add_arguments(self, parser):
        parser.add_argument('file_path', help='CSV file')

    def handle(self, *args, **options):
        file_path = options.get('file_path')

        RE_COMMENT = re.compile(r'^#')
        RE_CURRENT = re.compile(
            r'^\d:('
            r'4|5|13|14|15|17|24|25|27|32|40|43|45|46|53|54|55|56|'
            r'57|66|69|72|76|77|78|79|80|104|105|145|170|171'
            r')\/1$')

        outfile = open('current_users.csv', 'wb')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')

        with open(file_path, 'rb') as csvfile:
            writer.writerow(['uwnetid', 'deskmail', 'gsuite', 'mslive',
                             'o365', 'forwarding', 'category'])

            reader = csv.reader(csvfile)
            for row in reader:
                if not len(row):
                    continue

                uwnetid = row[0]
                deskmail = row[1]
                gsuite = row[2]
                mslive = row[3]
                o365 = row[4]
                forwarding = row[5]
                category = row[7]
                admins = row[8]

                # Ignore commented lines
                if RE_COMMENT.match(uwnetid):
                    continue

                # Ignore uwnetids with admins (non-personal netids)
                if len(admins):
                    continue

                # Ignore uwnetids with no services
                if (deskmail == 'no' and gsuite == 'no' and mslive == 'no' and
                        o365 == 'no'):
                    continue

                # Ignore uwnetids with no categories
                if not len(category):
                    print('No categories for %s' % uwnetid)
                    continue

                categories = category.split(' ')
                for c in categories:
                    if RE_CURRENT.match(c):
                        if deskmail != 'no':  # Convert float to 'yes'
                            deskmail = 'yes'
                        writer.writerow([uwnetid, deskmail, gsuite, mslive,
                                         o365, forwarding, category])
                        break

        outfile.close()
