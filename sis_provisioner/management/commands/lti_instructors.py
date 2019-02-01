from django.core.management.base import BaseCommand, CommandError
from uw_canvas.users import Users
from restclients_core.exceptions import DataFailureException
import csv


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('file_path', help='CSV file')

    def handle(self, *args, **options):
        file_path = options.get('file_path')

        outfile = open('lti_instructors.csv', 'wb')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')

        client = Users()

        with open(file_path, 'rb') as csvfile:
            writer.writerow([
                'login', 'email', 'full_name', 'first_name', 'last_name'])

            course_ids = {}
            user_ids = {}

            reader = csv.reader(csvfile)
            for row in reader:
                if not len(row):
                    continue

                context_type = row[0]
                course_id = row[1]

                if context_type.lower() != 'course':
                    continue

                if course_id in course_ids:
                    continue

                users = client.get_users_for_course(
                    course_id, params={
                        'enrollment_type': ['teacher', 'designer'],
                        'include': ['email']})
                course_ids[course_id] = True

                for user in users:
                    if user.user_id in user_ids:
                        continue
                    user_ids[user.user_id] = True

                    email = user.email
                    if email is None:
                        email = '%s@uw.edu' % user.login_id

                    last_name = ''
                    first_name = ''
                    try:
                        (last_name, first_name) = user.sortable_name.split(',')
                    except ValueError:
                        pass

                    writer.writerow([user.login_id,
                                     email,
                                     user.name.strip().encode('utf-8'),
                                     first_name.strip().encode('utf-8'),
                                     last_name.strip().encode('utf-8')])

        outfile.close()
