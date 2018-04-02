from django.core.management.base import BaseCommand
import glob
import csv
import sys
import re


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument('dir_path', help='Directory containing CSV files')

    def handle(self, *args, **options):
        dir_path = options.get('dir_path')

        RE_COMMENT = re.compile(r'^#')
        RE_CURRENT = re.compile(
            r'^\d:('
            r'1|2|4|5|13|14|15|17|18|19|20|24|25|27|29|32|40|41|'
            r'43|45|46|53|54|55|56|57|66|69|72|76|77|78|79|80|104|105|'
            r'145|170|171'
            r')\/1$')
        RE_RETIRED = re.compile(
            r'^\d:('
            r'4|5|13|14|15|17|24|25|27|32|34|40|43|45|46|53|54|55|56|'
            r'57|66|69|72|76|77|78|79|80|104|105|145|170|171'
            r')\/\d$')
        RE_ALUMNI = re.compile(r'^\d:(1|2|16|18|19|20|28|29|41)\/\d$')
        RE_ADMIN_TYPE = re.compile(r'^(1|2|3)$')
        RE_AFFILIATE = re.compile(r'^\d:28\/1$')

        retired_users = {}
        alumni_users = {}

        outfile = open('shared_netids.csv', 'wb')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')

        files = glob.glob('%s/*' % dir_path)

        for file_path in files:
            print(file_path)
            with open(file_path, 'rU') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if not len(row):
                        continue

                    uwnetid = row[0]
                    try:
                        o365 = row[4]
                    except:
                        print row
                    category = row[7]
                    admins = row[8]
                    is_retired = False
                    is_alum = False

                    # Ignore commented lines
                    if RE_COMMENT.match(uwnetid):
                        continue

                    if '059' in file_path and o365 == 'no':
                        continue

                    if not len(category):
                        print('No categories for %s' % uwnetid)
                        continue

                    categories = category.split(' ')
                    for category in categories:
                        if RE_CURRENT.match(category):
                            is_retired = False
                            is_alum = False
                            break
                        else:
                            if RE_RETIRED.match(category):
                                is_retired = True
                            if RE_ALUMNI.match(category):
                                is_alum = True

                    if not is_retired and not is_alum:
                        for category in categories:
                            if RE_AFFILIATE.match(category):
                                is_alum = True

                    if not is_retired and not is_alum:
                        continue

                    if len(admins):  # shared netid
                        if is_retired or is_alum:
                            writer.writerow(row)

                        admins = admins.split(':')
                        admins = dict(admins[i:i+2] for i in range(0, len(admins), 2))
                        for admin in admins.keys():
                            if RE_ADMIN_TYPE.match(admins[admin]):
                                if is_retired:
                                    retired_users[admin] = True
                                if is_alum:
                                    alumni_users[admin] = True
                    else:
                        if is_retired:
                            retired_users[uwnetid] = True
                        if is_alum:
                            alumni_users[uwnetid] = True

        self.write_file('retired_users.txt', retired_users)
        self.write_file('alumni_users.txt', alumni_users)

    def write_file(self, path, data):
        f = open(path, 'w')
        f.write("\n".join(sorted(data.keys())))
        f.close()
