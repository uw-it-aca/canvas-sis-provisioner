# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db.models.signals import post_save
from django.dispatch import receiver
from logging import getLogger
from sis_provisioner.models import Import
from sis_provisioner.models.group import Group
from sis_provisioner.models.course import Course
from sis_provisioner.models.user import User
from sis_provisioner.builders.users import UserBuilder
import traceback


log = getLogger(__name__)


@receiver(post_save, sender=Course)
def priority_course_import(sender, **kwargs):
    course = kwargs['instance']
    if course.priority == course.PRIORITY_IMMEDIATE:
        post_save.disconnect(priority_course_import, sender=Course)

        try:
            grouplist = Group.objects.filter(course_id=course.course_id,
                                             is_deleted__isnull=True,
                                             queue_id__isnull=True)
            grouplist.update(priority=course.PRIORITY_IMMEDIATE)
        except Exception as err:
            log.error('Immediate course provision fail: {}'.format(err))

        post_save.connect(priority_course_import, sender=Course)


@receiver(post_save, sender=User)
def priority_user_import(sender, **kwargs):
    user = kwargs['instance']
    if user.priority == user.PRIORITY_IMMEDIATE:
        post_save.disconnect(priority_user_import, sender=User)

        try:
            imp = Import(priority=user.priority, csv_type='user')
            imp.save()

            user.priority = user.PRIORITY_DEFAULT
            user.queue_id = imp.pk
            user.save()

            try:
                imp.csv_path = UserBuilder([user]).build()
            except Exception:
                imp.csv_errors = traceback.format_exc()

            if imp.csv_path:
                imp.import_csv()
            else:
                user.queue_id = None
                user.priority = user.PRIORITY_HIGH
                user.save()
                imp.delete()

        except Exception as err:
            log.error('Immediate user provision failed: {}'.format(err))
            user.priority = user.PRIORITY_HIGH
            user.save()

        post_save.connect(priority_user_import, sender=User)
