from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from logging import getLogger
from models import Course, Group, User, Import
from models import PRIORITY_DEFAULT, PRIORITY_HIGH, PRIORITY_IMMEDIATE
from csv_builder import CSVBuilder
import traceback
import socket


log = getLogger(__name__)


@receiver(post_save, sender=Course)
def priority_course_import(sender, **kwargs):
    course = kwargs['instance']
    if course.priority == PRIORITY_IMMEDIATE:
        post_save.disconnect(priority_course_import, sender=Course)

        try:
            grouplist = Group.objects.filter(course_id=course.course_id,
                                             is_deleted__isnull=True,
                                             queue_id__isnull=True)
            grouplist.update(priority=PRIORITY_IMMEDIATE)
        except Exception as err:
            log.error('Immediate course provision fail: %s' % (err))

        post_save.connect(priority_course_import, sender=Course)


@receiver(post_save, sender=User)
def priority_user_import(sender, **kwargs):
    user = kwargs['instance']
    if user.priority == PRIORITY_IMMEDIATE:
        post_save.disconnect(priority_user_import, sender=User)

        try:
            imp = Import(priority=user.priority, csv_type='user')
            imp.save()

            user.priority = PRIORITY_DEFAULT
            user.queue_id = imp.pk
            user.save()

            try:
                imp.csv_path = CSVBuilder().generate_user_csv([user])
            except:
                imp.csv_errors = traceback.format_exc()

            if imp.csv_path:
                imp.import_csv()
            else:
                user.queue_id = None
                user.priority = PRIORITY_HIGH
                user.save()
                imp.delete()

        except Exception, err:
            log.error('Immediate user provision failed: %s' % (err))
            user.priority = PRIORITY_HIGH
            user.save()

        post_save.connect(priority_user_import, sender=User)
