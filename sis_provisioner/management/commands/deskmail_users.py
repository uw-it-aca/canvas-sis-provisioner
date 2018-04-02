from django.core.management.base import BaseCommand
import csv
import sys
import re


def to_email(uwnetid):
    return "%s@uw.edu" % uwnetid


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument('file_path', help='CSV file')

    def handle(self, *args, **options):
        file_path = options.get('file_path')

        RE_COMMENT = re.compile(r'^#')
        RE_ADMIN_TYPE = re.compile(r'^(1|2|3)$')

        dm_all_users = {}
        dm_datastorage_users = {}
        dm_shared_netid_admins = {}

        with open(file_path, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not len(row):
                    continue

                uwnetid = row[0]
                deskmail = row[1]
                forwarding = row[5]
                admins = row[8]

                if RE_COMMENT.match(uwnetid):
                    continue

                if deskmail == 'no':
                    continue

                if len(admins):  # shared netid
                    if re.match(r'^%s@%s.deskmail.washington.edu$' % (
                            uwnetid, uwnetid), forwarding):
                        continue

                    admins = admins.split(':')
                    admins = dict(admins[i:i+2] for i in range(0, len(admins), 2))
                    for admin in admins.keys():
                        if RE_ADMIN_TYPE.match(admins[admin]):
                            dm_all_users[to_email(admin)] = True
                            dm_shared_netid_admins[to_email(admin)] = True
                else:
                    dm_all_users[to_email(uwnetid)] = True

                    if not re.match(r'^%s@%s.deskmail.washington.edu$' % (
                            uwnetid, uwnetid), forwarding):
                        dm_datastorage_users[to_email(uwnetid)] = True

        self.write_file('dm_all_users.txt', dm_all_users)
        self.write_file('dm_datastorage_users.txt', dm_datastorage_users)
        self.write_file('dm_shared_netid_admins.txt', dm_shared_netid_admins)

    def write_file(self, path, data):
        f = open(path, 'w')
        f.write("\n".join(sorted(data.keys())))
        f.close()
