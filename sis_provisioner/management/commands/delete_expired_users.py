# Copyright 2026 UWIT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from logging import getLogger

from django.core.management.base import BaseCommand

logger = getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('user_file_path', help='User CSV file')
        parser.add_argument('enrollment_file_path', help='Enrollment CSV file')

    def handle(self, *args, **options):
        user_file_path = options.get('user_file_path')
        enrollment_file_path = options.get('enrollment_file_path')

        enrolled_users = set()
        with open(enrollment_file_path, 'r') as enrollment_csv:
            header = next(enrollment_csv)
            user_id_idx = header.index('canvas_user_id')

            for row in enrollment_csv:
                if len(row):
                    enrolled_users.add(row[user_id_idx])

        logger.info(f'Found {len(enrolled_users)} enrolled users')

        with open(user_file_path, 'r') as user_csv:
            header = next(user_csv)
            user_id_idx = header.index('canvas_user_id')

            for row in enrollment_csv:
                if not len(row):
                    continue

                if row[user_id_idx] in enrolled_users:
                    logger.info(f'User {row[user_id_idx]} is enrolled')
                else:
                    pass




